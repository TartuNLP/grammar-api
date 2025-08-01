from typing import Optional
from pydantic import BaseSettings, validator


class APISettings(BaseSettings):
    max_input_length: int = 10000
    languages: str = "et"  # comma-separated list of 2-letter codes
    
    # Ollama server configuration - Individual servers for each model
    gec_ollama_url: str = "http://localhost:11434"  # Grammar Error Correction server
    gee_ollama_url: str = "http://localhost:11435"  # Grammar Error Explanation server
    ged_ollama_url: str = "http://localhost:11436"  # Grammar Error Detection server
    
    # Model names for different tasks
    gec_model: str = "gec"  # Grammar Error Correction model
    gee_model: str = "gee"  # Grammar Error Explanation model  
    ged_model: str = "ged"  # Grammar Error Detection model
    
    version: Optional[str] = None

    @validator('languages')
    def list_languages(cls, v):
        return v.split(',')

    class Config:
        env_prefix = 'api_'
        env_file = '.env'


api_settings = APISettings()
