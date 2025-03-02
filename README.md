# Grammatical Error Correction API

An API for using the grammatical error correction (GEC) service.

### Setup

The API can be deployed using Docker. It acts as a middleware between clients and various GEC-related services:
- Grammar correction service
- M2 format generation service
- Explanation generation service

The following environment variables can be configured:

- `API_MAX_INPUT_LENGTH` (optional) - Maximum request size in characters (`10000` by default)
- `API_LANGUAGES` (optional) - A comma-separated list of supported languages using 2-letter language codes (`et` by default)
- `API_GEC_URL` (optional) - URL for the grammar correction service (`https://mgc.hpc.ut.ee/v1/completions` by default)
- `API_M2_URL` (optional) - URL for the M2 format generation service (`http://artemis20.hpc.ut.ee:8000/v1/completions` by default)
- `API_EXPLANATION_URL` (optional) - URL for the explanation service (`http://artemis20.hpc.ut.ee:8001/v1/completions` by default)
- `API_AUTH_USERNAME` - Username for service authentication
- `API_AUTH_PASSWORD` - Password for service authentication

### API Endpoints

#### Main Endpoint
- `POST /` - Submit text for grammar correction
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

