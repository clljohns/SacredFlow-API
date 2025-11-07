# ================================================================
# File: monitoring.py
# Path: app/routes/monitoring.py
# Description: Exposes health/metrics endpoints and registers Prometheus probes.
# Author: Clint Johnson
# Project: SacredFlow API
# ================================================================

import time
from fastapi import APIRouter
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_fastapi_instrumentator.metrics import Info
from prometheus_client import Summary, Histogram
from sqlalchemy import event
from app.core.database import engine

# -------------------- Prometheus Metrics --------------------
REQUEST_LATENCY = Histogram(
    "sacredflow_request_latency_seconds",
    "Latency of HTTP requests in seconds",
    ["method", "path"],
)

DB_QUERY_TIME = Summary(
    "sacredflow_db_query_seconds",
    "Time spent executing SQL queries",
)

# ----------------- SQLAlchemy Timing Hooks ------------------
@event.listens_for(engine.sync_engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault("query_start_time", []).append(time.time())

@event.listens_for(engine.sync_engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    start_time = conn.info["query_start_time"].pop(-1)
    DB_QUERY_TIME.observe(time.time() - start_time)

# --------------- FastAPI Router: /health only ---------------
router = APIRouter(prefix="", tags=["Monitoring"])

@router.get("/health", summary="Health check endpoint")
async def health_check():
    return {"status": "ok", "service": "SacredFlow API", "uptime": "✅ healthy"}

# -------------- Instrumentator (custom callback) ------------
def _resolve_path(info: Info) -> str:
    """Prometheus instrumentation Info doesn't always expose `.path` depending on version."""
    if hasattr(info, "modified_path") and info.modified_path:
        return info.modified_path
    if hasattr(info, "path") and info.path:
        return info.path
    if hasattr(info, "request") and info.request:
        try:
            return info.request.url.path
        except Exception:
            pass
    scope = getattr(info, "scope", None) or {}
    if isinstance(scope, dict):
        return scope.get("path") or scope.get("raw_path") or "unknown"
    return "unknown"


def _resolve_method(info: Info) -> str:
    if hasattr(info, "method") and info.method:
        return info.method
    scope = getattr(info, "scope", None) or {}
    if isinstance(scope, dict) and scope.get("method"):
        return scope["method"]
    return "UNKNOWN"


def record_latency(info: Info) -> None:
    path = _resolve_path(info)
    method = _resolve_method(info)
    latency = next(
        (
            value
            for value in (
                getattr(info, "latency", None),
                getattr(info, "modified_duration", None),
                getattr(info, "duration", None),
                getattr(info, "modified_duration_without_streaming", None),
            )
            if value is not None
        ),
        0.0,
    )
    REQUEST_LATENCY.labels(method=method, path=path).observe(latency)

instrumentator = Instrumentator().add(record_latency)
