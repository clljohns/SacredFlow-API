# ================================================================
# File: system.py
# Path: app/routes/system.py
# Description: System-level routes including the core health check endpoint.
# Author: Clint Johnson
# Project: SacredFlow API
# ================================================================

from fastapi import APIRouter

from app.core.square import square_healthcheck

router = APIRouter()

@router.get("/health", tags=["system"])
async def health_check():
    square_status = await square_healthcheck()
    return {
        "status": "ok",
        "service": "SacredFlow API",
        "square": square_status,
    }
