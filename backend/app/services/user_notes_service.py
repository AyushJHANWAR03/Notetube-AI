"""
User Notes Service for saving and rewriting user-selected transcript notes.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
from openai import OpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from app.core.config import settings
from app.core.constants import AIModels
from app.models.notes import Notes
from app.models.video import Video
from app.prompts import REWRITE_PROMPTS
from app.prompts.rewrite_prompts import REWRITE_SYSTEM_PROMPT


class UserNotesServiceError(Exception):
    """Custom exception for User Notes service errors."""
    pass


class UserNotesService:
    """Service for managing user-saved notes from transcript selections."""

    def __init__(self, db: AsyncSession, api_key: Optional[str] = None):
        """Initialize the User Notes service."""
        self.db = db
        if api_key is None:
            api_key = settings.OPENAI_API_KEY

        self._api_key = api_key
        self._client = None

    @property
    def client(self) -> OpenAI:
        """Lazily initialize the OpenAI client."""
        if self._client is None:
            self._client = OpenAI(api_key=self._api_key)
        return self._client

    async def get_notes_record(self, video_id: str, user_id: str) -> Optional[Notes]:
        """Get the Notes record for a video, with access control for cached videos."""
        # Query video without ownership filter first
        result = await self.db.execute(
            select(Video).where(Video.id == video_id)
        )
        video = result.scalar_one_or_none()

        if not video:
            return None

        # Access control: allow if user owns it OR if video is READY (cached)
        # READY videos can be accessed by any authenticated user
        if video.user_id != user_id and video.status != "READY":
            return None

        # Get the notes for this video
        notes_result = await self.db.execute(
            select(Notes).where(Notes.video_id == video_id)
        )
        return notes_result.scalar_one_or_none()

    async def save_note(
        self,
        video_id: str,
        user_id: str,
        text: str,
        timestamp: float
    ) -> Dict[str, Any]:
        """
        Save a new user note to the video's notes.
        """
        notes_record = await self.get_notes_record(video_id, user_id)
        if not notes_record:
            raise UserNotesServiceError("Video not found or not owned by user")

        # Create new note
        new_note = {
            "id": str(uuid.uuid4()),
            "text": text,
            "timestamp": timestamp,
            "created_at": datetime.utcnow().isoformat(),
            "rewritten_text": None
        }

        # Get existing user_notes or initialize empty list
        user_notes = list(notes_record.user_notes or [])
        user_notes.append(new_note)

        # Update the record - must use flag_modified for JSONB
        notes_record.user_notes = user_notes
        flag_modified(notes_record, "user_notes")
        await self.db.commit()
        await self.db.refresh(notes_record)

        return new_note

    async def get_notes(self, video_id: str, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all user notes for a video.
        """
        notes_record = await self.get_notes_record(video_id, user_id)
        if not notes_record:
            raise UserNotesServiceError("Video not found or not owned by user")

        user_notes = notes_record.user_notes or []
        # Sort by timestamp
        return sorted(user_notes, key=lambda x: x.get("timestamp", 0))

    async def delete_note(self, video_id: str, user_id: str, note_id: str) -> bool:
        """
        Delete a user note.
        """
        notes_record = await self.get_notes_record(video_id, user_id)
        if not notes_record:
            raise UserNotesServiceError("Video not found or not owned by user")

        user_notes = list(notes_record.user_notes or [])
        original_length = len(user_notes)

        # Filter out the note to delete
        user_notes = [n for n in user_notes if n.get("id") != note_id]

        if len(user_notes) == original_length:
            return False  # Note not found

        notes_record.user_notes = user_notes
        flag_modified(notes_record, "user_notes")
        await self.db.commit()
        return True

    async def rewrite_note(
        self,
        video_id: str,
        user_id: str,
        note_id: str,
        style: str,
        model: str = "gpt-3.5-turbo"
    ) -> Dict[str, Any]:
        """
        Rewrite a note using AI with the specified style.
        """
        notes_record = await self.get_notes_record(video_id, user_id)
        if not notes_record:
            raise UserNotesServiceError("Video not found or not owned by user")

        user_notes = list(notes_record.user_notes or [])

        # Find the note
        note_index = None
        target_note = None
        for i, note in enumerate(user_notes):
            if note.get("id") == note_id:
                note_index = i
                target_note = note
                break

        if target_note is None:
            raise UserNotesServiceError("Note not found")

        # Get the rewrite prompt
        prompt = REWRITE_PROMPTS.get(style)
        if not prompt:
            raise UserNotesServiceError(f"Invalid rewrite style: {style}")

        # Call OpenAI to rewrite
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": REWRITE_SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": f"{prompt}\n\nText to rewrite:\n{target_note['text']}"
                    }
                ],
                temperature=0.7,
                max_tokens=500
            )

            rewritten_text = response.choices[0].message.content.strip()

            # Update the note
            user_notes[note_index]["rewritten_text"] = rewritten_text
            notes_record.user_notes = user_notes
            flag_modified(notes_record, "user_notes")
            await self.db.commit()
            await self.db.refresh(notes_record)

            return user_notes[note_index]

        except Exception as e:
            raise UserNotesServiceError(f"Failed to rewrite note: {str(e)}")
