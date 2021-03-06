from fastapi import APIRouter, Header, HTTPException, status, Response

from . import GECResult, GECRequest
from app import mq_connector

gec_router = APIRouter()


@gec_router.post('/', response_model=GECResult, description="Submit a GEC request.")
async def grammar(body: GECRequest, response: Response, content_type: str = Header(..., include_in_schema=False)):
    if content_type != "application/json":
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY
        )

    result = await mq_connector.publish_request(body, body.language)
    response.headers['Content-Disposition'] = 'attachment; filename="api.json"'
    return result
