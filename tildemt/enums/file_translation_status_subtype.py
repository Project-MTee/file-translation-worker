from enum import Enum


class FileTranslationSubstatus(Enum):
    UNSPECIFIED = "Unspecified"
    BAD_FILE = "BadFileError"
    UNKNOWN_FILE_TYPE = "UnknownFileTypeError"
    TRACK_CHANGES_ENABLED = "TrackChangesEnabledError"
    NO_TEXT_EXTRACTED = "NoTextExtractedError"