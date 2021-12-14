import os
import re
import zipfile
import logging
from lxml import etree
from tildemt.enums.file_translation_status_subtype import FileTranslationSubstatus
from tildemt.exceptions.file_translation_exception import FileTranslationException
from tildemt.file_translator.types.tikal import TikalTranslator


class DOCXTranslator(TikalTranslator):
    """Handles the DOCX file translation"""
    def __init__(self, metadata):
        self.__logger = logging.getLogger('DOCXTranslator')
        self.__logger.info("Initializing DOCX Translator")
        super().__init__(
            metadata,
            overwrite_translation=True,
            translation_options=['zoneStandalone',
                                 'inline',
                                 'sent_info']
        )

    def preprocess(self, source_file):
        """Preprocesses the source document for Okapi Tikal to avoid content extraction error"""
        self.__logger.info("Preprocessing DOCX document %s", source_file)

        tmp_file = source_file + '.tmp'
        try:
            with zipfile.ZipFile(source_file, 'r') as source:
                with zipfile.ZipFile(tmp_file, 'w') as target:
                    for item in source.infolist():
                        buffer = source.read(item.filename)
                        buffer = self.__filter_xml_file(item.filename, buffer)
                        target.writestr(item, buffer)

        except FileTranslationException:
            raise

        except Exception as ex:
            # Mostly, errors in this section indicate broken DOCX document.
            # Other unlikely reasons could include insufficiant storage space, permission issues and similar things
            self.__logger.exception("Error while preprocessing the input document")
            raise FileTranslationException(FileTranslationSubstatus.BAD_FILE) from ex

        os.remove(source_file)
        os.rename(tmp_file, source_file)
        return source_file

    @staticmethod
    def __filter_xml_file(filename, buffer):
        "Remove unallowed tags from XML file buffer string"
        marginals = re.match(r'.*(header|footer)\d+\.xml$', filename)

        if filename.endswith('document.xml'):
            xml_doc = etree.fromstring(buffer, etree.XMLParser(recover=False))

            # remove field element tags and properties, keep content
            etree.strip_tags(
                xml_doc,
                '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}fldSimple',
                '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}sdt',
                '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}sdtContent',
                '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}softHyphen' # remove softHyphen (¬)
            )

            etree.strip_elements(
                xml_doc,
                '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}sdtPr',
                '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}sdtEndPr',
                '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}instrText',
                '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}fldChar'
            )

            deletable = []

            # merge broken words (partially formatted words are split into several text elements)
            # paragraphs:
            text_break = r'\s|\W'

            for paragraph in xml_doc.iterfind('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'):
                paragraph_elements = paragraph.findall(
                    './{http://schemas.openxmlformats.org/wordprocessingml/2006/main}r/*'
                )
                txt_elements = paragraph.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t')
                if len(txt_elements) < 2:
                    continue
                last_txt_elem = txt_elements[-1]
                merged_word = ''
                word_start = None
                word_parts = 0

                for element in paragraph_elements:
                    if (
                        element.tag in (
                            '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tab',
                            '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}br',
                            '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}cr',
                            '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}noBreakHyphen'
                        )
                    ):
                        if word_parts > 1:
                            word_start.text = merged_word
                        merged_word = ''
                        word_parts = 0
                        word_start = None
                    elif element.tag == '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rPr':
                        # check if text has superscript or subscript formatting
                        # iterates over elements properties and checks for vertAlign
                        for run_props in element:
                            if (
                                (
                                    run_props.tag
                                    == '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}vertAlign'
                                ) and (
                                    run_props.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val')
                                    == 'superscript' or
                                    run_props.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val')
                                    == 'subscript'
                                )
                            ):
                                if word_parts > 1:
                                    word_start.text = merged_word
                                merged_word = ''
                                word_parts = 0
                                word_start = None
                    elif element.tag == '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t' and element.text:
                        # if text element starts with space or a non word chararcter
                        if re.match(text_break, element.text[0]):
                            if word_parts > 1:
                                word_start.text = merged_word
                            merged_word = ''
                            word_parts = 0
                            word_start = None
                            # if broken word starts with space
                            if not re.match(text_break, element.text[-1]):
                                merged_word += element.text
                                word_parts += 1
                                word_start = element
                        # if text element ends with space or a non word chararcter or it is last in paragraph
                        elif re.match(text_break, element.text[-1]) or element == last_txt_elem:
                            if word_parts >= 1:
                                merged_word += element.text
                                word_start.text = merged_word
                                deletable.append(element)
                            merged_word = ''
                            word_parts = 0
                            word_start = None
                        else:
                            merged_word += element.text
                            if word_parts > 0:
                                deletable.append(element)
                            word_parts += 1
                            if word_start is None:
                                word_start = element

            DOCXTranslator.__remove_tags(deletable)
            deletable = []

            for tag in xml_doc.iter():
                tag_name = tag.tag

                #seems to be fixed in latest tikal
                #if tag_name.endswith('ins'):
                # Track Changes detected within the document - further processing with Tikal is not possible
                #    raise FileTranslationException(FileTranslationErrorType.TRACK_CHANGES_ENABLED)

                if (
                    'proofErr' in tag_name # Spellcheck information
                    or '{http://schemas.openxmlformats.org/drawingml/2006/main}txSp' in tag_name or
                    'commentRangeStart' in tag_name # Comments
                    or 'commentRangeEnd' in tag_name # Empty text runs
                    or (tag_name == 'w:r' and not tag.getchildren())
                ):
                    deletable.append(tag)

            DOCXTranslator.__remove_tags(deletable)
            buffer = etree.tostring(xml_doc)

        elif filename.endswith('comments.xml'):
            deletable = []
            xml_doc = etree.fromstring(buffer, etree.XMLParser(recover=False))

            for tag in xml_doc.iter():
                tag_name = tag.tag
                if 'proofErr' in tag_name:
                    deletable.append(tag)

            DOCXTranslator.__remove_tags(deletable)
            buffer = etree.tostring(xml_doc)

        elif marginals:
            deletable = []
            xml_doc = etree.fromstring(buffer, etree.XMLParser(recover=False))

            for tag in xml_doc.iter():
                tag_name = tag.tag
                if (
                    'proofErr' in tag_name or
                    #let those posers live
                    #'AlternateContent' in tag_name or
                    'commentRangeStart' in tag_name or 'commentRangeEnd' in tag_name or
                    (tag_name == 'w:r' and not tag.getchildren())
                ):
                    deletable.append(tag)

            if tag_name.endswith('ins'):
                # Track Changes detected within the document - further processing with Tikal is not possible
                raise FileTranslationException(FileTranslationSubstatus.TRACK_CHANGES_ENABLED)

            DOCXTranslator.__remove_tags(deletable)
            buffer = etree.tostring(xml_doc)

        return buffer

    @staticmethod
    def __remove_tags(tags):
        "Remove tags from document"
        for tag in tags:
            try:
                DOCXTranslator.__remove_tag_hierarchy(tag)
            except Exception:
                logging.getLogger('DOCXTranslator').exception("Cannot remove tag from document")

    @staticmethod
    def __remove_tag_hierarchy(tag):
        """Removes a tag and it's parents if the tag is the only child from a document"""
        parent = tag.getparent()
        while len(parent.getchildren()) == 1:
            tag = parent
            parent = parent.getparent()

        parent.remove(tag)
