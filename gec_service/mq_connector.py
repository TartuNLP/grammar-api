import logging
import json
from asyncio import AbstractEventLoop

from aio_pika import ExchangeType, Message, IncomingMessage, connect_robust
from pydantic import BaseModel

LOGGER = logging.getLogger(__name__)


class MQConnector:
    def __init__(self, host: str, port: int, username: str, password: str, exchange_name: str, message_timeout: int,
                 loop: AbstractEventLoop):
        """
        Initializes a RabbitMQ connector class used for publishing requests using the relevant routing key and
        receiving a response.
        """
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self.message_timeout = message_timeout
        self.exchange_name = exchange_name

        self.futures = {}
        self.loop = loop

        self.connection = None
        self.channel = None
        self.exchange = None

        self.callback_queue = None

    async def connect(self):
        self.connection = await connect_robust(host=self._host,
                                               port=self._port,
                                               login=self._username,
                                               password=self._password)
        self.channel = await self.connection.channel()
        self.exchange = await self.channel.declare_exchange(self.exchange_name, ExchangeType.DIRECT)
        self.callback_queue = await self.channel.declare_queue(exclusive=True)

        await self.callback_queue.consume(self.on_response)

    async def disconnect(self):
        await self.connection.close()

    def on_response(self, message: IncomingMessage):
        LOGGER.info(f"Received response for request: {{id: {message.correlation_id}}}")
        future = self.futures.pop(message.correlation_id)
        future.set_result(json.loads(message.body))
        LOGGER.debug(f"Response for {message.correlation_id}: {json.loads(message.body)}")

    async def publish_request(self, correlation_id: str, body: BaseModel, language: str):
        """
        Publishes the request to RabbitMQ.
        """
        future = self.loop.create_future()
        self.futures[correlation_id] = future

        body = body.json().encode()
        await self.exchange.publish(
            Message(
                body,
                correlation_id=correlation_id,
                expiration=self.message_timeout,
                reply_to=self.callback_queue.name
            ),
            routing_key=f"{self.exchange_name}.{language}"
        )
        LOGGER.info(f"Sent request: {{id: {correlation_id}, routing_key: {self.exchange_name}.{language}}}")
        LOGGER.debug(f"Request {correlation_id} content: {{id: {correlation_id}}}")

        response = await future

        return response
