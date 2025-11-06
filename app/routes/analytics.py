from fastapi import APIRouter, Request
from app.core.config import settings
import httpx

router = APIRouter()

@router.post("/analytics/event", tags=["analytics"])
async def track_event(request: Request):
    event = await request.json()
    # Placeholder for GA4/Meta forwarding
    return {"status": "event_logged", "event": event}

