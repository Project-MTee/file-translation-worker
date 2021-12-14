import io
import os
import logging
import codecs
from tildemt.file_translator.xlf_inline import XLFInlineTranslator
from tildemt.utils.file_encoder import FileEncoder


class TXTTranslator(XLFInlineTranslator):
    """Reads a plaintext (TXT) file, translates it using XLFInlineTranslator class and produces a plaintext output file"""
    def __init__(self, metadata):
        self.__logger = logging.getLogger('TXTTranslator')
        self.__logger.info("Initializing TXT Translator")
        super().__init__(metadata)

    def translate(self, source_file, target_file):
        """Translates the 'source_file' to 'target_file'
            'source_file' - path to an existing local .txt file
            'target_file' - path to local translated .txt file to be created in the translation process"""

        self.__logger.info("Translating TXT document from %s to %s", source_file, target_file)

        # Detect file encoding and convert to UTF-8 if necessary
        encoder = FileEncoder()
        encoding, _ = encoder.get_encoding(source_file, self.metadata['srcLang'])
        if encoding != 'utf-8':
            if encoding is None:
                self.__logger.error("Unable to detect file encoding")
            else:
                self.__logger.info("Detected incompatible encoding: %s. Converting to UTF-8...", encoding)
                utf8_source_file = source_file + '.utf8'
                self.on_temp_file.fire(utf8_source_file)

                if encoder.convert_to(source_file, encoding, utf8_source_file):
                    source_file = utf8_source_file
                else:
                    self.__logger.error("Error while converting file to UTF-8. Continuing as is...")
                encoding = 'utf-8'
        else:
            with io.open(source_file, 'rb') as file:
                raw = file.read(min(3, os.path.getsize(source_file)))
                if raw.startswith(codecs.BOM_UTF8):
                    encoding = 'utf-8-sig'

        with io.open(source_file, 'r', encoding=encoding, newline='') as txt_source_file:
            super().translate_file(txt_source_file)

        self.__logger.info("Writing translated segments to %s", target_file)

        with io.open(target_file, 'w', encoding=encoding) as txt_target_file:
            self.on_temp_file.fire(target_file)

            # Write translated segments to the result file
            txt_target_file.writelines(self.target_segments)
