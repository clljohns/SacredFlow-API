# ================================================================
# File: database.py
# Path: app/core/database.py
# Description: Configures the async SQLAlchemy engine and session dependency.
# Author: Clint Johnson
# Project: SacredFlow API
# ================================================================

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

# ---------------------------------------------------------------
# 🧠 Database Engine Setup
# Using asyncpg driver for PostgreSQL connections
# ---------------------------------------------------------------
engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=False,
    future=True
)

# ---------------------------------------------------------------
# 🧠 Session Factory
# Each request gets its own async database session
# ---------------------------------------------------------------
async_session_factory = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession
)

# ---------------------------------------------------------------
# 🧠 Dependency Injection (used in FastAPI routes)
# Provides a session that auto-closes after use
# ---------------------------------------------------------------
async def get_session() -> AsyncSession:
    async with async_session_factory() as session:
        yield session
