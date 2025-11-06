# ================================================================
# File: config.py
# Path: app/core/config.py
# Description: Centralizes SacredFlow configuration via Pydantic settings.
# Author: Clint Johnson
# Project: SacredFlow API
# ================================================================

import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "SacredFlow API"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./sacredflow.db")
    SQUARE_SECRET_KEY: str = os.getenv("SQUARE_SECRET_KEY", "")
    SQUARE_CHAT_WEBHOOK_URL: str = os.getenv("SQUARE_CHAT_WEBHOOK_URL", "")
    SQUARE_CHAT_BEARER_TOKEN: str = os.getenv("SQUARE_CHAT_BEARER_TOKEN", "")
    INBOX_FORWARD_WEBHOOK_URL: str = os.getenv("INBOX_FORWARD_WEBHOOK_URL", "")
    INBOX_PUSH_WEBHOOK_URL: str = os.getenv("INBOX_PUSH_WEBHOOK_URL", "")
    PRIMARY_INBOX_EMAIL: str = os.getenv("PRIMARY_INBOX_EMAIL", "")
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "")
    SLACK_WEBHOOK_URL: str = os.getenv("SLACK_WEBHOOK_URL", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "changeme")
    ENV: str = os.getenv("ENV", "development")

settings = Settings()
