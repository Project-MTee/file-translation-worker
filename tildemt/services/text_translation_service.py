import datetime
import time
import logging
import os
import multiprocessing
from concurrent.futures.thread import ThreadPoolExecutor
from concurrent.futures import CancelledError
import requests

from tildemt.enums.text_translation_type import TextTranslationType


class TextTranslationService():
    def __init__(self, source_language, target_language, domain):
        self.__logger = logging.getLogger("TextTranslationService")
        self.__url = os.environ.get("TRANSLATION_API_SERVICE_URL")
        # Parralel requests
        self.__concurrency = 1
        # max characters in batch
        self.__max_batch_characters = 500
        # Retry count (For unexpected errors - not for timeout)
        self.__retries = 5
        # If timeout happens at translation, then translation is busy processing messages, maybe we need to wait a little
        # (In seconds)
        self.__timeout_cooldown = self.__concurrency * 3
        # Service halted
        self.__halted = False
        # If timeout happens all the time then we need to stop sometime
        self.__current_consecutive_failed_requests = 0
        self.__max_consecutive_failed_requests = self.__concurrency * 3
        multiprocess_manager = multiprocessing.Manager()
        self.__lock_edit = multiprocess_manager.Lock()

        self.__source_language = source_language
        self.__target_language = target_language

        # We need domain to translate, domain will be extracted from translation api response
        self.domain = domain

    def translate(self, segments):
        batches = self.__get_batches(segments)

        if not self.domain:
            self.__logger.info("Domain is not provided, autodetect it from first batch")
            # Acquire domain by translating one batch of text
            first_batch = batches[0]
            batches = batches[1:]

            first_batch_result = self.__translate_segment(first_batch)

            for segment_result in first_batch_result:
                yield segment_result

        self.__logger.info("Start translation of all batches")

        with ThreadPoolExecutor(max_workers=self.__concurrency) as executor:
            futures = [executor.submit(self.__translate_segment, batch) for batch in batches]

            for future in futures:
                if self.__halted:
                    cancelled_futures = 0
                    for future_ob in futures:
                        cancelled = future_ob.cancel()
                        if cancelled:
                            cancelled_futures += 1

                    futures = None

                    self.__logger.debug("Cancelled futures: %d", cancelled_futures)

                    break

                try:
                    future_exception = future.exception()
                    if future_exception:
                        self.stop()
                        raise Exception(future_exception)

                except CancelledError:
                    # Swallow future cancellation error
                    self.__logger.info("Future cancelled")

                for segment_result in future.result():
                    yield segment_result

        executor.shutdown(wait=True)

    def stop(self):
        self.__logger.debug("Cancel translation")
        self.__halted = True

    def __get_batches(self, segments):
        result = []
        batch = []
        batch_characters = 0

        for _i, segment in enumerate(segments):
            segment_characters = len(segment)

            if batch_characters + segment_characters > self.__max_batch_characters:
                if batch_characters == 0:
                    batch.append(segment)
                    result.append(batch)
                    batch = []
                else:
                    result.append(batch)
                    batch = [segment]
                    batch_characters = segment_characters
            else:
                batch_characters += segment_characters
                batch.append(segment)

        if batch:
            # add last batch
            result.append(batch)

        return result

    def __translate_segment(self, batch):
        i = 0
        while i < self.__retries:
            response = None

            with self.__lock_edit:
                if self.__current_consecutive_failed_requests < self.__max_consecutive_failed_requests:
                    if self.__current_consecutive_failed_requests > 0:
                        self.__logger.warning(
                            "Consecutive timeout errors: %d/%d",
                            self.__current_consecutive_failed_requests,
                            self.__max_consecutive_failed_requests
                        )
                else:
                    raise Exception("Consecutive request timeout exception limit reached")
            try:
                if self.__halted:
                    return None

                start_time = datetime.datetime.utcnow()
                if i == 0:
                    self.__logger.info("Request translation batch, segments: %s", len(batch))
                    self.__logger.debug("Translation batch contents: %s", batch)
                else:
                    self.__logger.info("Retry translation request: %d/%d", i, self.__retries)

                response = requests.post(
                    f"{self.__url}/Text",
                    json={
                        "srcLang": self.__source_language,
                        "trgLang": self.__target_language,
                        "domain": self.domain,
                        "text": batch,
                        "textType": TextTranslationType.DOCUMENT.value
                    }
                )

                if response.status_code == 504:
                    self.__logger.warning("Translation timed out, waiting reshedule: %ss", self.__timeout_cooldown)
                    time.sleep(self.__timeout_cooldown)
                    self.__logger.warning("Cooldown ended")

                    with self.__lock_edit:
                        self.__current_consecutive_failed_requests += 1

                    continue

                with self.__lock_edit:
                    self.__current_consecutive_failed_requests = 0

                response.raise_for_status()

                response_data = response.json()
                translated_batch = response_data['translations']

                if not self.domain:
                    self.domain = response_data['domain']
                    self.__logger.info("Domain auto detected from text: %s", self.domain)

                results = [
                    self.__format_translation_result(translated_batch['translation'])
                    for translated_batch in translated_batch
                ]

                self.__logger.info("Translation received in %s", datetime.datetime.utcnow() - start_time)
                self.__logger.debug("Translation result: %s", results)

                return results

            except Exception as ex:
                self.__logger.warning("Translation retry error: %d/%d, error: %s", i, self.__retries, ex)
                if response:
                    self.__logger.warning(
                        "Translation error, status: %d message: %s",
                        response.status_code,
                        response.text
                    )
                if i + 1 == self.__retries:
                    self.__logger.error("Failed to translate batch with retries")
                    raise

            i = i + 1
        return None

    @staticmethod
    def __format_translation_result(translation):
        return {'translation': translation}
