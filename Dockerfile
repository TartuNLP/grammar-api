FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libffi-dev \
    musl-dev \
    git \
    build-essential \
    swig \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONIOENCODING=utf-8
WORKDIR /app

RUN useradd -m app
USER app
ENV PATH="/home/app/.local/bin:${PATH}"

COPY --chown=app:app requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

COPY --chown=app:app . .

ARG API_VERSION
ENV API_VERSION=$API_VERSION

EXPOSE 8000

ENTRYPOINT ["uvicorn", "app:app", "--host", "0.0.0.0", "--proxy-headers", "--log-config", "logging/logging.ini"]
