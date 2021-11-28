import uuid

from fastapi import APIRouter

from . import GECResult, GECRequest
from app import mq_connector

gec_router = APIRouter()


# TODO content limit?
@gec_router.post('/', response_model=GECResult, description="Submit a GEC request.")
async def grammar(body: GECRequest):
    correlation_id = str(uuid.uuid4())
    result = await mq_connector.publish_request(correlation_id, body, body.language)
    return result
