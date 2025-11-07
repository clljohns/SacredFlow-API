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
# ⚙️ Database Engine Setup
# Using asyncpg driver for PostgreSQL connections
# ---------------------------------------------------------------
engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=False,
    future=True
)

# ---------------------------------------------------------------
# 🧠 Session Factory (global)
# Provides async session instances for database operations
# ---------------------------------------------------------------
async_session_maker = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession
)

# ---------------------------------------------------------------
# 💉 FastAPI Dependency
# Yields a scoped async session per request and ensures cleanup
# ---------------------------------------------------------------
async def get_session() -> AsyncSession:
    async with async_session_maker() as session:
        yield session
