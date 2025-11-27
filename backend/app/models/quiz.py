import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class QuizQuestion(Base):
    """Quiz question model for storing generated quiz questions."""

    __tablename__ = "quiz_questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    question_text = Column(Text, nullable=False)
    question_type = Column(String(32), nullable=False)  # MCQ, TRUE_FALSE, SHORT
    options = Column(JSONB, nullable=True)  # ["A", "B", "C", "D"]
    correct_option_index = Column(Integer, nullable=True)  # 0-based index
    correct_answer = Column(Text, nullable=True)  # for TRUE_FALSE/SHORT
    explanation = Column(Text, nullable=True)
    related_timestamp_seconds = Column(Integer, nullable=True)
    concept_tag = Column(String(128), nullable=True)
    difficulty = Column(String(16), nullable=True)  # easy, medium, hard
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    video = relationship("Video", back_populates="quiz_questions")
    answers = relationship("QuizAnswer", back_populates="question", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<QuizQuestion {self.question_type} - {self.difficulty}>"


class QuizSession(Base):
    """Quiz session model for tracking user quiz attempts."""

    __tablename__ = "quiz_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    score = Column(Integer, nullable=True)
    total_questions = Column(Integer, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="quiz_sessions")
    video = relationship("Video", back_populates="quiz_sessions")
    answers = relationship("QuizAnswer", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<QuizSession {self.id} - Score: {self.score}/{self.total_questions}>"


class QuizAnswer(Base):
    """Quiz answer model for storing user answers."""

    __tablename__ = "quiz_answers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("quiz_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(UUID(as_uuid=True), ForeignKey("quiz_questions.id", ondelete="CASCADE"), nullable=False, index=True)
    selected_option_index = Column(Integer, nullable=True)
    submitted_answer = Column(Text, nullable=True)
    is_correct = Column(Boolean, nullable=False)
    evaluated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    session = relationship("QuizSession", back_populates="answers")
    question = relationship("QuizQuestion", back_populates="answers")

    def __repr__(self):
        return f"<QuizAnswer {self.id} - Correct: {self.is_correct}>"
