import subprocess


class FileEncoder():
    """Class uses Linux command line utilities for detecting and manipulating text-file encoding"""
    def get_encoding(self, file_path, language=None):
        """Gets and returns the encoding of a text file using 'file -bi' command
        'file_path' - full path to file
        'language' - two-symbol ISO language code of the file's source language.
                     Used to blindly guess the codepage of non-Unicode files.
        Returns the probable encoding or None if undetermined and a flag
        indicating whether an ASCII extentension codepage is used. """

        exit_code = -1
        encoding = ''
        is_ascii = False

        file_process_args = ['file', '-bi', file_path]
        filtred_info_process_args = ['sed', '-e', 's/.*[ ]charset=//']
        with subprocess.Popen(file_process_args, stdout=subprocess.PIPE) as file_info_process:
            with subprocess.Popen(
                filtred_info_process_args,
                stdin=file_info_process.stdout,
                stdout=subprocess.PIPE
            ) as filtred_info_process:

                for line in filtred_info_process.stdout.readlines():
                    encoding = encoding + line.strip().decode("utf-8")

                exit_code = filtred_info_process.wait()

        if exit_code == 0:
            # No extra guessing should be necessary for 'us-ascii' encoding, because the file
            # obviously contains only symbols 0 - 127 without any extensions
            if encoding not in ['us-ascii', 'utf-8', 'utf-16le', 'utf-16be']:
                is_ascii = True

            if language and is_ascii:
                return self.get_codepage(language), is_ascii

            return encoding, is_ascii

        return None, is_ascii

    @staticmethod
    def get_codepage(language):
        """Retruns a Windows codepage name based on ISO 639-1 language code.
        If the language code is not mapped with a codepage, returns None."""

        encoding_map = {
            # key - name of a common Windows codepage
            # value - a list of ISO 639-1 language codes compatable with key codepage

            # Western Europe
            'windows-1252':
                [
                    'af',
                    'sq',
                    'eu',
                    'ca',
                    'co',
                    'da',
                    'en',
                    'fo',
                    'gl',
                    'de',
                    'is',
                    'id',
                    'ga',
                    'it',
                    'la',
                    'lb',
                    'ms',
                    'gv',
                    'no',
                    'oc',
                    'pt',
                    'rm',
                    'gd',
                    'es',
                    'sw',
                    'sv',
                    'wa'
                ],
            # Central and Eastern Europe
            'windows-1250': ['pl',
                             'cs',
                             'sk',
                             'hu',
                             'sl',
                             'bs',
                             'hr',
                             'ro',
                             'sq'],
            # Bulgarian, Byelorussian, Macedonian, Russian, Serbian
            'windows-1251': ['bg',
                             'be',
                             'mk',
                             'ru',
                             'sr'],
            # Greek
            'windows-1253': ['el'],
            # Turkish
            'windows-1254': ['tr'],
            # Hebrew
            'windows-1255': ['he'],
            # Arabic
            'windows-1256': ['ar'],
            # Baltic languages
            'windows-1257': ['lv',
                             'lt',
                             'et'],
            # Vietnamese
            'windows-1258': ['vi']
        }

        for encoding, encoding_languages in encoding_map.items():
            if language in encoding_languages:
                return encoding

        return None

    @staticmethod
    def convert_to(source_filepath, source_encoding, target_filepath, target_encoding='utf-8'):
        """Converts the source file with source encoding to target encoding which defaults to UTF-8 and saves
        it in the target file location"""

        exit_code = -1

        arguments = ['iconv', '-f', source_encoding, '-t', target_encoding, '-o', target_filepath, source_filepath]
        with subprocess.Popen(arguments, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=None) as process:
            exit_code = process.wait()

        return exit_code == 0
