from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from app.database import get_db
from app.models.lesson import LessonItem

router = APIRouter()


@router.get("", response_model=dict)
def list_grammar(
    lesson: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(
        LessonItem.id,
        LessonItem.lesson,
        LessonItem.sub_topic,
        LessonItem.grammar_topic,
        LessonItem.grammar_explanation,
        LessonItem.vocabulary_word
    ).filter(LessonItem.grammar_explanation.isnot(None))

    if lesson:
        query = query.filter(LessonItem.lesson.like(f"{lesson}%"))

    if q:
        query = query.filter(LessonItem.grammar_explanation.like(f"%{q}%"))

    total = query.count()
    offset = (page - 1) * limit
    items = query.offset(offset).limit(limit).all()

    return {
        "total": total,
        "explanations": [
            {
                "id": item.id,
                "lesson": item.lesson,
                "sub_topic": item.sub_topic,
                "grammar_topic": item.grammar_topic,
                "grammar_explanation": item.grammar_explanation,
                "vocabulary_word": item.vocabulary_word,
            }
            for item in items
        ]
    }


@router.get("/{lesson_id}", response_model=dict)
def get_grammar_by_lesson(lesson_id: str, db: Session = Depends(get_db)):
    all_lessons = db.query(LessonItem.lesson).distinct().all()
    matching_lesson = None
    for l in all_lessons:
        if l.lesson.startswith(lesson_id):
            matching_lesson = l.lesson
            break

    if not matching_lesson:
        raise HTTPException(status_code=404, detail=f"Lesson {lesson_id} not found")

    items = db.query(
        LessonItem.id,
        LessonItem.sub_topic,
        LessonItem.grammar_explanation
    ).filter(
        LessonItem.lesson == matching_lesson,
        LessonItem.grammar_explanation.isnot(None)
    ).distinct().all()

    explanations = []
    seen = set()
    for item in items:
        if item.grammar_explanation and item.grammar_explanation not in seen:
            explanations.append({
                "id": item.id,
                "sub_topic": item.sub_topic,
                "grammar_explanation": item.grammar_explanation,
            })
            seen.add(item.grammar_explanation)

    return {
        "lesson_id": lesson_id,
        "lesson_name": matching_lesson,
        "grammar_explanations": explanations
    }