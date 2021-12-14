# File Translation Worker

Translates document with external MT translation api and storage for storing metadata and files.
Communication is done by RabbitMQ.

```

 -------------------------------
|                               |
|                               |   ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ←
|   File translation service    |                                                 ↑
|           [Public]            |   → → → → → → → → → → → → → → → → → → → → → →   ↑
|                               |                                             ↓   ↑
 -------------------------------                                              ↓   ↑
                                                                              ↓   ↑
            ↓                                                                 ↓   ↑
            ↓ sends message about new file translation                        ↓   ↑
            ↓ job (via RabbitMQ)                                              ↓   ↑
            ↓                                                                 ↓   ↑
                                                                              ↓   ↑
 -------------------------------                                              ↓   ↑
|                               |   ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ↓   ↑
|   File translation worker     |                                                 ↑
|                               |   → → → → → → → → → → → → → → → → → → → → → → → ↑
 -------------------------------            Stores translated results and metadata
                                            about translation
            ↑   ↓
            ↑   ↓
            ↑   ↓   requests translation
            ↑   ↓   from MT systems
            ↑   ↓
            ↑   ↓
 -------------------------------
|                               |
|       Translation API         |
|                               |
 -------------------------------

```

### Receiveing message from File translation Service via RabbitMQ:

> exchange, queue and binding redirects are created on service startup

| Parameter        | Value            |
| ---------------- | ---------------- |
| exchange         | file-translation |
| exchange type    | fanout           |
| exchange options | durable          |

# Monitor

## Healthcheck probes

https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/

Startup probe / Readiness probe:

`/health/ready`

Liveness probe:

`/health/live`

# Configuration

Environment variable configuration

## RabbitMQ configuration

`RABBITMQ_USER` - RabbitMQ username

`RABBITMQ_PASS` - RabbitMQ password

`RABBITMQ_HOST` - RabbitMQ host

`RABBITMQ_PORT` - RabbitMQ port (Default: 5672) [Optional]

## Translation service environment variables

`FILE_TRANSLATION_SERVICE_URL` - File translation service url

`FILE_TRANSLATION_SERVICE_USER` - inter-service auth username

`FILE_TRANSLATION_SERVICE_PASS` - inter-service auth password

## Local debugging configuraton [OPTIONAL]

All environment variables defined below are for testing purposes only

`RUN_MODE` - Enable local debugging. Run single file translation and exit.

- `simple` - Translate file and exit
- `<Not set>` - (Default) Run service in production mode

`TASK_ID` - (needed only for RUN_MODE=simple) Specify document translation id (Example: 08d96310-7b2d-47e2-8843-34baf47b3599)

# Test

Install prerequisites

```Shell
# install kubectl
choco install kubernetes-cli
# install helm
choco install kubernetes-helm
```

Install RabbitMQ

```Shell
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

# RabbitMQ
helm install rabbitmq --set auth.username=root,auth.password=root,auth.erlangCookie=secretcookie bitnami/rabbitmq
```

forward ports:

```Shell
# RabbitMQ
kubectl port-forward --namespace default svc/rabbitmq 15672:15672 5672:5672
```

Using docker compose

```
# Build and run service
docker-compose up --build
```

# Lint code

```
pip install pylint
pylint ./tildemt -f colorized
```
