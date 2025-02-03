from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Social Media Upload API"
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # OpenAI
    OPENAI_API_KEY: str
    
    # Social Media Credentials
    YOUTUBE_CLIENT_ID: str
    YOUTUBE_CLIENT_SECRET: str
    INSTAGRAM_ACCESS_TOKEN: str
    TIKTOK_ACCESS_TOKEN: str
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()
