# ================================================================
# File: db_check.py
# Path: app/routes/db_check.py
# Description: Diagnostics route verifying database connectivity and fetching rows.
# Author: Clint Johnson
# Project: SacredFlow API
# ================================================================

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import get_session

# Router instance for modular route management
router = APIRouter(prefix="/db-check", tags=["Diagnostics"])

@router.get("/", summary="Verify database connectivity")
async def db_check(session: AsyncSession = Depends(get_session)):
    """
    Test endpoint to confirm database connection and query execution.

    Returns:
        JSON object containing rows from 'test_table' if the database is live.
    """
    result = await session.execute(text("SELECT * FROM test_table"))
    rows = result.fetchall()
    return {"rows": [dict(row._mapping) for row in rows]}
