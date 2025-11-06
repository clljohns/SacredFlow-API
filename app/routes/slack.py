from fastapi import APIRouter, Request
from app.core.config import settings
import httpx

router = APIRouter()

@router.post("/slack/webhook", tags=["slack"])
async def handle_slack(request: Request):
    data = await request.json()
    async with httpx.AsyncClient() as client:
        await client.post(settings.SLACK_WEBHOOK_URL, json=data)
    return {"status": "forwarded"}

