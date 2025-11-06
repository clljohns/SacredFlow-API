from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from alembic import context
from app.models import Base
from app.core.database import engine

config = context.config
fileConfig(config.config_file_name)
target_metadata = Base.metadata

def run_migrations_online():
    import asyncio
    async def do_run_migrations():
        async with engine.begin() as conn:
            await conn.run_sync(target_metadata.create_all)
    asyncio.run(do_run_migrations())

run_migrations_online()
