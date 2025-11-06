# ================================================================
# File: app/main.py
# Description: FastAPI entry point for SacredFlow API
# Author: Clint Johnson
# Project: SacredFlow API
# Created: 2025-11-06
# ================================================================

from fastapi import FastAPI
from app.routes import system, square, slack, analytics, db_check

# ---------------------------------------------------------------
# 🧠 Initialize FastAPI App
# ---------------------------------------------------------------
app = FastAPI(
    title="SacredFlow API",
    description="Spiritual flow management backend — powered by FastAPI",
    version="1.0.0"
)

# ---------------------------------------------------------------
# 🧠 Include API Routers
# ---------------------------------------------------------------
app.include_router(system.router)
app.include_router(square.router)
app.include_router(slack.router)
app.include_router(analytics.router)
app.include_router(db_check.router)  # ✅ New DB health check route

# ---------------------------------------------------------------
# 🧠 Root Endpoint
# ---------------------------------------------------------------
@app.get("/", summary="Root endpoint")
async def root():
    """
    Returns a simple status message confirming that the API is alive.
    """
    return {"message": "SacredFlow API is alive 🔮"}
