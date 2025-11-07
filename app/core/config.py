# ================================================================
# File: config.py
# Path: app/core/config.py
# Description: Centralizes SacredFlow configuration via Pydantic settings.
# Author: Clint Johnson
# Project: SacredFlow API
# ================================================================

import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# ✅ Ensure environment variables from .env are loaded
#    This must run before Pydantic reads settings.
load_dotenv()


class Settings(BaseSettings):
    # --- Core ---
    APP_NAME: str = "SacredFlow API"
    ENV: str = os.getenv("ENV", "development")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "changeme")

    # --- Database ---
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./sacredflow.db")

    # --- Square Configuration ---
    SQUARE_SECRET_KEY: str = os.getenv("SQUARE_SECRET_KEY", "")
    SQUARE_ENVIRONMENT: str = os.getenv("SQUARE_ENVIRONMENT", "sandbox")
    SQUARE_LOCATION_ID: str = os.getenv("SQUARE_LOCATION_ID", "")
    SQUARE_APPLICATION_ID: str = os.getenv("SQUARE_APPLICATION_ID", "")

    # --- Square Checkout URLs ---
    SQUARE_SUBSCRIPTION_CHECKOUT_URL: str = os.getenv("SQUARE_SUBSCRIPTION_CHECKOUT_URL", "")
    SQUARE_ONE_TIME_CHECKOUT_URL: str = os.getenv("SQUARE_ONE_TIME_CHECKOUT_URL", "")
    SQUARE_FAMILY_CHECKOUT_URL: str = os.getenv("SQUARE_FAMILY_CHECKOUT_URL", "")

    # --- Square Chat ---
    SQUARE_CHAT_WEBHOOK_URL: str = os.getenv("SQUARE_CHAT_WEBHOOK_URL", "")
    SQUARE_CHAT_BEARER_TOKEN: str = os.getenv("SQUARE_CHAT_BEARER_TOKEN", "")

    # --- Inbox / Webhooks ---
    INBOX_FORWARD_WEBHOOK_URL: str = os.getenv("INBOX_FORWARD_WEBHOOK_URL", "")
    INBOX_PUSH_WEBHOOK_URL: str = os.getenv("INBOX_PUSH_WEBHOOK_URL", "")
    PRIMARY_INBOX_EMAIL: str = os.getenv("PRIMARY_INBOX_EMAIL", "")

    # --- Slack / Integrations ---
    SLACK_WEBHOOK_URL: str = os.getenv("SLACK_WEBHOOK_URL", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")

    # --- CORS / Frontend ---
    CORS_ORIGINS: str = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,https://malulaniinnovations.com"
    )


# ✅ Instantiate global settings object
settings = Settings()


# Optional: quick debug utility for local testing
if __name__ == "__main__":
    from pprint import pprint

    print("\n🔍 SacredFlow Configuration Snapshot:")
    pprint({
        "DATABASE_URL": settings.DATABASE_URL,
        "SQUARE_ENVIRONMENT": settings.SQUARE_ENVIRONMENT,
        "SQUARE_SUBSCRIPTION_CHECKOUT_URL": settings.SQUARE_SUBSCRIPTION_CHECKOUT_URL,
        "SQUARE_ONE_TIME_CHECKOUT_URL": settings.SQUARE_ONE_TIME_CHECKOUT_URL,
        "SQUARE_FAMILY_CHECKOUT_URL": settings.SQUARE_FAMILY_CHECKOUT_URL,
        "CORS_ORIGINS": settings.CORS_ORIGINS,
    })
    print()
