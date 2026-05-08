from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean
from datetime import datetime
from app.database import Base


class UserQuizData(Base):
    """14-screen onboarding/registration quiz answers."""
    __tablename__ = "user_quiz_data"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True, unique=True)
    q1_name = Column(String, nullable=True)
    q2_age = Column(String, nullable=True)
    q3_occupation = Column(String, nullable=True)
    q4_learning_goal = Column(Text, nullable=True)
    q5_current_level = Column(String, nullable=True)
    q6_study_frequency = Column(String, nullable=True)
    q7_preferred_topics = Column(Text, nullable=True)
    q8_learning_style = Column(String, nullable=True)
    q9_challenges = Column(Text, nullable=True)
    q10_previous_experience = Column(String, nullable=True)
    q11_daily_time = Column(String, nullable=True)
    q12_motivation = Column(Text, nullable=True)
    q13_pronunciation_focus = Column(String, nullable=True)
    q14_additional_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class QuizHistory(Base):
    """Generated quiz questions, options, correct answers, user answers, attempts."""
    __tablename__ = "quiz_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    lesson_topic = Column(String, nullable=True)
    question = Column(Text, nullable=True)
    options = Column(Text, nullable=True)  # JSON array of options
    correct_answer = Column(Text, nullable=True)
    user_answer = Column(Text, nullable=True)
    is_correct = Column(Integer, default=0)
    mode = Column(String, default="multiple_choice")  # multiple_choice, fill_blank, conversation
    db_mode = Column(String, nullable=True)
    attempts = Column(Integer, default=0)
    skipped = Column(Integer, default=0)
    offset = Column(Integer, default=0)
    session_id = Column(String, nullable=True)
    feedback = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
