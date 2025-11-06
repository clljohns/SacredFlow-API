# ================================================================
# File: security.py
# Path: app/core/security.py
# Description: Lightweight API key guard utilities for SacredFlow endpoints.
# Author: Clint Johnson
# Project: SacredFlow API
# ================================================================

from fastapi import Request, HTTPException
from fastapi.security.api_key import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(request: Request, api_key: str = None):
    expected_key = request.app.state.secret_key
    if expected_key and api_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
