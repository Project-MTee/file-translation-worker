import datetime
import logging
import logging.config
import os
import os.path
import tempfile
import shutil
from tildemt.enums.file_translation_status_subtype import FileTranslationSubstatus
from tildemt.enums.file_translation_status_type import FileTranslationStatusType
from tildemt.exceptions.file_translation_exception import FileTranslationException

import tildemt.file_translator
from tildemt.enums.file_upload_type import FileUploadType
from tildemt.services.file_translation_service import FileTranslationService


class Translator():
    def __init__(self, doc_id):
        self.__logger = logging.getLogger('FileTranslator')

        self.__logger.info("Initializing File Translator")

        self.doc_id = doc_id

        # List of temporary files created in the translation process
        self.temp_files = []

        self.file_meta = {}

        self.temp_dir = tempfile.gettempdir()

        self.__file_translation_service = FileTranslationService(doc_id)

    def translate(self):
        "Initialize translation process & translate"

        extension = None
        start_time = datetime.datetime.utcnow()

        try:
            self.__logger.info("Initializing the translation process")

            self.__file_translation_service.update_metadata({'status': FileTranslationStatusType.INITIALIZING.value})

            # Get the neccessary file metadata
            self.file_meta = self.__file_translation_service.get_metadata()

            source_file = list(filter(lambda file: file["category"] == "Source", self.file_meta['files']))[0]

            extension = source_file["extension"]

            extension = self.file_meta["extension"] = extension[1:].lower()

            source_dir = f'{self.temp_dir}/{self.doc_id}/source'
            result_dir = f'{self.temp_dir}/{self.doc_id}/result'

            if not os.path.exists(source_dir):
                os.makedirs(source_dir)
            if not os.path.exists(result_dir):
                os.makedirs(result_dir)

            local_source_file, file_name_id = self.__file_translation_service.download_source_file(source_dir)
            local_target_file = f'{result_dir}/{file_name_id}'

            self.__logger.info("File extension: %s", extension)

            # Initialize the appropriate Translator according to the file extension
            file_translator_type = extension

            translator = tildemt.file_translator.FILE_TYPES.get(file_translator_type)

            if translator is None:
                raise FileTranslationException(FileTranslationSubstatus.UNKNOWN_FILE_TYPE)

            translator = translator(self.file_meta)

            # Bind the translation events
            self.__logger.info("Binding translation Events")
            translator.on_start += self.__on_translation_start
            translator.on_progress += self.__on_translation_progress
            translator.on_temp_file += self.__on_temp_file_created
            translator.on_upload_file_result += self.__file_translation_service.upload_file
            translator.on_postprocess_start += self.__on_postprocess_start

            self.__on_preprocess_start()

            translator.translate(local_source_file, local_target_file)

            self.__file_translation_service.upload_file(local_target_file, FileUploadType.TRANSLATED.value)

            # Change the document status to "completed" and update statistics
            end_time = datetime.datetime.utcnow()

            self.__file_translation_service.update_metadata(
                {
                    'status': FileTranslationStatusType.SUCCEEDED.value,
                    'translatedSegments': translator.translated_segment_count,
                }
            )

        except FileTranslationException as err:
            self.__logger.exception("File translation terminated with error code %s: %s", err.error_type, err.message)
            self.__report_error(err.error_type)
        except Exception:
            self.__logger.exception("File translation terminated with uncaught Exception")
            self.__report_error('E_UNKNOWN_ERROR')
        finally:
            self.__cleanup()

        self.__logger.info("File translation finished in %s", end_time - start_time)

    def __report_error(self, error_type: FileTranslationSubstatus):
        """Sets translation status metadata in Resource Repository to error with passed error code and message"""
        self.__file_translation_service.update_metadata(
            {
                'status': FileTranslationStatusType.ERROR.value,
                'substatus': error_type.value
            }
        )

    def __cleanup(self):
        """Cleans up temporary files created in translation process"""

        self.__logger.info("Cleaning up system from temporary files")
        for filepath in self.temp_files:
            try:
                if os.path.isfile(filepath):
                    self.__logger.info("Removing file %s", filepath)
                    os.remove(filepath)
                else:
                    self.__logger.warning("Seems that %s is not a file. Skipping...", filepath)
            except OSError:
                self.__logger.exception("Unable to remove file %s", filepath)

        temp_file_dir = f'{self.temp_dir}/{self.doc_id}'

        try:
            self.__logger.info("Removing directory %s", temp_file_dir)
            shutil.rmtree(temp_file_dir)
        except OSError:
            self.__logger.exception("Unable to remove directory  %s", temp_file_dir)

    # *********************** #
    # File Translation Events #
    # *********************** #
    def __set_file_translation_status(self, translation_status):
        self.__file_translation_service.update_metadata({'status': translation_status})

    def __on_postprocess_start(self):
        self.__set_file_translation_status(FileTranslationStatusType.SAVING.value)

    def __on_preprocess_start(self):
        self.__set_file_translation_status(FileTranslationStatusType.EXTRACTING.value)

    def __on_translation_start(self):
        """Event fired when translation has started, changes the status of the file"""
        self.__set_file_translation_status(FileTranslationStatusType.TRANSLATING.value)

    def __on_translation_progress(
        self,
        domain: str,
        seg_count: int = -1,
        seg_translated: int = -1,
    ):
        """Event fired at the start of a translation, reporting the total segment count, and at designated times, reporting the progress"""
        if seg_translated > -1:
            self.__file_translation_service.update_metadata({'translatedSegments': seg_translated, 'domain': domain})

        if seg_count > -1:
            self.__file_translation_service.update_metadata({'segments': seg_count, 'domain': domain})

    def __on_temp_file_created(self, filepath):
        """Event fired when a temporary file is created in the translation process. Stores the file path in a list for later clean-up porcess."""
        self.__logger.info("A temporary file has been created in %s", filepath)
        self.temp_files.append(filepath)
