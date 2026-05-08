from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.database import get_db
from app.models.lesson import LessonItem
from app.models.user import User, UserProgress
from app.auth import get_current_user

router = APIRouter()


class ProgressRecord(BaseModel):
    item_id: int = Field(..., gt=0)
    activity_type: str = Field(..., pattern="^(word_viewed|exercise_attempt)$")
    correct: Optional[bool] = None
    response: Optional[str] = None
    time_spent_seconds: Optional[int] = Field(None, ge=0)


@router.post("/{user_id}/progress", response_model=dict)
def record_progress(
    user_id: str,
    progress: ProgressRecord,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    if current_user.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this user's progress")
    existing_user = db.query(User).filter(User.user_id == user_id).first()
    if not existing_user:
        new_user = User(user_id=user_id)
        db.add(new_user)
        db.commit()

    record = UserProgress(
        user_id=user_id,
        item_id=progress.item_id,
        viewed=progress.activity_type == "word_viewed",
        correct=progress.correct if progress.correct is not None else False,
        last_reviewed=datetime.utcnow()
    )
    db.add(record)
    db.commit()

    words_viewed = db.query(UserProgress).filter(
        UserProgress.user_id == user_id,
        UserProgress.viewed == True
    ).count()

    exercises_completed = db.query(UserProgress).filter(
        UserProgress.user_id == user_id,
        UserProgress.correct.isnot(None)
    ).count()

    return {
        "user_id": user_id,
        "recorded": True,
        "total_words_learned": words_viewed,
        "total_exercises_completed": exercises_completed
    }


@router.get("/{user_id}/progress", response_model=dict)
def get_progress(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    if current_user.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this user's progress")
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        return {
            "user_id": user_id,
            "total_words_viewed": 0,
            "total_words_learned": 0,
            "total_exercises_completed": 0,
            "total_exercises_correct": 0,
            "accuracy_percent": 0,
            "lessons_progress": []
        }

    words_viewed = db.query(UserProgress).filter(
        UserProgress.user_id == user_id,
        UserProgress.viewed == True
    ).count()

    exercises = db.query(UserProgress).filter(
        UserProgress.user_id == user_id,
        UserProgress.correct.isnot(None)
    ).all()

    exercises_completed = len(exercises)
    exercises_correct = sum(1 for e in exercises if e.correct)
    accuracy = round((exercises_correct / exercises_completed * 100), 1) if exercises_completed > 0 else 0

    lesson_progress_data = db.query(
        LessonItem.lesson,
        func.count(LessonItem.id).label("total")
    ).group_by(LessonItem.lesson).all()

    lessons_list: List[dict] = []
    for lp in lesson_progress_data:
        viewed_count = db.query(UserProgress).join(
            LessonItem, UserProgress.item_id == LessonItem.id
        ).filter(
            UserProgress.user_id == user_id,
            LessonItem.lesson == lp.lesson,
            UserProgress.viewed == True
        ).count()

        lessons_list.append({
            "lesson_id": lp.lesson.split()[0] if lp.lesson else "",
            "lesson_name": lp.lesson,
            "items_total": lp.total,
            "items_viewed": viewed_count,
            "items_learned": viewed_count,
            "progress_percent": round((viewed_count / lp.total * 100), 1) if lp.total > 0 else 0
        })

    return {
        "user_id": user_id,
        "total_words_viewed": words_viewed,
        "total_words_learned": words_viewed,
        "total_exercises_completed": exercises_completed,
        "total_exercises_correct": exercises_correct,
        "accuracy_percent": accuracy,
        "lessons_progress": lessons_list
    }


@router.get("/{user_id}/weak-words", response_model=dict)
def get_weak_words(
    user_id: str,
    lesson: Optional[str] = None,
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    if current_user.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this user's progress")
    query = db.query(
        LessonItem.id,
        LessonItem.vocabulary_word,
        LessonItem.lesson,
        LessonItem.sub_topic,
        func.count(UserProgress.id).label("incorrect_count"),
        func.max(UserProgress.last_reviewed).label("last_attempt")
    ).join(
        UserProgress,
        (UserProgress.item_id == LessonItem.id) &
        (UserProgress.user_id == user_id) &
        (UserProgress.correct == False)
    ).group_by(LessonItem.id)

    if lesson:
        query = query.filter(LessonItem.lesson.like(f"{lesson}%"))

    weak_words = query.order_by(func.count(UserProgress.id).desc()).limit(limit).all()

    return {
        "user_id": user_id,
        "weak_word_count": len(weak_words),
        "words": [
            {
                "item_id": w.id,
                "vocabulary_word": w.vocabulary_word,
                "lesson": w.lesson,
                "sub_topic": w.sub_topic,
                "incorrect_count": w.incorrect_count,
                "last_attempt": w.last_attempt.isoformat() if w.last_attempt else None
            }
            for w in weak_words
        ]
    }