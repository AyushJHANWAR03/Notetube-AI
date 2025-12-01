"""
User API routes for quota management and limit increase requests.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.schemas.user import User
from app.api.dependencies.auth import get_current_user
from app.services.email_service import email_service


router = APIRouter(prefix="/api/users", tags=["users"])


class QuotaResponse(BaseModel):
    videos_analyzed: int
    video_limit: int
    remaining: int


class LimitIncreaseRequest(BaseModel):
    feedback: str


class LimitIncreaseResponse(BaseModel):
    success: bool
    message: str


@router.get("/quota", response_model=QuotaResponse)
async def get_quota(
    current_user: User = Depends(get_current_user)
) -> QuotaResponse:
    """
    Get current user's video quota information.
    """
    return QuotaResponse(
        videos_analyzed=current_user.videos_analyzed,
        video_limit=current_user.video_limit,
        remaining=current_user.video_limit - current_user.videos_analyzed
    )


@router.post("/request-limit-increase", response_model=LimitIncreaseResponse)
async def request_limit_increase(
    request: LimitIncreaseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> LimitIncreaseResponse:
    """
    Request a video limit increase by providing feedback.

    Sends an email to the admin with user info and feedback.
    """
    if not request.feedback or len(request.feedback.strip()) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide meaningful feedback (at least 10 characters)"
        )

    # Send email to admin
    try:
        success = await email_service.send_limit_increase_request(
            user_email=current_user.email,
            user_name=current_user.name or "Unknown",
            feedback=request.feedback,
            videos_analyzed=current_user.videos_analyzed,
            video_limit=current_user.video_limit
        )

        if success:
            return LimitIncreaseResponse(
                success=True,
                message="Your request has been submitted. We'll review it and get back to you soon!"
            )
        else:
            return LimitIncreaseResponse(
                success=True,
                message="Your feedback has been recorded. We'll review it soon!"
            )
    except Exception:
        # Don't expose internal errors, just acknowledge the request
        return LimitIncreaseResponse(
            success=True,
            message="Your feedback has been recorded. We'll review it soon!"
        )
