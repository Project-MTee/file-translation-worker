from tildemt.enums.file_translation_status_subtype import FileTranslationSubstatus


class FileTranslationException(Exception):
    def __init__(self, error_type: FileTranslationSubstatus, message: str = ''):
        super().__init__(message)

        self.error_type = error_type
        self.message = message