import logging
import asyncio
import os
import json
import aio_pika

from aio_pika import ExchangeType
from tildemt.translator import Translator

# Exchange, type: Direct
RABBITMQ_EXCHANGE = "file-translation"
#
RABBITMQ_QUEUE = RABBITMQ_EXCHANGE
#
RABBITMQ_ROUTING_KEY = RABBITMQ_QUEUE
# User friendly name for RabbitMQ management console
SERVICE_NAME = "File translation worker"


class RabbitMQ():
    def __init__(self):
        self.__logger = logging.getLogger('RabbitMQ')

        self.__username = os.environ.get("RABBITMQ_USER")
        self.__password = os.environ.get("RABBITMQ_PASS")
        self.__host = os.environ.get("RABBITMQ_HOST")
        self.__port = int(os.environ.get("RABBITMQ_PORT", "5672"))

    async def _healthy(self, loop):
        try:
            connection = await aio_pika.connect(
                host=self.__host,
                port=self.__port,
                login=self.__username,
                password=self.__password,
                loop=loop,
                # https://github.com/mosquito/aio-pika/issues/301
                client_properties={"client_properties": {
                    "connection_name": f"{SERVICE_NAME} (health probe)"
                }}
            )

            logging.disable(logging.DEBUG)
            await connection.close()
            logging.disable(logging.NOTSET)

            return True

        except Exception as ex:
            self.__logger.exception(ex, "Failed to connect to RabbitMQ")

            return False

    def healthy(self):
        loop = asyncio.new_event_loop()
        healthy = loop.run_until_complete(self._healthy(loop))
        loop.close()
        return healthy

    def listen(self):
        loop = asyncio.new_event_loop()
        while True:
            try:
                loop.run_until_complete(self.__main_loop(loop))
            except Exception:
                self.__logger.exception("Unexpected exception, trying to restart consumer")

    def __process_message(self, message):
        try:
            message_body = json.loads(message)

            self.__logger.info(" =========== RabbitMQ work item received: '%s' ===========", message_body)

            translator = Translator(message_body["task"])

            translator.translate()
        except Exception:
            self.__logger.error("Failed to process task")

    async def __main_loop(self, loop):

        connection = await aio_pika.connect_robust(
            host=self.__host,
            port=self.__port,
            login=self.__username,
            password=self.__password,
            loop=loop,
            # https://github.com/mosquito/aio-pika/issues/301
            client_properties={"client_properties": {
                "connection_name": SERVICE_NAME
            }}
        )

        async with connection:
            channel = await connection.channel()
            await channel.set_qos(prefetch_count=1)

            exchange = await channel.declare_exchange(RABBITMQ_EXCHANGE, ExchangeType.FANOUT, durable=True)

            queue = await channel.declare_queue(RABBITMQ_QUEUE, auto_delete=False, durable=True)
            await queue.bind(exchange, routing_key=RABBITMQ_ROUTING_KEY)

            self.__logger.info("RabbitMQ ready for messages")

            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        self.__process_message(message.body)
