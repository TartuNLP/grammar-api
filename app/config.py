from typing import Optional
from pydantic import BaseSettings, validator


class MQSettings(BaseSettings):
    host: str = 'localhost'
    port: int = 5672
    username: str = 'guest'
    password: str = 'guest'
    exchange: str = 'grammar'
    timeout: int = 60

    class Config:
        env_prefix = 'mq_'


class APISettings(BaseSettings):
    max_input_length: int = 10000
    languages: str = "et"  # comma-separated list of 2-letter codes
    version: Optional[str]

    @validator('languages')
    def list_languages(cls, v):
        return v.split(',')

    class Config:
        env_prefix = 'api_'


mq_settings = MQSettings()
api_settings = APISettings()
