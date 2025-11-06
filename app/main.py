# ================================================================
# File: main.py
# Path: app/main.py
# Description: FastAPI entry point that wires SacredFlow routers and monitoring.
# Author: Clint Johnson
# Project: SacredFlow API
# ================================================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.proxy_headers import ProxyHeadersMiddleware
from app.core.config import settings
from app.routes import analytics, communications, db_check, slack, square, system

# ---------------------------------------------------------------
# 🧠 Initialize FastAPI App
# ---------------------------------------------------------------
app = FastAPI(
    title="SacredFlow API",
    description="Spiritual flow management backend — powered by FastAPI",
    version="1.0.0"
)

# ---------------------------------------------------------------
# 🧠 CORS Configuration
# ---------------------------------------------------------------
default_cors_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://malulani.co",
]

cors_origins = [
    origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()
] if settings.CORS_ORIGINS else default_cors_origins

# Ensure the original client scheme/host from Render's proxy is respected
# before applying redirect/CORS logic.
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"])

app.add_middleware(HTTPSRedirectMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------
# 🧠 Include API Routers
# ---------------------------------------------------------------
app.include_router(system.router)
app.include_router(square.router)
app.include_router(slack.router)
app.include_router(analytics.router)
app.include_router(communications.router)
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

# ============================================================
# Monitoring Integration
# ============================================================
from app.routes.monitoring import router as monitoring_router, instrumentator
app.include_router(monitoring_router)
instrumentator.instrument(app).expose(app)
