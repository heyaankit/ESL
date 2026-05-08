from sqlalchemy import Column, String, Integer, Text, DateTime
from datetime import datetime
from app.database import Base


class AudioFile(Base):
    """TTS/generated audio metadata."""
    __tablename__ = "audio_files"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=True, index=True)
    lesson_id = Column(String, nullable=True)
    item_id = Column(Integer, nullable=True)
    text = Column(Text, nullable=True)
    voice = Column(String, nullable=True)
    audio_url = Column(String, nullable=True)
    file_path = Column(String, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    source = Column(String, default="tts")  # tts, google_tts
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)


class AudioAnswer(Base):
    """Uploaded voice answers, transcription results."""
    __tablename__ = "audio_answers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    lesson_id = Column(String, nullable=True)
    item_id = Column(Integer, nullable=True)
    audio_url = Column(String, nullable=True)
    file_path = Column(String, nullable=True)
    transcription = Column(Text, nullable=True)
    expected_answer = Column(Text, nullable=True)
    is_correct = Column(Integer, default=0)
    duration_seconds = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
