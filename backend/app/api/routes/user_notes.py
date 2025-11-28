"""
User Notes API routes for saving and managing notes from transcript selections.
"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.user_notes import (
    UserNoteCreate,
    UserNoteResponse,
    RewriteRequest,
    RewriteResponse
)
from app.schemas.user import User
from app.services.user_notes_service import UserNotesService, UserNotesServiceError
from app.api.dependencies.auth import get_current_user


router = APIRouter(prefix="/api/videos", tags=["user-notes"])


@router.post("/{video_id}/user-notes", response_model=UserNoteResponse, status_code=status.HTTP_201_CREATED)
async def save_user_note(
    video_id: UUID,
    request: UserNoteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> UserNoteResponse:
    """
    Save a new user note from a transcript selection.

    - Requires authentication
    - User must own the video
    - Returns the saved note with generated ID
    """
    service = UserNotesService(db)

    try:
        note = await service.save_note(
            video_id=str(video_id),
            user_id=str(current_user.id),
            text=request.text,
            timestamp=request.timestamp
        )
        return UserNoteResponse(**note)
    except UserNotesServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/{video_id}/user-notes", response_model=List[UserNoteResponse])
async def get_user_notes(
    video_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[UserNoteResponse]:
    """
    Get all user notes for a video.

    - Requires authentication
    - User must own the video
    - Returns notes sorted by timestamp
    """
    service = UserNotesService(db)

    try:
        notes = await service.get_notes(
            video_id=str(video_id),
            user_id=str(current_user.id)
        )
        return [UserNoteResponse(**note) for note in notes]
    except UserNotesServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.delete("/{video_id}/user-notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_note(
    video_id: UUID,
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a user note.

    - Requires authentication
    - User must own the video
    - Returns 204 on success, 404 if not found
    """
    service = UserNotesService(db)

    try:
        deleted = await service.delete_note(
            video_id=str(video_id),
            user_id=str(current_user.id),
            note_id=note_id
        )
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Note not found"
            )
    except UserNotesServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/{video_id}/user-notes/{note_id}/rewrite", response_model=RewriteResponse)
async def rewrite_user_note(
    video_id: UUID,
    note_id: str,
    request: RewriteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> RewriteResponse:
    """
    Rewrite a user note using AI with a specific style.

    Supported styles:
    - simplify: Rewrite in simpler language
    - summarize: Summarize in 1-2 sentences
    - formal: Rewrite in formal language
    - bullet_points: Convert to bullet points
    - explain: Explain the concept for beginners

    - Requires authentication
    - User must own the video
    """
    service = UserNotesService(db)

    try:
        note = await service.rewrite_note(
            video_id=str(video_id),
            user_id=str(current_user.id),
            note_id=note_id,
            style=request.style
        )
        return RewriteResponse(**note)
    except UserNotesServiceError as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
