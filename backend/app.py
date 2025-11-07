import os
from typing import List

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import conversations, customers, messages

load_dotenv()

app = FastAPI(title="SacredFlow Chat Service")

allowed_origins_env = os.getenv("BACKEND_CORS_ORIGINS", "")
allowed_origins: List[str] = (
    [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]
    if allowed_origins_env
    else ["http://localhost:5173"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(messages.router)
app.include_router(conversations.router)
app.include_router(customers.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
