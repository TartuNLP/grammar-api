from typing import Optional
from pydantic import BaseSettings, validator


class APISettings(BaseSettings):
    max_input_length: int = 10000
    languages: str = "et"  # comma-separated list of 2-letter codes
    gec_url: str = "https://mgc.hpc.ut.ee/v1/completions"
    m2_url: str = "http://artemis20.hpc.ut.ee:8000/v1/completions"
    explanation_url: str = "http://artemis20.hpc.ut.ee:8001/v1/completions"
    auth_username: str
    auth_password: str
    version: Optional[str]

    @validator('languages')
    def list_languages(cls, v):
        return v.split(',')

    class Config:
        env_prefix = 'api_'
        env_file = '.env'


api_settings = APISettings()
