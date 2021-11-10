# Grammatical Error Correction API

An API for using the grammatical error correction (GEC) service.

### Setup

The API can be deployed using the docker image published alongside the repository. Each image version correlates to a
specific release. The API is designed to work together with our
[GEC worker](https://github.com/TartuNLP/grammar-worker) worker containers and a RabbitMQ message broker.

The following environment variables should be specified when running the container:

- `MQ_USERNAME` - RabbitMQ username
- `MQ_PASSWORD` - RabbitMQ user password
- `MQ_HOST` - RabbitMQ host
- `MQ_PORT` (optional) - RabbitMQ port (`5672` by default)
- `MQ_TIMEOUT` (optional) - Message timeout in seconds (`30` by default)
- `CONFIGURATION` (optional) - if value is `debug` logging will be more detailed, this value should not be used in
  production environments where user input should not be logged.

The service is available on port `80`. The API documentation is available under the `\docs` endpoint.

The RabbitMQ connection parameters are set with environment variables. Exchange name `grammar` will be used and requests
will be sent to the worker using the routing key `grammar.{lang}` where `{lang}` refers to the 2-letter ISO langauge
code (for example `grammar.et`).

The setup can be tested with the following sample `docker-compose.yml` configuration:

```
version: '3'
services:
  rabbitmq:
    image: 'rabbitmq:3.6-alpine'
    environment:
      - RABBITMQ_DEFAULT_USER=${RABBITMQ_USER}
      - RABBITMQ_DEFAULT_PASS=${RABBITMQ_PASS}
  grammar_api:
    image: ghcr.io/tartunlp/grammar-api:latest
    environment:
      - MQ_HOST=rabbitmq
      - MQ_PORT=5672
      - MQ_USERNAME=${RABBITMQ_USER}
      - MQ_PASSWORD=${RABBITMQ_PASS}
    ports:
      - '80:80'
    depends_on:
      - rabbitmq
  grammar_worker:
    image: ghcr.io/tartunlp/grammar-worker:latest
      - MQ_HOST=rabbitmq
      - MQ_PORT=5672
      - MQ_USERNAME=${RABBITMQ_USER}
      - MQ_PASSWORD=${RABBITMQ_PASS}
    depends_on:
      - rabbitmq
```
