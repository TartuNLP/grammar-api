FROM python:3.8-alpine

# Install system dependencies
RUN apk update && \
    apk add --no-cache \
        gcc \
        libffi-dev \
        musl-dev \
        git

ENV PYTHONIOENCODING=utf-8
ENV CONFIGURATION=production
ENV ROOT_PATH=""
WORKDIR /app

RUN adduser -D app && \
    chown -R app:app /app

USER app
ENV PATH="/home/app/.local/bin:${PATH}"

COPY --chown=app:app config/requirements.txt .
RUN pip install --user -r requirements.txt && \
    rm requirements.txt

COPY --chown=app:app . .

EXPOSE 80

RUN echo \
    "if [ \$CONFIGURATION == \"debug\" ]; \
    then \
      uvicorn app:app --host 0.0.0.0 --port 80 --root-path \$ROOT_PATH --log-config config/logging.debug.ini --proxy-headers; \
    else \
      uvicorn app:app --host 0.0.0.0 --port 80 --root-path \$ROOT_PATH --log-config config/logging.ini --proxy-headers; \
    fi" > entrypoint.sh

ENTRYPOINT ["/bin/sh", "entrypoint.sh"]
