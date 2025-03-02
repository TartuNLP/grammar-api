from fastapi import APIRouter, Header, HTTPException, status, Response

from . import GECResult, GECResult_v2, GECRequest
from app.services import grammar_service

gec_router = APIRouter()

@gec_router.post('/', response_model=GECResult, description="Submit a GEC request and get correction spans.")
async def grammar(body: GECRequest, response: Response, content_type: str = Header(..., include_in_schema=False)):
    if content_type != "application/json":
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY
        )
    result = grammar_service.process_request(body.text, body.language)
    response.headers['Content-Disposition'] = 'attachment; filename="api.json"'
    return result

@gec_router.post('/v2', response_model=GECResult_v2, description="Submit a GEC request.")
async def grammar_v2(body: GECRequest, response: Response, content_type: str = Header(..., include_in_schema=False)):
    if content_type != "application/json":
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY
        )

    result = grammar_service.process_request_v2(body.text, body.language)
    response.headers['Content-Disposition'] = 'attachment; filename="api.json"'
    return result
