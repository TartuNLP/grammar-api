import asyncio
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from gec_service.models import GECResult, GECRequest
from gec_service.mq_connector import MQConnector
from gec_service import settings

app = FastAPI(
    title="Grammatical Error Correction",
    version="0.1.0",
    description="A service that performs automatic grammatical error correction."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

mq_connector = MQConnector(host=settings.MQ_HOST,
                           port=settings.MQ_PORT,
                           username=settings.MQ_USERNAME,
                           password=settings.MQ_PASSWORD,
                           exchange_name=settings.EXCHANGE,
                           message_timeout=settings.MQ_TIMEOUT,
                           loop=asyncio.get_running_loop())


@app.on_event("startup")
async def startup():
    await mq_connector.connect()


@app.on_event("shutdown")
async def shutdown():
    await mq_connector.disconnect()


# TODO content limit?
@app.post('/', response_model=GECResult, description="Submit a GEC request.")
async def gram_check(body: GECRequest):
    correlation_id = str(uuid.uuid4())
    result = await mq_connector.publish_request(correlation_id, body, body.language)
    return result
