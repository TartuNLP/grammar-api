# Grammatical Error Correction API

An API for using the grammatical error correction (GEC) service with Ollama backend.

### Setup

The API can be deployed using Docker. It acts as a middleware between clients and Ollama-hosted GEC-related models:
- Grammar correction service (GEC)
- Grammar error detection service (GED)  
- Grammar error explanation service (GEE)

The following environment variables can be configured:

#### Ollama Configuration
- `API_GEC_OLLAMA_URL` (optional) - URL for GEC Ollama server (`http://localhost:11434` by default)
- `API_GEE_OLLAMA_URL` (optional) - URL for GEE Ollama server (`http://localhost:11435` by default)
- `API_GED_OLLAMA_URL` (optional) - URL for GED Ollama server (`http://localhost:11436` by default)
- `API_GEC_MODEL` (optional) - Model name for grammar correction (`gec` by default)
- `API_GEE_MODEL` (optional) - Model name for error explanations (`gee` by default)
- `API_GED_MODEL` (optional) - Model name for error detection/logging (`ged` by default)
- `API_MAX_INPUT_LENGTH` (optional) - Maximum request size in characters (`10000` by default)
- `API_LANGUAGES` (optional) - A comma-separated list of supported languages using 2-letter language codes (`et` by default)

### API Endpoints

#### Root Endpoint
- `POST /` - Submit text for grammar correction with span-based corrections
  - Request body:
    ```json
    {
      "language": "et",
      "text": "Your text here"
    }
    ```
  - Response format:
    ```json
    {
      "corrections": [
        {
          "span": {
            "start": 0,
            "end": 13,
            "value": "original text"
          },
          "replacements": [
            {
              "value": "corrected text"
            }
          ]
        }
      ],
      "corrected_text": "Full corrected text"
    }
    ```

#### V2 Endpoint
- `POST /v2` - Submit text for grammar correction with detailed explanations
  - Request body:
    ```json
    {
      "language": "lang_code",
      "text": "Your text here"
    }
    ```
  - Response format:
    ```json
    {
      "corrections": [
        {
          "original": "Original sentence",
          "corrected": "Corrected sentence",
          "correction_log": "Detailed list of corrections",
          "explanations": "Explanation for each correction"
        }
      ]
    }
    ```

### Build Configuration

The entrypoint of the container is `["uvicorn", "app:app", "--host", "0.0.0.0", "--proxy-headers", "--log-config", "logging/logging.ini"]`. `CMD` can be used to define additional [Uvicorn parameters](https://www.uvicorn.org/deployment/). For example, `["--log-config", "logging/debug.ini", "--root-path", "/api/grammar"]` enables debug logging and allows the API to be deployed to the non-root path `/api/grammar`.

The service is available on port `8000`. The API documentation is available under the `/docs` endpoint.

