import logging
import os
import shutil
import requests

from tildemt.models.update_file_translation_metadata import UpdateFileTranslationMetadata


class FileTranslationService():
    def __init__(self, task):
        self.__logger = logging.getLogger('FileTranslatorService')
        self.__url = os.environ.get("FILE_TRANSLATION_SERVICE_URL")
        self.__task = task

        self.__http_client = requests.Session()
        self.__http_client.auth = (
            os.environ.get("FILE_TRANSLATION_SERVICE_USER"),
            os.environ.get("FILE_TRANSLATION_SERVICE_PASS")
        )
        self.__current_metadata = None

    def update_metadata(self, metadata):
        if not self.__current_metadata:
            self.get_metadata()

        for key in metadata:
            self.__current_metadata[key] = metadata[key]

        metadata_update = UpdateFileTranslationMetadata(
            segments=self.__current_metadata['segments'],
            translatedSegments=self.__current_metadata['translatedSegments'],
            status=self.__current_metadata['status'],
            substatus=self.__current_metadata['substatus'],
            domain=self.__current_metadata['domain']
        )

        self.__logger.info("Update metadata[%s]: %s", self.__task, metadata_update)

        response = self.__http_client.put(f"{self.__url}/file/{self.__task}", json=metadata_update)

        response.raise_for_status()

        self.__current_metadata = response.json()

        self.__logger.info("Metadata updated: %s", self.__current_metadata)

    def get_metadata(self):
        self.__logger.info("Fetch metadata[%s]", self.__task)
        response = self.__http_client.get(f"{self.__url}/file/{self.__task}")

        response.raise_for_status()

        self.__current_metadata = response.json()

        self.__logger.info("Metadata fetched")
        return self.__current_metadata

    def download_source_file(self, save_directory):
        self.__logger.info("Fetch available file list")

        response = self.__http_client.get(f"{self.__url}/file/{self.__task}")

        response.raise_for_status()

        file_list = response.json()["files"]
        self.__logger.warning(file_list)

        source_file = next(filter(lambda x: x["category"] == "Source", file_list))

        storage_name = f"{source_file['category']}{source_file['extension']}"
        file_path = f"{save_directory}/{storage_name}"

        self.__logger.info("Download source file")
        with self.__http_client.get(f"{self.__url}/File/{self.__task}/{source_file['id']}", stream=True) as response:
            response.raise_for_status()
            with open(file_path, 'wb') as file:
                shutil.copyfileobj(response.raw, file)

        self.__logger.info("Source file downloaded: %s", file_path)

        return file_path, storage_name

    def upload_file(self, file_path, file_type):
        self.__logger.info("Uploading file: %s", file_path)

        with open(file_path, 'rb') as upload_file:
            files = {'file': upload_file}
            data = {"category": file_type}

            response = self.__http_client.post(f"{self.__url}/file/{self.__task}", files=files, params=data)

            if response.status_code == 409:
                # Skip this error if we run file translation multiple times in debug mode
                self.__logger.warning("File already uploaded")
            else:
                response.raise_for_status()

        self.__logger.info("File upload completed")
