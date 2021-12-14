from enum import Enum


class FileTranslationStatusType(Enum):
    INITIALIZING = "initializing"
    EXTRACTING = "extracting"
    # WAITING_FOR_MT = "waiting"
    TRANSLATING = "translating"
    SAVING = "saving"
    SUCCEEDED = "completed"
    ERROR = "error"
