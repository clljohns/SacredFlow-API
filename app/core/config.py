import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "SacredFlow API"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./sacredflow.db")
    SQUARE_SECRET_KEY: str = os.getenv("SQUARE_SECRET_KEY", "")
    SLACK_WEBHOOK_URL: str = os.getenv("SLACK_WEBHOOK_URL", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "changeme")
    ENV: str = os.getenv("ENV", "development")

settings = Settings()

