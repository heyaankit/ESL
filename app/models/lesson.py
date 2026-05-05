from sqlalchemy import Column, Integer, String, Text
from app.database import Base


class LessonItem(Base):
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