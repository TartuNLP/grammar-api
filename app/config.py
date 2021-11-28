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


mq_settings = MQSettings()
