"""
Guest Service for managing anonymous user access.
Allows 1 free video analysis before requiring sign-in.
"""
import hashlib
import uuid
from typing import Optional, Tuple
from uuid import UUID

from fastapi import Request
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.guest_usage import GuestUsage
from app.models.video import Video


class GuestService:
    """
    Service for managing guest (anonymous) user access.

    Features:
    - Generate and manage guest tokens (stored in cookies)
    - Hash IP addresses for backup identification
    - Track guest video usage (1 free video per guest)
    - Check if video is already cached (free access)
    """

    GUEST_TOKEN_COOKIE = "notetube_guest_token"
    GUEST_LIMIT = 1  # Number of free videos for guests

    @staticmethod
    def generate_guest_token() -> str:
        """Generate a new guest token (UUID4)."""
        return str(uuid.uuid4())

    @staticmethod
    def hash_ip(ip: str) -> str:
        """
        Hash an IP address for privacy-preserving identification.

        Args:
            ip: Client IP address

        Returns:
            SHA-256 hash of the IP (first 64 chars)
        """
        if not ip:
            return ""
        return hashlib.sha256(ip.encode()).hexdigest()[:64]

    @staticmethod
    def get_client_ip(request: Request) -> str:
        """
        Extract client IP from request, handling proxies.

        Args:
            request: FastAPI request object

        Returns:
            Client IP address
        """
        # Check for forwarded headers (common with proxies/load balancers)
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            # Take the first IP in the chain (original client)
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fallback to direct connection IP
        if request.client:
            return request.client.host

        return ""

    def get_guest_token_from_request(self, request: Request) -> Optional[str]:
        """
        Extract guest token from request cookies.

        Args:
            request: FastAPI request object

        Returns:
            Guest token if present, None otherwise
        """
        return request.cookies.get(self.GUEST_TOKEN_COOKIE)

    async def has_used_free_video(
        self,
        db: AsyncSession,
        guest_token: Optional[str],
        ip_hash: Optional[str]
    ) -> bool:
        """
        Check if guest has already used their free video.

        Args:
            db: Database session
            guest_token: Guest token from cookie
            ip_hash: Hashed IP address

        Returns:
            True if guest has used their free video, False otherwise
        """
        if not guest_token and not ip_hash:
            return False

        # Build query conditions
        conditions = []
        if guest_token:
            conditions.append(GuestUsage.guest_token == guest_token)
        if ip_hash:
            conditions.append(GuestUsage.ip_hash == ip_hash)

        result = await db.execute(
            select(GuestUsage).where(or_(*conditions)).limit(1)
        )
        usage = result.scalar_one_or_none()

        return usage is not None

    async def is_video_cached(
        self,
        db: AsyncSession,
        youtube_id: str
    ) -> Tuple[bool, Optional[UUID]]:
        """
        Check if a video is already processed (cached).
        Cached videos are free for guests.

        Args:
            db: Database session
            youtube_id: YouTube video ID

        Returns:
            Tuple of (is_cached, video_id)
        """
        result = await db.execute(
            select(Video).where(
                Video.youtube_video_id == youtube_id,
                Video.status == "READY"
            ).limit(1)
        )
        video = result.scalar_one_or_none()

        if video:
            return True, video.id

        return False, None

    async def record_guest_usage(
        self,
        db: AsyncSession,
        guest_token: str,
        ip_hash: str,
        video_id: Optional[UUID] = None,
        youtube_id: Optional[str] = None
    ) -> GuestUsage:
        """
        Record that a guest has used their free video.

        Args:
            db: Database session
            guest_token: Guest token from cookie
            ip_hash: Hashed IP address
            video_id: UUID of the processed video
            youtube_id: YouTube video ID

        Returns:
            Created GuestUsage record
        """
        usage = GuestUsage(
            guest_token=guest_token,
            ip_hash=ip_hash,
            video_id=video_id,
            youtube_id=youtube_id
        )
        db.add(usage)
        await db.commit()
        await db.refresh(usage)
        return usage

    async def get_guest_access_state(
        self,
        db: AsyncSession,
        request: Request,
        youtube_id: Optional[str] = None
    ) -> dict:
        """
        Get the current access state for a guest user.

        Args:
            db: Database session
            request: FastAPI request object
            youtube_id: Optional YouTube video ID to check

        Returns:
            Dict with access state:
            {
                "can_generate": bool,
                "requires_auth": bool,
                "is_cached": bool,
                "guest_token": str,
                "tier": "anonymous"
            }
        """
        guest_token = self.get_guest_token_from_request(request)
        client_ip = self.get_client_ip(request)
        ip_hash = self.hash_ip(client_ip) if client_ip else None

        # Check if video is already cached
        is_cached = False
        if youtube_id:
            is_cached, _ = await self.is_video_cached(db, youtube_id)

        # Cached videos are always accessible
        if is_cached:
            return {
                "can_generate": True,
                "requires_auth": False,
                "is_cached": True,
                "guest_token": guest_token or self.generate_guest_token(),
                "tier": "anonymous"
            }

        # Check if guest has used their free video
        has_used = await self.has_used_free_video(db, guest_token, ip_hash)

        if has_used:
            return {
                "can_generate": False,
                "requires_auth": True,
                "is_cached": False,
                "guest_token": guest_token,
                "tier": "anonymous"
            }

        # Guest can use their free video
        return {
            "can_generate": True,
            "requires_auth": False,
            "is_cached": False,
            "guest_token": guest_token or self.generate_guest_token(),
            "tier": "anonymous"
        }


# Singleton instance
guest_service = GuestService()
