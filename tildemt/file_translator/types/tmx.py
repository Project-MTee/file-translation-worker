#!/usr/bin/python

import logging
import subprocess
from tildemt.file_translator.types.tikal import TikalTranslator


class TMXTranslator(TikalTranslator):
    """Handles the TMX file translation"""
    def __init__(self, metadata):
        self.__logger = logging.getLogger('TMXTranslator')
        self.__logger.info("Initializing TMX Translator")
        super().__init__(metadata, translation_options=['inline'], overwrite_translation=True)

        # check if set to keep existing primary tanslations, only append new one to <alt-trans /> node
        if not self.replace_target:
            self.overwrite_translation = False

    def translate(self, source_file, target_file):
        """ Translates the 'source_file' to 'target_file'
        'source_file' - path to an existing local file
        'target_file' - path to local translated file to be created in the translation process"""

        # When working with TMX files, language codes provided in metadata and actual XML node attributes might differ
        # Okapi Tikal needs to know the which are the real source and target language codes (found in TMX file)
        self.source_lang = self.get_tmx_lang(source_file, self.source_lang)
        self.__logger.info("Using %s as TMX source language", self.source_lang)
        self.target_lang = self.get_tmx_lang(source_file, self.target_lang)

        self.__logger.info("Using %s as TMX target language", self.target_lang)

        super().translate(source_file, target_file)

    def get_tmx_lang(self, filepath, lang_code):
        """Calls a Perl script that tries to get the real language provided in TMX document based on attribute values
        'filepath' - path to tmx file to process
        'lang_code' - language code to look for in the document"""

        exit_code = -1
        temp_lang = ''
        try:
            arguments = ['perl', self.tools_dir + '/scripts/guessLang.pl', filepath, lang_code]
            self.__logger.info("Trying to guess TMX provided language for %s", lang_code)
            self.__logger.debug('Lang gueser parameters: %s', arguments)

            with subprocess.Popen(arguments, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=None) as process:
                for line in process.stdout.readlines():
                    line = line.strip().decode('utf-8')
                    self.__logger.info(line)
                    if line:
                        temp_lang = line

                exit_code = process.wait()

        except Exception:
            self.__logger.exception(
                "An exception occurred while trying to get the language code from TMX file! Falling back to default"
            )
            return lang_code

        if exit_code != 0:
            self.__logger.warning("guesLang.pl quit with status code %d. See debug log for more information", exit_code)
            return lang_code

        if temp_lang == 'ERR':
            if len(lang_code) > 2:
                # If non ISO 639-1 language code is provided, shorten it and search again
                # For example, 'en' matches 'en', 'eng', 'en-US', 'en-GB' etc.
                self.__logger.info(
                    "Trying to get the real TMX language again using ISO 639-1 language code %s",
                    lang_code[:2]
                )
                return self.get_tmx_lang(filepath, lang_code[:2])
            else:
                self.__logger.warning(
                    "Error while trying to get the language code from TMX file! Falling back to default"
                )
                return lang_code

        return temp_lang
