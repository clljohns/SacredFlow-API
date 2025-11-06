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
def record_latency(info: Info) -> None:
    # Some versions use `modified_path` when grouping paths
    path = getattr(info, "modified_path", info.path)
    REQUEST_LATENCY.labels(method=info.method, path=path).observe(info.latency)

instrumentator = Instrumentator().add(record_latency)
