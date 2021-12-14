import logging

from tildemt.file_translator.types.tikal import TikalTranslator


class ODFTranslator(TikalTranslator):
    """Handles the ODF file translation. Format extentions: .odt, .odp or .ods file"""
    def __init__(self, metadata):
        self.__logger = logging.getLogger('ODFTranslator')
        self.__logger.info('Initializing ODF Translator')

        super().__init__(
            metadata,
            translation_options=['zoneStandalone',
                                 'inline',
                                 'sent_info'],
            tikal_filter='okf_openoffice',
            overwrite_translation=True
        )
