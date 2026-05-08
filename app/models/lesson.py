from sqlalchemy import Column, Integer, String, Text
from app.database import Base


class LessonItem(Base):
    """Excel-backed lesson items — the master vocabulary/content table."""
    __tablename__ = "lesson_items"

    id = Column(Integer, primary_key=True, index=True)
    lesson = Column(String, nullable=False, index=True)
    sub_topic = Column(String, nullable=False, index=True)
    grammar_topic = Column(String, nullable=True)
    word_number = Column(String, nullable=True)
    vocabulary_word = Column(String, nullable=False)
    meaning = Column(Text, nullable=True)
    example_sentence = Column(Text, nullable=True)
    conversation_question = Column(Text, nullable=True)
    conversation_affirmative = Column(Text, nullable=True)
    conversation_interrogative = Column(Text, nullable=True)
    conversation_yes = Column(Text, nullable=True)
    conversation_no = Column(Text, nullable=True)
    grammar_explanation = Column(Text, nullable=True)
    exercise_type = Column(String, nullable=True)
    exercise_answers = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)


class LessonProgress(Base):
    """Progress tracking for dynamic Excel-backed lessons (/lesson/* endpoints)."""
    __tablename__ = "lesson_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    lesson_id = Column(String, nullable=False, index=True)
    current_question_index = Column(Integer, default=0)
    total_questions = Column(Integer, default=0)
    correct_count = Column(Integer, default=0)
    incorrect_count = Column(Integer, default=0)
    completed = Column(Integer, default=0)  # 0=in-progress, 1=completed
    started_at = Column(String, nullable=True)
    last_activity = Column(String, nullable=True)


class LessonAnswer(Base):
    """Individual answers within dynamic lesson sessions."""
    __tablename__ = "lesson_answers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    lesson_id = Column(String, nullable=False, index=True)
    item_id = Column(Integer, nullable=False)
    user_answer = Column(Text, nullable=True)
    expected_answer = Column(Text, nullable=True)
    is_correct = Column(Integer, default=0)  # 0=wrong, 1=correct
    attempt_number = Column(Integer, default=1)
    answered_at = Column(String, nullable=True)


class QuestionAttempt(Base):
    """Retry counters for lesson questions."""
    __tablename__ = "question_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    lesson_id = Column(String, nullable=False)
    item_id = Column(Integer, nullable=False)
    attempts = Column(Integer, default=0)
    revealed = Column(Integer, default=0)  # 0=not revealed, 1=hint shown
    last_attempt_at = Column(String, nullable=True)


class LessonAppProgress(Base):
    """Progress tracking for app.py hardcoded lesson APIs (/lessons/* endpoints)."""
    __tablename__ = "lesson_app_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    lesson_id = Column(String, nullable=False, index=True)
    viewed = Column(Integer, default=0)
    completed = Column(Integer, default=0)
    last_activity = Column(String, nullable=True)


class LessonAppAnswer(Base):
    """Answer records for app.py hardcoded lesson APIs."""
    __tablename__ = "lesson_app_answers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    lesson_id = Column(String, nullable=False)
    item_id = Column(Integer, nullable=False)
    user_answer = Column(Text, nullable=True)
    is_correct = Column(Integer, default=0)
    answered_at = Column(String, nullable=True)
