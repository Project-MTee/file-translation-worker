import logging
import os
import threading

from waitress import serve
from flask import Flask
from flask_healthz import healthz
from flask_healthz import HealthError

from tildemt.rabbitmq import RabbitMQ
from tildemt.translator import Translator

ready_checks = []


def liveness():
    pass


def readiness():
    for check in ready_checks:
        if not check():
            raise HealthError("Unhealthy")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s [%(name)s:%(funcName)s:%(lineno)d] %(message)s"
    )

    run_mode = os.environ.get("RUN_MODE")

    logger = logging.getLogger('Worker')
    logger.info("Initialize...")

    if run_mode == "simple":
        logger.info("Run plain translator test")

        translator = Translator(os.environ.get("TASK_ID"))
        translator.translate()
    else:
        # Rabbit will block thread so, start in seperate thread
        rabbit = RabbitMQ()
        rabbit_thread = threading.Thread(target=rabbit.listen)
        rabbit_thread.start()

        # Serve healthcheck endpoints
        ready_checks.append(rabbit.healthy)

        app = Flask(__name__)
        app.register_blueprint(healthz, url_prefix="/health")
        app.config.update(HEALTHZ={
            "live": liveness,
            "ready": readiness,
        })
        serve(app, port=5000)
