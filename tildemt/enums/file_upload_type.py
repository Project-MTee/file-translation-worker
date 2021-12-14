from enum import Enum


class FileUploadType(Enum):
    SOURCE = "Source"
    SOURCE_CONVERTED = "SourceConverted"
    TRANSLATED = "Translated"
    TRANSLATED_CONVERTED = "TranslatedConverted"
    UNKNOWN_WORD_FILE = "UnknownWordFile"
