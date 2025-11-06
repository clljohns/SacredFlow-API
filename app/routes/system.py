# ================================================================
# File: system.py
# Path: app/routes/system.py
# Description: System-level routes including the core health check endpoint.
# Author: Clint Johnson
# Project: SacredFlow API
# ================================================================

from fastapi import APIRouter

router = APIRouter()

@router.get("/health", tags=["system"])
async def health_check():
    return {"status": "ok", "service": "SacredFlow API"}
