from typing import TypedDict
from tildemt.enums.file_translation_status_subtype import FileTranslationSubstatus
from tildemt.enums.file_translation_status_type import FileTranslationStatusType


class UpdateFileTranslationMetadata(TypedDict):
    segments: int
    translatedSegments: int
    status: FileTranslationStatusType
    substatus: FileTranslationSubstatus
    domain: str
