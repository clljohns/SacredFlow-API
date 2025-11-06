from fastapi import APIRouter, Request
from app.core.config import settings
import httpx

router = APIRouter()

@router.post("/square/webhook", tags=["square"])
async def handle_square(request: Request):
    payload = await request.json()
    # Placeholder for signature verification & handling
    return {"received": True, "data": payload}

