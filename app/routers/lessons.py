from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from typing import Optional, List
from pydantic import BaseModel, Field
from app.database import get_db
from app.models.lesson import LessonItem
from app.config import settings

router = APIRouter()


def _get_concat_agg(col):
    """Return database-specific string aggregation function."""
    if settings.database_url.startswith("postgresql"):
        return func.string_agg(col, ',')
    return func.group_concat(col)


class SubTopicSummary(BaseModel):
    name: str
    item_count: int
    has_exercises: bool


class LessonSummary(BaseModel):
    lesson_id: str
    lesson_name: str
    grammar_topic: Optional[str]
    sub_topics: List[str]
    total_items: int
    has_exercises: bool


class LessonItemResponse(BaseModel):
    id: int
    sub_topic: str
    word_number: Optional[str]
    vocabulary_word: str
    conversation_question: Optional[str]
    conversation_affirmative: Optional[str]
    conversation_interrogative: Optional[str]
    conversation_yes: Optional[str]
    conversation_no: Optional[str]
    grammar_explanation: Optional[str]


class LessonDetail(BaseModel):
    lesson_id: str
    lesson_name: str
    grammar_topic: Optional[str]
    sub_topics: List[str]
    total_items: int
    page: int
    limit: int
    items: List[LessonItemResponse]


@router.get("", response_model=dict)
def list_lessons(db: Session = Depends(get_db)) -> dict:
    lessons_data = db.query(
        LessonItem.lesson,
        func.max(LessonItem.grammar_topic).label("grammar_topic"),
        _get_concat_agg(LessonItem.sub_topic).label("sub_topics"),
        func.count(LessonItem.id).label("total_items"),
    ).group_by(LessonItem.lesson).all()

    result: List[dict] = []
    for row in lessons_data:
        sub_topics = row.sub_topics.split(",") if row.sub_topics else []
        sub_topics = list(set(sub_topics))

        has_exercises = db.query(LessonItem).filter(
            LessonItem.lesson == row.lesson,
            LessonItem.exercise_type.isnot(None)
        ).first() is not None

        lesson_id = row.lesson.split()[0] if row.lesson else ""

        result.append({
            "lesson_id": lesson_id,
            "lesson_name": row.lesson,
            "grammar_topic": row.grammar_topic,
            "sub_topics": sub_topics,
            "total_items": row.total_items,
            "has_exercises": has_exercises
        })

    return {"lessons": result}


@router.get("/{lesson_id}", response_model=LessonDetail)
def get_lesson(
    lesson_id: str,
    sub_topic: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
) -> dict:
    lesson_name = f"{lesson_id} Noun" if lesson_id.startswith("1.") else f"{lesson_id} Noun"

    all_lessons = db.query(LessonItem.lesson).distinct().all()
    matching_lesson: Optional[str] = None
    for l in all_lessons:
        if l.lesson.startswith(lesson_id):
            matching_lesson = l.lesson
            break

    if not matching_lesson:
        raise HTTPException(status_code=404, detail=f"Lesson {lesson_id} not found")

    query = db.query(LessonItem).filter(LessonItem.lesson == matching_lesson)

    if sub_topic:
        query = query.filter(LessonItem.sub_topic == sub_topic)

    total_items = query.count()
    offset = (page - 1) * limit
    items = query.offset(offset).limit(limit).all()

    sub_topics_data = db.query(LessonItem.sub_topic).filter(
        LessonItem.lesson == matching_lesson
    ).distinct().all()
    sub_topics = list(set([s.sub_topic for s in sub_topics_data]))

    grammar_topic = db.query(LessonItem.grammar_topic).filter(
        LessonItem.lesson == matching_lesson
    ).first()

    return {
        "lesson_id": lesson_id,
        "lesson_name": matching_lesson,
        "grammar_topic": grammar_topic.grammar_topic if grammar_topic else None,
        "sub_topics": sub_topics,
        "total_items": total_items,
        "page": page,
        "limit": limit,
        "items": [
            {
                "id": item.id,
                "sub_topic": item.sub_topic,
                "word_number": item.word_number,
                "vocabulary_word": item.vocabulary_word,
                "conversation_question": item.conversation_question,
                "conversation_affirmative": item.conversation_affirmative,
                "conversation_interrogative": item.conversation_interrogative,
                "conversation_yes": item.conversation_yes,
                "conversation_no": item.conversation_no,
                "grammar_explanation": item.grammar_explanation,
            }
            for item in items
        ]
    }


@router.get("/{lesson_id}/subtopics", response_model=dict)
def get_subtopics(lesson_id: str, db: Session = Depends(get_db)) -> dict:
    all_lessons = db.query(LessonItem.lesson).distinct().all()
    matching_lesson: Optional[str] = None
    for l in all_lessons:
        if l.lesson.startswith(lesson_id):
            matching_lesson = l.lesson
            break

    if not matching_lesson:
        raise HTTPException(status_code=404, detail=f"Lesson {lesson_id} not found")

    sub_topics_data = db.query(
        LessonItem.sub_topic,
        func.count(LessonItem.id).label("item_count")
    ).filter(LessonItem.lesson == matching_lesson).group_by(LessonItem.sub_topic).all()

    subtopics: List[dict] = []
    for st in sub_topics_data:
        has_exercises = db.query(LessonItem).filter(
            LessonItem.lesson == matching_lesson,
            LessonItem.sub_topic == st.sub_topic,
            LessonItem.exercise_type.isnot(None)
        ).first() is not None

        subtopics.append({
            "name": st.sub_topic,
            "item_count": st.item_count,
            "has_exercises": has_exercises
        })

    return {"lesson_id": lesson_id, "subtopics": subtopics}


@router.get("/{lesson_id}/items", response_model=dict)
def get_lesson_items(
    lesson_id: str,
    sub_topic: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
) -> dict:
    all_lessons = db.query(LessonItem.lesson).distinct().all()
    matching_lesson: Optional[str] = None
    for l in all_lessons:
        if l.lesson.startswith(lesson_id):
            matching_lesson = l.lesson
            break

    if not matching_lesson:
        raise HTTPException(status_code=404, detail=f"Lesson {lesson_id} not found")

    query = db.query(LessonItem).filter(LessonItem.lesson == matching_lesson)

    if sub_topic:
        query = query.filter(LessonItem.sub_topic == sub_topic)

    total = query.count()
    offset = (page - 1) * limit
    items = query.offset(offset).limit(limit).all()

    return {
        "lesson_id": lesson_id,
        "sub_topic": sub_topic or "all",
        "total": total,
        "page": page,
        "items": [
            {
                "id": item.id,
                "vocabulary_word": item.vocabulary_word,
                "meaning": item.meaning,
                "example_sentence": item.example_sentence,
                "conversation_affirmative": item.conversation_affirmative,
                "grammar_explanation": item.grammar_explanation,
            }
            for item in items
        ]
    }