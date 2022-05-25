from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app import mq_connector
from app.api import gec_router

app = FastAPI(
    title="Grammatical Error Correction",
    version="1.0.1",
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


app.include_router(gec_router)
