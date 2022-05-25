import uuid
import os
import logging
import asyncio
import json

from fastapi import HTTPException
from pydantic import BaseModel
from aio_pika import ExchangeType, Message, connect_robust
from aio_pika.abc import AbstractIncomingMessage

from app import mq_settings

LOGGER = logging.getLogger(__name__)


def uuid4():
    """Cryptographycally secure UUID generator."""
    return uuid.UUID(bytes=os.urandom(16), version=4)


class MQConnector:
    def __init__(self):
        self.futures = {}
        self.loop = asyncio.get_running_loop()

        self.connection = None
        self.channel = None
        self.exchange = None
        self.callback_queue = None

    async def connect(self):
        self.connection = await connect_robust(
            host=mq_settings.host,
            port=mq_settings.port,
            login=mq_settings.username,
            password=mq_settings.password
        )
        self.channel = await self.connection.channel()
        self.exchange = await self.channel.declare_exchange(mq_settings.exchange, ExchangeType.DIRECT)
        self.callback_queue = await self.channel.declare_queue(exclusive=True)

        await self.callback_queue.consume(self.on_response)

    async def disconnect(self):
        await self.callback_queue.delete()
        await self.connection.close()

    def on_response(self, message: AbstractIncomingMessage):
        if message.correlation_id in self.futures:
            LOGGER.info(f"Received response for request: {{id: {message.correlation_id}}}")
            future = self.futures.pop(message.correlation_id)
            future.set_result(json.loads(message.body))
            LOGGER.debug(f"Response for {message.correlation_id}: {json.loads(message.body)}")
        else:
            LOGGER.warning(f"Response received after message timeout: {{id: {message.correlation_id}}}")
        message.ack()

    async def publish_request(self, body: BaseModel, language: str):
        """
        Publishes the request to RabbitMQ.
        """
        correlation_id = str(uuid4())
        future = self.loop.create_future()
        self.futures[correlation_id] = future

        body = body.json().encode()
        message = Message(
            body,
            content_type='application/json',
            correlation_id=correlation_id,
            expiration=mq_settings.timeout,
            reply_to=self.callback_queue.name
        )

        try:
            await self.exchange.publish(message, routing_key=f"{mq_settings.exchange}.{language}")
        except Exception as e:
            LOGGER.exception(e)
            LOGGER.info("Attempting to restore the channel.")
            await self.channel.reopen()
            await self.exchange.publish(message, routing_key=f"{mq_settings.exchange}.{language}")

        LOGGER.info(f"Sent request: {{id: {correlation_id}, routing_key: {mq_settings.exchange}.{language}}}")
        LOGGER.debug(f"Request {correlation_id} content: {{id: {correlation_id}}}")
        try:
            response = await asyncio.wait_for(future, timeout=mq_settings.timeout/1000)
        except asyncio.TimeoutError:
            LOGGER.info(f"Request timed out: {{id: {message.correlation_id}}}")
            self.futures.pop(message.correlation_id)
            raise HTTPException(408)

        return response


mq_connector = MQConnector()
