"""
Admin API routes for dashboard, user management, and analytics.
"""
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, func, desc
from pydantic import BaseModel

from app.core.database import get_db
from app.schemas.user import User
from app.api.dependencies.auth import get_admin_user


router = APIRouter(prefix="/api/admin", tags=["admin"])


# ============ Response Models ============

class StatsResponse(BaseModel):
    total_users: int
    total_videos: int
    total_guests: int
    total_chats: int
    videos_ready: int
    videos_failed: int
    videos_processing: int
    today_users: int
    today_videos: int
    today_guests: int


class UserListItem(BaseModel):
    id: str
    name: Optional[str]
    email: str
    videos_count: int
    chats_count: int
    video_limit: int
    videos_analyzed: int
    created_at: datetime
    last_active: Optional[datetime]


class UsersListResponse(BaseModel):
    users: List[UserListItem]
    total: int


class VideoListItem(BaseModel):
    id: str
    title: Optional[str]
    status: str
    user_name: Optional[str]
    user_email: Optional[str]
    is_guest: bool
    created_at: datetime
    duration_seconds: Optional[int]
    youtube_video_id: Optional[str]
    original_url: Optional[str]


class VideosListResponse(BaseModel):
    videos: List[VideoListItem]
    total: int


class GuestListItem(BaseModel):
    id: str
    guest_token: str
    video_title: Optional[str]
    video_status: Optional[str]
    youtube_id: Optional[str]
    created_at: datetime


class GuestsListResponse(BaseModel):
    guests: List[GuestListItem]
    total: int


class ChatMessageItem(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime


class UserVideoItem(BaseModel):
    id: str
    title: Optional[str]
    status: str
    created_at: datetime
    youtube_video_id: Optional[str]
    original_url: Optional[str]


class UserDetailResponse(BaseModel):
    id: str
    name: Optional[str]
    email: str
    avatar_url: Optional[str]
    videos_analyzed: int
    video_limit: int
    created_at: datetime
    videos: List[UserVideoItem]
    recent_chats: List[ChatMessageItem]


# ============ Routes ============

@router.get("/stats", response_model=StatsResponse)
async def get_admin_stats(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
) -> StatsResponse:
    """
    Get dashboard statistics for admin panel.
    """
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    # Total counts
    users_result = await db.execute(text("SELECT COUNT(*) FROM users"))
    total_users = users_result.scalar()

    videos_result = await db.execute(text("SELECT COUNT(*) FROM videos"))
    total_videos = videos_result.scalar()

    guests_result = await db.execute(text("SELECT COUNT(*) FROM guest_usage"))
    total_guests = guests_result.scalar()

    chats_result = await db.execute(text("SELECT COUNT(*) FROM chat_messages"))
    total_chats = chats_result.scalar()

    # Video status counts
    status_result = await db.execute(text("""
        SELECT status, COUNT(*) FROM videos GROUP BY status
    """))
    status_counts = {row[0]: row[1] for row in status_result.fetchall()}

    # Today's counts
    today_users_result = await db.execute(
        text("SELECT COUNT(*) FROM users WHERE created_at >= :today"),
        {"today": today}
    )
    today_users = today_users_result.scalar()

    today_videos_result = await db.execute(
        text("SELECT COUNT(*) FROM videos WHERE created_at >= :today"),
        {"today": today}
    )
    today_videos = today_videos_result.scalar()

    today_guests_result = await db.execute(
        text("SELECT COUNT(*) FROM guest_usage WHERE created_at >= :today"),
        {"today": today}
    )
    today_guests = today_guests_result.scalar()

    return StatsResponse(
        total_users=total_users or 0,
        total_videos=total_videos or 0,
        total_guests=total_guests or 0,
        total_chats=total_chats or 0,
        videos_ready=status_counts.get("READY", 0),
        videos_failed=status_counts.get("FAILED", 0),
        videos_processing=status_counts.get("PROCESSING", 0),
        today_users=today_users or 0,
        today_videos=today_videos or 0,
        today_guests=today_guests or 0
    )


@router.get("/users", response_model=UsersListResponse)
async def get_admin_users(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
) -> UsersListResponse:
    """
    Get list of all users with their activity counts.
    """
    # Get total count
    total_result = await db.execute(text("SELECT COUNT(*) FROM users"))
    total = total_result.scalar()

    # Get users with video and chat counts
    users_result = await db.execute(text("""
        SELECT
            u.id,
            u.name,
            u.email,
            u.video_limit,
            u.videos_analyzed,
            u.created_at,
            COUNT(DISTINCT v.id) as videos_count,
            COUNT(DISTINCT c.id) as chats_count,
            MAX(COALESCE(v.created_at, c.created_at)) as last_active
        FROM users u
        LEFT JOIN videos v ON u.id = v.user_id
        LEFT JOIN chat_messages c ON u.id = c.user_id
        GROUP BY u.id, u.name, u.email, u.video_limit, u.videos_analyzed, u.created_at
        ORDER BY u.created_at DESC
        LIMIT :limit OFFSET :offset
    """), {"limit": limit, "offset": offset})

    users = []
    for row in users_result.fetchall():
        users.append(UserListItem(
            id=str(row[0]),
            name=row[1],
            email=row[2],
            video_limit=row[3] or 5,
            videos_analyzed=row[4] or 0,
            created_at=row[5],
            videos_count=row[6] or 0,
            chats_count=row[7] or 0,
            last_active=row[8]
        ))

    return UsersListResponse(users=users, total=total or 0)


@router.get("/users/{user_id}", response_model=UserDetailResponse)
async def get_admin_user_detail(
    user_id: UUID,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
) -> UserDetailResponse:
    """
    Get detailed information about a specific user including their videos and chats.
    """
    # Get user info
    user_result = await db.execute(
        text("""
            SELECT id, name, email, avatar_url, videos_analyzed, video_limit, created_at
            FROM users WHERE id = :user_id
        """),
        {"user_id": user_id}
    )
    user_row = user_result.fetchone()

    if not user_row:
        raise HTTPException(status_code=404, detail="User not found")

    # Get user's videos
    videos_result = await db.execute(
        text("""
            SELECT id, title, status, created_at, youtube_video_id, original_url
            FROM videos
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            LIMIT 50
        """),
        {"user_id": user_id}
    )

    videos = [
        UserVideoItem(
            id=str(row[0]),
            title=row[1],
            status=row[2],
            created_at=row[3],
            youtube_video_id=row[4],
            original_url=row[5]
        )
        for row in videos_result.fetchall()
    ]

    # Get user's recent chats
    chats_result = await db.execute(
        text("""
            SELECT id, role, content, created_at
            FROM chat_messages
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            LIMIT 50
        """),
        {"user_id": user_id}
    )

    chats = [
        ChatMessageItem(
            id=str(row[0]),
            role=row[1],
            content=row[2][:500] if row[2] else "",  # Truncate long messages
            created_at=row[3]
        )
        for row in chats_result.fetchall()
    ]

    return UserDetailResponse(
        id=str(user_row[0]),
        name=user_row[1],
        email=user_row[2],
        avatar_url=user_row[3],
        videos_analyzed=user_row[4] or 0,
        video_limit=user_row[5] or 5,
        created_at=user_row[6],
        videos=videos,
        recent_chats=chats
    )


@router.get("/videos", response_model=VideosListResponse)
async def get_admin_videos(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    status_filter: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
) -> VideosListResponse:
    """
    Get list of all videos with user info.
    """
    # Build query based on filter
    where_clause = ""
    params = {"limit": limit, "offset": offset}

    if status_filter:
        where_clause = "WHERE v.status = :status"
        params["status"] = status_filter

    # Get total count
    count_query = f"SELECT COUNT(*) FROM videos v {where_clause}"
    total_result = await db.execute(text(count_query), params)
    total = total_result.scalar()

    # Get videos with user info
    videos_result = await db.execute(text(f"""
        SELECT
            v.id,
            v.title,
            v.status,
            v.created_at,
            v.duration_seconds,
            v.user_id,
            u.name as user_name,
            u.email as user_email,
            v.youtube_video_id,
            v.original_url
        FROM videos v
        LEFT JOIN users u ON v.user_id = u.id
        {where_clause}
        ORDER BY v.created_at DESC
        LIMIT :limit OFFSET :offset
    """), params)

    videos = []
    for row in videos_result.fetchall():
        videos.append(VideoListItem(
            id=str(row[0]),
            title=row[1],
            status=row[2],
            created_at=row[3],
            duration_seconds=row[4],
            user_name=row[6],
            user_email=row[7],
            is_guest=row[5] is None,  # user_id is None for guest videos
            youtube_video_id=row[8],
            original_url=row[9]
        ))

    return VideosListResponse(videos=videos, total=total or 0)


@router.get("/guests", response_model=GuestsListResponse)
async def get_admin_guests(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
) -> GuestsListResponse:
    """
    Get list of all guest usage sessions.
    """
    # Get total count
    total_result = await db.execute(text("SELECT COUNT(*) FROM guest_usage"))
    total = total_result.scalar()

    # Get guests with video info
    guests_result = await db.execute(text("""
        SELECT
            g.id,
            g.guest_token,
            g.youtube_id,
            g.created_at,
            v.title as video_title,
            v.status as video_status
        FROM guest_usage g
        LEFT JOIN videos v ON g.video_id = v.id
        ORDER BY g.created_at DESC
        LIMIT :limit OFFSET :offset
    """), {"limit": limit, "offset": offset})

    guests = []
    for row in guests_result.fetchall():
        guests.append(GuestListItem(
            id=str(row[0]),
            guest_token=row[1][:20] + "..." if row[1] and len(row[1]) > 20 else row[1],
            youtube_id=row[2],
            created_at=row[3],
            video_title=row[4],
            video_status=row[5]
        ))

    return GuestsListResponse(guests=guests, total=total or 0)


class InsightsResponse(BaseModel):
    insights: str
    video_categories: List[dict]
    user_behavior: dict
    recommendations: List[str]


@router.get("/insights", response_model=InsightsResponse)
async def get_admin_insights(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
) -> InsightsResponse:
    """
    Get AI-powered insights about user behavior and content patterns.
    """
    # Get video titles for categorization
    videos_result = await db.execute(text("""
        SELECT title, status FROM videos
        WHERE title IS NOT NULL
        ORDER BY created_at DESC
        LIMIT 100
    """))
    videos = videos_result.fetchall()

    # Get chat messages to understand user questions
    chats_result = await db.execute(text("""
        SELECT content FROM chat_messages
        WHERE role = 'user'
        ORDER BY created_at DESC
        LIMIT 50
    """))
    user_chats = [row[0] for row in chats_result.fetchall()]

    # Get user signup trends
    signups_result = await db.execute(text("""
        SELECT DATE(created_at) as date, COUNT(*) as count
        FROM users
        WHERE created_at > NOW() - INTERVAL '30 days'
        GROUP BY DATE(created_at)
        ORDER BY date DESC
    """))
    signups = signups_result.fetchall()

    # Get video processing success rate
    status_result = await db.execute(text("""
        SELECT status, COUNT(*) FROM videos GROUP BY status
    """))
    status_counts = {row[0]: row[1] for row in status_result.fetchall()}

    # Categorize videos by type (simple keyword matching)
    categories = {
        "Education/Study": 0,
        "Programming/Tech": 0,
        "Business/Finance": 0,
        "Self-Improvement": 0,
        "Entertainment": 0,
        "Other": 0
    }

    education_keywords = ["class", "chapter", "exam", "study", "lecture", "course", "learn", "tutorial", "jee", "neet", "cbse", "upsc"]
    tech_keywords = ["python", "java", "code", "programming", "react", "javascript", "api", "software", "ai", "machine learning", "aws"]
    business_keywords = ["business", "money", "invest", "finance", "startup", "entrepreneur", "marketing", "career"]
    self_improvement_keywords = ["motivation", "success", "habit", "productivity", "mindset", "life", "growth"]

    for video in videos:
        title = (video[0] or "").lower()
        if any(kw in title for kw in education_keywords):
            categories["Education/Study"] += 1
        elif any(kw in title for kw in tech_keywords):
            categories["Programming/Tech"] += 1
        elif any(kw in title for kw in business_keywords):
            categories["Business/Finance"] += 1
        elif any(kw in title for kw in self_improvement_keywords):
            categories["Self-Improvement"] += 1
        else:
            categories["Other"] += 1

    # Calculate insights
    total_videos = sum(status_counts.values())
    success_rate = (status_counts.get("READY", 0) / total_videos * 100) if total_videos > 0 else 0

    top_category = max(categories, key=categories.get)

    # Build recommendations
    recommendations = []

    if categories["Education/Study"] > categories["Programming/Tech"]:
        recommendations.append("Most users are students - consider adding exam prep features or flashcard improvements")

    if status_counts.get("FAILED", 0) > total_videos * 0.1:
        recommendations.append(f"High failure rate ({status_counts.get('FAILED', 0)} videos) - investigate transcript fetching issues")

    if len(user_chats) > 0:
        recommendations.append("Users are actively using chat - consider improving AI response quality")

    recommendations.append(f"Focus marketing on {top_category} content creators - this is your main user segment")

    # Build summary
    insights = f"""
Based on {total_videos} videos analyzed:
- Top content category: {top_category} ({categories[top_category]} videos)
- Video success rate: {success_rate:.1f}%
- Most active user segment: Students/Learners preparing for exams
- Users are using NoteTube primarily for educational content
    """.strip()

    video_categories = [{"name": k, "count": v} for k, v in categories.items() if v > 0]
    video_categories.sort(key=lambda x: x["count"], reverse=True)

    user_behavior = {
        "total_videos": total_videos,
        "success_rate": round(success_rate, 1),
        "total_chats": len(user_chats),
        "signups_last_30_days": sum(row[1] for row in signups)
    }

    return InsightsResponse(
        insights=insights,
        video_categories=video_categories,
        user_behavior=user_behavior,
        recommendations=recommendations
    )
