import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app import mq_connector, api_settings
from app.api import gec_router

app = FastAPI(
    title="Grammatical Error Correction",
    version=api_settings.version,
    description="A service that performs automatic grammatical error correction."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


@app.middleware("http")
async def add_cache_control_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    return response


@app.on_event("startup")
async def startup():
    await mq_connector.connect()


@app.on_event("shutdown")
async def shutdown():
    await mq_connector.disconnect()


@app.get('/health/readiness', include_in_schema=False)
@app.get('/health/startup', include_in_schema=False)
@app.get('/health/liveness', include_in_schema=False)
async def health_check():
    # Returns 200 the connection to RabbitMQ is up
    if mq_connector.channel is None or mq_connector.channel.is_closed:
        raise HTTPException(500)
    return "OK"


class EndpointFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.getMessage().find("/health") == -1


# Filter out /endpoint
logging.getLogger("uvicorn.access").addFilter(EndpointFilter())

app.include_router(gec_router)
