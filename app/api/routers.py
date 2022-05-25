from fastapi import APIRouter, Depends, Header, HTTPException, status

from . import GECResult, GECRequest
from app import mq_connector

gec_router = APIRouter()


@gec_router.post('/', response_model=GECResult, description="Submit a GEC request.")
async def grammar(body: GECRequest, content_type: str = Header(...)):
    if content_type != "application/json":
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY
        )

    result = await mq_connector.publish_request(body, body.language)
    return result
