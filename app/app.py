from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import mq_connector
from app.api import gec_router

app = FastAPI(
    title="Grammatical Error Correction",
    version="0.1.1",
    description="A service that performs automatic grammatical error correction."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


@app.on_event("startup")
async def startup():
    await mq_connector.connect()


@app.on_event("shutdown")
async def shutdown():
    await mq_connector.disconnect()


app.include_router(gec_router)
