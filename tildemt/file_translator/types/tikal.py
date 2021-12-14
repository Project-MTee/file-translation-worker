"""Convert file using Okapi Tikal to XLIFF, translate it,
and convert back to the original document format"""

import glob
import io
import logging
import os.path
import subprocess

from tildemt.enums.file_translation_status_subtype import FileTranslationSubstatus
from tildemt.exceptions.file_translation_exception import FileTranslationException
from tildemt.file_translator.xlf_inline import XLFInlineTranslator


class TikalTranslator(XLFInlineTranslator):
    """Handles Okapi Tikal supported file translation"""

    # Tikal path
    __TIKAL_PATH = '/usr/local/lib/okapi_tikal/tikal.sh'

    # Don't generate source MXLF file if it's created already by preprocess method for example
    reuse_mxlf = False

    def __init__(self, metadata, translation_options=None, overwrite_translation=True, tikal_filter=None):
        self.__logger = logging.getLogger('TikalTranslator')
        self.__logger.info('Initializing Tikal Translator')

        self.translation_options = translation_options
        # Tikal option - Overwrite translation in the target, even if it exists
        self.overwrite_translation = overwrite_translation
        # Tikal option - Identifier of the filter configuration to use for the extraction
        self.tikal_filter = tikal_filter

        super().__init__(metadata)

    def translate(self, source_file, target_file):
        """ Translates the 'source_file' to 'target_file'
        'source_file' - path to an existing local file
        'target_file' - path to local translated file to be created in the translation process"""

        self.__logger.info("Translating document from %s to %s", source_file, target_file)

        # call pre processing of the source file
        source_file = self.preprocess(source_file)

        # Extract inline contents of the source file
        inline_source_filepath = self.__to_inline(source_file)

        # Call the XLFInlineTranslator's translation method with inline stream
        # and document format appropriate parameters
        with io.open(inline_source_filepath, 'r', encoding='utf-8', newline='') as inline_source_file:
            super().translate_file(inline_source_file)

        inline_target_filepath = f'{target_file}.mxlf.{self.target_lang.lower()}'
        self.__logger.info("Writing translated segments to %s", inline_target_filepath)

        # Create and write XLF Inline file from translated segments
        with io.open(inline_target_filepath, 'w', encoding='utf-8', newline='') as inline_target_file:
            self.on_temp_file.fire(inline_target_filepath)

            for segment in self.target_segments:
                inline_target_file.write(self.postprocess_segment(segment))

        # Create the final translation document
        self.__from_inline(inline_target_filepath, source_file, target_file)

        # call post processing of the target file
        self.postprocess(target_file)

    @staticmethod
    def preprocess(source_file):
        """Pre processing of the target file and return preprocessed file path"""
        return source_file

    def postprocess(self, target_file):
        """Post processing of the target file"""

    @staticmethod
    def postprocess_segment(segment):
        """Post processing of the translation of the segment"""
        return segment

    def __to_inline(self, source_file):
        """Extracts XLF-Inline content from the provided source file using Okapi Tikal"""

        exit_code = -1
        target = f"{source_file}.mxlf.{self.source_lang.lower()}"

        if self.reuse_mxlf and os.path.exists(target):
            self.__logger.info("XLF-Inline file exists already. Skip convertion.")
            return target

        try:
            arguments = [self.__TIKAL_PATH, '-xm', source_file, '-sl', self.source_lang.lower(), '-to', target]
            # add format specific extraction filter if specified
            if self.tikal_filter:
                arguments.extend(['-fc', self.tikal_filter])

            self.__logger.info("Extracting XLF-Inline from the source document")
            self.__logger.debug('Tikal parameters: %s', arguments)

            with subprocess.Popen(arguments, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=None) as process:
                for line in process.stdout.readlines():
                    self.__logger.info(line.decode('utf-8'))

                exit_code = process.wait()

            # Sometimes mxliff target file name is appended with source language code by tikal,
            # so check if target file exists, and return first file with extention if it does not
            if not os.path.isfile(target):
                self.__logger.warning(
                    "XLF-Inline output file %s does not exist. Looking for file with extension",
                    target
                )
                candidates = glob.glob(target + '*')
                if candidates:
                    target = candidates[0]
                    self.__logger.info("XLF-Inline output file changed to %s", target)

        except (subprocess.SubprocessError, ValueError, OSError) as ex:
            self.__logger.exception("Error extracting inline contents from the source document")
            raise FileTranslationException(FileTranslationSubstatus.BAD_FILE) from ex

        finally:
            self.on_temp_file.fire(target)

        if exit_code != 0:
            self.__logger.error("Okapi Tikal quit with status code %d", exit_code)
            raise FileTranslationException(FileTranslationSubstatus.BAD_FILE)

        return target

    def __from_inline(self, inline_source_file, source_file, target_file):
        """Merges XLF-Inline document back to original document format
        using original document as a template"""

        exit_code = -1
        try:
            arguments = [
                self.__TIKAL_PATH,
                '-lm',
                source_file,
                '-sl',
                self.source_lang.lower(),
                '-tl',
                self.target_lang.lower(),
                '-from',
                inline_source_file,
                '-to',
                target_file
            ]

            if self.overwrite_translation:
                arguments.append('-overtrg') # overwrite target
            else:
                arguments.append('-totrg') # write to target but don't overwrite existing

            # add format specific extraction filter if specified
            if self.tikal_filter:
                arguments.extend(['-fc', self.tikal_filter])

            self.__logger.info("Merging XLF-Inline back to the document")
            self.__logger.debug('Tikal parameters: %s', arguments)

            with subprocess.Popen(arguments, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=None) as process:
                for line in process.stdout.readlines():
                    self.__logger.info(line.decode('utf-8'))

                exit_code = process.wait()

        except (subprocess.SubprocessError, ValueError, OSError) as ex:
            self.__logger.exception("Error converting translated content to the original document format")

            raise FileTranslationException(FileTranslationSubstatus.BAD_FILE) from ex

        finally:
            self.on_temp_file.fire(target_file)

        if exit_code != 0:
            self.__logger.error("Okapi Tikal quit with status code %d. See debug log for more information", exit_code)

            raise FileTranslationException(FileTranslationSubstatus.BAD_FILE)
