FROM python:3.10-slim

ARG DEBIAN_FRONTEND=noninteractive

# Set the locale
RUN apt update &&\
    DEBIAN_FRONTEND=noninteractive apt install -y locales &&\
    sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen &&\
    dpkg-reconfigure --frontend=noninteractive locales &&\
    update-locale LANG=en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LC_ALL en_US.UTF-8

# Install JAVA Dependency for tikal tool
RUN apt install -y default-jre

RUN apt install -y perl

# Linux file command
RUN apt install -y file

# Python dependencies
RUN pip3 install \
    # general
    requests \
    # .docx translation
    lxml \
    # rabbitmq client
    aio-pika \
    # For health check
    waitress \
    flask \
    flask-healthz

# add non root user
RUN groupadd -r service_user && useradd -m --no-log-init -r -g service_user service_user

COPY external_libs/ /usr/local/lib/

WORKDIR /usr/lib/tildemt

# Copy scripts
COPY scripts scripts

COPY tildemt src

# Register tildemt package so that source files use absolute imports
RUN ln -s /usr/lib/tildemt/src /usr/local/lib/python3.10/site-packages/tildemt

USER service_user

ENTRYPOINT ["python3", "/usr/lib/tildemt/src/main.py"]
