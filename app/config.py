from pydantic import BaseSettings


class MQSettings(BaseSettings):
    host: str = 'localhost'
    port: int = 5672
    username: str = 'guest'
    password: str = 'guest'
    exchange: str = 'grammar'
    timeout: int = 30000

    class Config:
        env_prefix = 'mq_'


class APISettings(BaseSettings):
    max_input_length: int = 10000

    class Config:
        env_prefix = 'api_'


mq_settings = MQSettings()
api_settings = APISettings()
