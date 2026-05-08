from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean, Float
from datetime import datetime
from app.database import Base


class ChatHistory(Base):
    """Bestie chat messages with mode/theme/dialog flags."""
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    role = Column(String, nullable=False)  # "user" or "assistant"
    message = Column(Text, nullable=True)
    mode = Column(String, default="chat")  # chat, dialog, practice
    theme = Column(String, nullable=True)
    dialog_id = Column(Integer, nullable=True)
    is_correction = Column(Integer, default=0)
    corrected_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SentenceCorrection(Base):
    """Stored grammar/correction feedback from chat."""
    __tablename__ = "sentence_corrections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    original = Column(Text, nullable=True)
    corrected = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)
    chat_message_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserLearningState(Base):
    """Chat story level/stage/theme/known words."""
    __tablename__ = "user_learning_state"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True, unique=True)
    level = Column(String, default="beginner")
    stage = Column(Integer, default=1)
    theme = Column(String, nullable=True)
    known_words = Column(Text, default="[]")  # JSON array
    words_to_review = Column(Text, default="[]")  # JSON array
    last_lesson_topic = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow)


class UserRelationship(Base):
    """Relationship continuity for Bestie chat personality."""
    __tablename__ = "user_relationship"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True, unique=True)
    stage = Column(String, default="stranger")  # stranger, acquaintance, friend, bestie
    rapport_score = Column(Float, default=0.0)
    interaction_count = Column(Integer, default=0)
    last_interaction = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow)


class Dialog(Base):
    """Authored dialog scripts for practice."""
    __tablename__ = "dialogs"

    id = Column(Integer, primary_key=True, index=True)
    theme = Column(String, nullable=False, index=True)
    line_number = Column(Integer, nullable=False)
    role = Column(String, nullable=False)  # "user" or "assistant"
    text = Column(Text, nullable=False)
    hint = Column(Text, nullable=True)


class UserDialogProgress(Base):
    """Per-user dialog progress."""
    __tablename__ = "user_dialog_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    theme = Column(String, nullable=False)
    current_line = Column(Integer, default=0)
    completed = Column(Integer, default=0)
    started_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class UserLevelAssessment(Base):
    """Periodic chat level assessment scores."""
    __tablename__ = "user_level_assessments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    assessment_score = Column(Float, default=0.0)
    vocabulary_score = Column(Float, default=0.0)
    grammar_score = Column(Float, default=0.0)
    fluency_score = Column(Float, default=0.0)
    level_assigned = Column(String, default="beginner")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
