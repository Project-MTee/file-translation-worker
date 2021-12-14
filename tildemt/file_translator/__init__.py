from tildemt.file_translator.types.tmx import TMXTranslator
from tildemt.file_translator.types.txt import TXTTranslator
from tildemt.file_translator.types.odf import ODFTranslator
from tildemt.file_translator.types.docx import DOCXTranslator

FILE_TYPES = {
    'tmx': TMXTranslator,
    'txt': TXTTranslator,
    'docx': DOCXTranslator,
    'xlsx': DOCXTranslator,
    'pptx': DOCXTranslator,
    'odt': ODFTranslator
}
