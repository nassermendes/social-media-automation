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
    
    # Google Cloud
    GOOGLE_CLOUD_PROJECT: str
    GCP_BUCKET_NAME: str
    GOOGLE_APPLICATION_CREDENTIALS: str
    
    # Instagram API App Credentials
    INSTAGRAM_APP_ID: str
    INSTAGRAM_APP_SECRET: str
    INSTAGRAM_CHARITY_USER_ID: str
    
    # YouTube API Credentials
    YOUTUBE_CLIENT_ID: str
    YOUTUBE_CLIENT_SECRET: str
    
    # TikTok API App Credentials
    TIKTOK_APP_KEY: str
    TIKTOK_APP_SECRET: str
    
    # TikTok Personal Account
    TIKTOK_PERSONAL_CLIENT_KEY: str
    TIKTOK_PERSONAL_CLIENT_SECRET: str
    TIKTOK_PERSONAL_ACCESS_TOKEN: str
    
    # TikTok Charity Account
    TIKTOK_CHARITY_CLIENT_KEY: str
    TIKTOK_CHARITY_CLIENT_SECRET: str
    TIKTOK_CHARITY_ACCESS_TOKEN: str
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()
