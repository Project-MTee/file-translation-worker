"""This module contain file translation base class that translate XLIFF inline files"""

import logging
import os
import time
from tildemt.enums.file_translation_status_subtype import FileTranslationSubstatus
from tildemt.exceptions.file_translation_exception import FileTranslationException
from tildemt.services.text_translation_service import TextTranslationService
from tildemt.utils.event_hook import EventHook


class XLFInlineTranslator():
    """Class implements tagged and plaintext translation"""
    def __init__(self, metadata):

        self.__logger = logging.getLogger('XLFInlineTranslator')
        self.__logger.info("Initializing XLF-Inline Translator")

        # Fire progress event after min_progress_report_interval seconds has elapsed and
        # new segments has been translated after the previous report event
        self.min_progress_report_interval = 1 # seconds
        self.metadata = metadata

        self.source_segments = []
        self.target_segments = []
        self.translated_segment_count = 0

        # Read the neccessary values from Environment Variables
        self.tools_dir = os.path.normpath(os.environ.get("TOOLS_DIR", "/usr/lib/tildemt/"))

        # Create Event Hooks for translation progress tracking
        self.on_start = EventHook()
        self.on_progress = EventHook()
        self.on_temp_file = EventHook()
        self.on_upload_file_result = EventHook()
        self.on_postprocess_start = EventHook()

        self.source_lang = self.metadata['srcLang']
        self.target_lang = self.metadata['trgLang']
        self.domain = self.metadata['domain']

        # A flag indicating whether to replace existing translations or
        # only put machine translations in empty target segments
        self.replace_target = False

        self.__text_translation_service = TextTranslationService(self.source_lang, self.target_lang, self.domain)

    def translate_file(self, data_stream):
        """
        Initiates the translation process.
            - 'data_stream' - a stream object of translatable segments separated by lines
        """

        self.on_start.fire()

        lines = data_stream.readlines()
        if not lines:
            raise FileTranslationException(FileTranslationSubstatus.NO_TEXT_EXTRACTED)

        # save newlines for later, but remove them in translation process, as many tools use CMDTextProcessor,
        # where newlines are conflicting with source text newlines
        saved_newlines = []
        self.source_segments = []
        for line in lines:
            self.source_segments.append(line.rstrip())

            if line.endswith('\r\n'):
                saved_newlines.append('\r\n')
            elif line.endswith('\n'):
                saved_newlines.append('\n')
            else:
                saved_newlines.append('')

        # Report total count of segments
        total_segment_count = len(self.source_segments)
        self.on_progress.fire(domain=self.__text_translation_service.domain, seg_count=total_segment_count)

        # Start translation thread pool
        self.__logger.info("Translate all %d segments", total_segment_count)
        last_progress_time = time.monotonic()

        for ith, result in enumerate(self.__text_translation_service.translate(self.source_segments)):
            self.target_segments.append(result['translation'] + saved_newlines[ith])

            self.translated_segment_count += 1

            # Report progress if time interval has elapsed
            if time.monotonic() - last_progress_time >= self.min_progress_report_interval:
                self.on_progress.fire(
                    domain=self.__text_translation_service.domain,
                    seg_translated=self.translated_segment_count
                )
                last_progress_time = time.monotonic()

        self.__logger.debug("Translation finished")

        # Fire final progress report
        self.on_progress.fire(
            domain=self.__text_translation_service.domain,
            seg_translated=self.translated_segment_count
        )
        self.on_postprocess_start.fire()
