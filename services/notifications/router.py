from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from datetime import datetime, timezone

from packages.auth.jwt import get_current_user_token, TokenPayload

router = APIRouter(prefix="/notifications", tags=["Notifications & Alerts"])


@router.get("/")
async def get_my_notifications(current_user: TokenPayload = Depends(get_current_user_token)) -> List[Dict[str, Any]]:
    return [
        {
            "id": "notif-001",
            "title": "Welcome to SevaHealth AI",
            "body": "Your preventive health decision intelligence dashboard is ready.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "read": False,
            "priority": "INFO",
        },
        {
            "id": "notif-002",
            "title": "Daily Habit Check-in",
            "body": "Don't forget to complete today's post-meal brisk walk to sustain optimal glucose uptake.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "read": False,
            "priority": "REMINDER",
        }
    ]
