from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
from pydantic import BaseModel, Field
from app.database import get_db
from app.models.lesson import LessonItem
from app.utils.response import success, error

router = APIRouter()


class AnswerCheck(BaseModel):
    item_id: int = Field(..., gt=0)
    response: str


class ExerciseCheckRequest(BaseModel):
    user_id: str
    answers: List[AnswerCheck]


@router.get("")
def list_exercises(
    lesson: Optional[str] = Query(None),
    sub_topic: Optional[str] = Query(None),
    db: Session = Depends(get_db)
) -> dict:
    """List exercise groups grouped by lesson/sub_topic/exercise_type."""
    query = db.query(
        LessonItem.lesson,
        LessonItem.sub_topic,
        LessonItem.exercise_type,
        func.count(LessonItem.id).label("item_count")
    ).filter(LessonItem.exercise_type.isnot(None))

    if lesson:
        query = query.filter(LessonItem.lesson.like(f"{lesson}%"))
    if sub_topic:
        query = query.filter(LessonItem.sub_topic == sub_topic)

    results = query.group_by(
        LessonItem.lesson,
        LessonItem.sub_topic,
        LessonItem.exercise_type
    ).all()

    return success(data={
        "total": len(results),
        "exercises": [
            {
                "lesson": r.lesson,
                "sub_topic": r.sub_topic,
                "exercise_type": r.exercise_type,
                "item_count": r.item_count
            }
            for r in results
        ]
    }, message="Exercises listed")


@router.get("/{exercise_id}")
def get_exercise(exercise_id: str, db: Session = Depends(get_db)) -> dict:
    """Get exercise items for a lesson."""
    parts = exercise_id.split("_")
    lesson_id = parts[0]

    all_lessons = db.query(LessonItem.lesson).distinct().all()
    matching_lesson: Optional[str] = None
    for l in all_lessons:
        if l.lesson.startswith(lesson_id):
            matching_lesson = l.lesson
            break

    if not matching_lesson:
        return error(message="Exercise not found")

    items = db.query(LessonItem).filter(
        LessonItem.lesson == matching_lesson,
        LessonItem.exercise_answers.isnot(None)
    ).all()

    if not items:
        return error(message="Exercise not found")

    return success(data={
        "exercise_id": exercise_id,
        "lesson": matching_lesson,
        "sub_topic": items[0].sub_topic if items else None,
        "exercise_type": items[0].exercise_type if items else None,
        "items": [
            {
                "id": item.id,
                "vocabulary_word": item.vocabulary_word,
                "exercise_answers": item.exercise_answers,
            }
            for item in items if item.exercise_answers
        ]
    }, message="Exercise items retrieved")


@router.post("/{exercise_id}/check")
def check_exercise(
    exercise_id: str,
    request: ExerciseCheckRequest,
    db: Session = Depends(get_db)
) -> dict:
    """Check exercise answers and return score."""
    results: List[dict] = []
    correct_count = 0

    for answer in request.answers:
        item = db.query(LessonItem).filter(LessonItem.id == answer.item_id).first()

        if not item or not item.exercise_answers:
            results.append({
                "item_id": answer.item_id,
                "response": answer.response,
                "correct": False,
                "expected": None
            })
            continue

        expected_answers = [a.strip() for a in item.exercise_answers.split(";")]
        is_correct = answer.response.strip() in expected_answers

        if is_correct:
            correct_count += 1

        results.append({
            "item_id": answer.item_id,
            "response": answer.response,
            "correct": is_correct,
            "expected": expected_answers[0] if expected_answers else None
        })

    total = len(results)
    score_percent = round((correct_count / total * 100), 1) if total > 0 else 0

    return success(data={
        "exercise_id": exercise_id,
        "total_questions": total,
        "correct": correct_count,
        "score_percent": score_percent,
        "results": results
    }, message="Exercise checked")
