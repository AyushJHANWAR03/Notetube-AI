"""
Guest routes for anonymous user access management.
"""
from typing import Optional

from fastapi import APIRouter, Request, Query, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.services.guest_service import guest_service

router = APIRouter(prefix="/guest", tags=["guest"])


@router.get("/check-limit")
async def check_guest_limit(
    request: Request,
    youtube_id: Optional[str] = Query(None, description="YouTube video ID to check"),
    db: AsyncSession = Depends(get_db)
):
    """
    Check if a guest user can generate a new video analysis.

    Returns:
        {
            "can_generate": bool,
            "requires_auth": bool,
            "is_cached": bool,
            "tier": "anonymous"
        }
    """
    state = await guest_service.get_guest_access_state(
        db,
        request,
        youtube_id
    )

    response = JSONResponse(content={
        "can_generate": state["can_generate"],
        "requires_auth": state["requires_auth"],
        "is_cached": state["is_cached"],
        "tier": state["tier"]
    })

    # Set guest token cookie if new
    if state["guest_token"] and not request.cookies.get(guest_service.GUEST_TOKEN_COOKIE):
        response.set_cookie(
            key=guest_service.GUEST_TOKEN_COOKIE,
            value=state["guest_token"],
            max_age=60 * 60 * 24 * 365,  # 1 year
            httponly=True,
            samesite="lax",
            secure=settings.ENVIRONMENT == "production"
        )

    return response
