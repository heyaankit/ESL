"""Onboarding Quiz API — Bestie Live API Handoff Document.

Stores and retrieves 14-screen registration quiz answers.
All endpoints return the legacy format:
    {"status": "1", "data": ..., "message": ...}   — success
    {"status": "0", "data": null, "message": ...}   — failure
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Form
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.quiz import UserQuizData
from app.utils.response import success, error
from app.logger import logger

router = APIRouter(tags=["onboarding"])


# ---------------------------------------------------------------------------
# Pydantic model for JSON body POST /quiz/final-result
# ---------------------------------------------------------------------------

class QuizFinalResultRequest(BaseModel):
    user_id: str
    q1_name: Optional[str] = None
    q2_age: Optional[str] = None
    q3_occupation: Optional[str] = None
    q4_learning_goal: Optional[str] = None
    q5_current_level: Optional[str] = None
    q6_study_frequency: Optional[str] = None
    q7_preferred_topics: Optional[str] = None
    q8_learning_style: Optional[str] = None
    q9_challenges: Optional[str] = None
    q10_previous_experience: Optional[str] = None
    q11_daily_time: Optional[str] = None
    q12_motivation: Optional[str] = None
    q13_pronunciation_focus: Optional[str] = None
    q14_additional_notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

QUIZ_FIELDS = [
    "q1_name", "q2_age", "q3_occupation", "q4_learning_goal",
    "q5_current_level", "q6_study_frequency", "q7_preferred_topics",
    "q8_learning_style", "q9_challenges", "q10_previous_experience",
    "q11_daily_time", "q12_motivation", "q13_pronunciation_focus",
    "q14_additional_notes",
]


def _quiz_to_dict(row: UserQuizData) -> dict:
    """Serialise a UserQuizData ORM object to a plain dict."""
    result = {
        "id": row.id,
        "user_id": row.user_id,
    }
    for field in QUIZ_FIELDS:
        result[field] = getattr(row, field, None)
    result["created_at"] = str(row.created_at) if row.created_at else None
    result["updated_at"] = str(row.updated_at) if row.updated_at else None
    return result


def _compute_learning_level(row: UserQuizData) -> str:
    """Derive a learning_level string from quiz answers."""
    level_map = {
        "beginner": 0,
        "elementary": 1,
        "intermediate": 2,
        "upper-intermediate": 3,
        "advanced": 4,
    }

    current_level = (row.q5_current_level or "").strip().lower()
    experience = (row.q10_previous_experience or "").strip().lower()
    frequency = (row.q6_study_frequency or "").strip().lower()

    score = 0

    # Current self-assessed level
    for key, val in level_map.items():
        if key in current_level:
            score += val
            break

    # Previous experience boost
    if any(w in experience for w in ["fluent", "advanced", "years", "many"]):
        score += 2
    elif any(w in experience for w in ["some", "moderate", "few years"]):
        score += 1

    # Study frequency
    if any(w in frequency for w in ["daily", "every day"]):
        score += 1
    elif any(w in frequency for w in ["weekly", "several times"]):
        score += 0

    # Map total score to level
    if score >= 6:
        return "advanced"
    elif score >= 4:
        return "upper-intermediate"
    elif score >= 3:
        return "intermediate"
    elif score >= 1:
        return "elementary"
    return "beginner"


# ---------------------------------------------------------------------------
# 1. POST /quiz/final-result  (JSON body)
# ---------------------------------------------------------------------------

@router.post("/quiz/final-result")
def store_final_result(
    request: QuizFinalResultRequest,
    db: Session = Depends(get_db),
):
    """Store or update 14-screen registration quiz answers in user_quiz_data."""
    try:
        existing = (
            db.query(UserQuizData)
            .filter(UserQuizData.user_id == request.user_id)
            .first()
        )

        if existing:
            for field in QUIZ_FIELDS:
                val = getattr(request, field, None)
                if val is not None:
                    setattr(existing, field, val)
            existing.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return success(data=_quiz_to_dict(existing), message="Quiz data updated")

        new_quiz = UserQuizData(user_id=request.user_id)
        for field in QUIZ_FIELDS:
            val = getattr(request, field, None)
            if val is not None:
                setattr(new_quiz, field, val)
        db.add(new_quiz)
        db.commit()
        db.refresh(new_quiz)
        return success(data=_quiz_to_dict(new_quiz), message="Quiz data saved")

    except Exception as e:
        logger.error(f"Error storing quiz final result: {e}")
        return error(message=f"Failed to store quiz data: {str(e)}")


# ---------------------------------------------------------------------------
# 2. GET /quiz/registration-results/{user_id}
# ---------------------------------------------------------------------------

@router.get("/quiz/registration-results/{user_id}")
def get_registration_results(user_id: str, db: Session = Depends(get_db)):
    """Return analyzed onboarding output: compute learning_level, return structured analysis."""
    quiz = (
        db.query(UserQuizData)
        .filter(UserQuizData.user_id == user_id)
        .first()
    )
    if not quiz:
        return error(message="No registration quiz data found for this user")

    learning_level = _compute_learning_level(quiz)

    analysis = {
        "user_id": quiz.user_id,
        "name": quiz.q1_name,
        "age": quiz.q2_age,
        "occupation": quiz.q3_occupation,
        "learning_goal": quiz.q4_learning_goal,
        "current_level": quiz.q5_current_level,
        "study_frequency": quiz.q6_study_frequency,
        "preferred_topics": quiz.q7_preferred_topics,
        "learning_style": quiz.q8_learning_style,
        "challenges": quiz.q9_challenges,
        "previous_experience": quiz.q10_previous_experience,
        "daily_time": quiz.q11_daily_time,
        "motivation": quiz.q12_motivation,
        "pronunciation_focus": quiz.q13_pronunciation_focus,
        "additional_notes": quiz.q14_additional_notes,
        "computed_learning_level": learning_level,
        "analysis": {
            "recommended_level": learning_level,
            "study_plan": _generate_study_plan(quiz, learning_level),
            "focus_areas": _identify_focus_areas(quiz),
        },
    }

    return success(data=analysis, message="Registration analysis retrieved")


def _generate_study_plan(quiz: UserQuizData, level: str) -> str:
    """Generate a brief study plan recommendation from quiz answers."""
    frequency = quiz.q6_study_frequency or "not specified"
    daily_time = quiz.q11_daily_time or "not specified"
    topics = quiz.q7_preferred_topics or "general English"

    return (
        f"Based on your {level} level, studying {frequency} for {daily_time} "
        f"each session, focusing on {topics}."
    )


def _identify_focus_areas(quiz: UserQuizData) -> list:
    """Identify focus areas from quiz answers."""
    areas = []
    challenges = (quiz.q9_challenges or "").lower()
    pronunciation = (quiz.q13_pronunciation_focus or "").lower()

    if any(w in challenges for w in ["grammar", "tense", "structure"]):
        areas.append("Grammar")
    if any(w in challenges for w in ["vocabulary", "words", "remember"]):
        areas.append("Vocabulary")
    if any(w in challenges for w in ["speaking", "conversation", "talk"]):
        areas.append("Speaking")
    if any(w in challenges for w in ["listening", "understand", "comprehension"]):
        areas.append("Listening")
    if any(w in challenges for w in ["writing", "spell", "write"]):
        areas.append("Writing")
    if any(w in challenges for w in ["pronunciation", "accent", "sound"]):
        areas.append("Pronunciation")
    if pronunciation and pronunciation not in ("no", "none", "n/a"):
        areas.append("Pronunciation")
    if not areas:
        areas.append("General English")
    return areas


# ---------------------------------------------------------------------------
# 3. GET /quiz/registration-summary/{user_id}
# ---------------------------------------------------------------------------

@router.get("/quiz/registration-summary/{user_id}")
def get_registration_summary(user_id: str, db: Session = Depends(get_db)):
    """Return summarized registration quiz answers (key fields only)."""
    quiz = (
        db.query(UserQuizData)
        .filter(UserQuizData.user_id == user_id)
        .first()
    )
    if not quiz:
        return error(message="No registration quiz data found for this user")

    summary = {
        "user_id": quiz.user_id,
        "name": quiz.q1_name,
        "learning_goal": quiz.q4_learning_goal,
        "current_level": quiz.q5_current_level,
        "study_frequency": quiz.q6_study_frequency,
        "preferred_topics": quiz.q7_preferred_topics,
        "learning_style": quiz.q8_learning_style,
        "motivation": quiz.q12_motivation,
        "computed_level": _compute_learning_level(quiz),
    }

    return success(data=summary, message="Registration summary retrieved")


# ---------------------------------------------------------------------------
# 4. GET /quiz/registration-raw/{user_id}
# ---------------------------------------------------------------------------

@router.get("/quiz/registration-raw/{user_id}")
def get_registration_raw(user_id: str, db: Session = Depends(get_db)):
    """Return raw user_quiz_data fields."""
    quiz = (
        db.query(UserQuizData)
        .filter(UserQuizData.user_id == user_id)
        .first()
    )
    if not quiz:
        return error(message="No registration quiz data found for this user")

    return success(data=_quiz_to_dict(quiz), message="Raw quiz data retrieved")


# ---------------------------------------------------------------------------
# 5. PUT /quiz/update-registration/{user_id}  (form-data fields)
# ---------------------------------------------------------------------------

@router.put("/quiz/update-registration/{user_id}")
def update_registration(
    user_id: str,
    q1_name: Optional[str] = Form(None),
    q2_age: Optional[str] = Form(None),
    q3_occupation: Optional[str] = Form(None),
    q4_learning_goal: Optional[str] = Form(None),
    q5_current_level: Optional[str] = Form(None),
    q6_study_frequency: Optional[str] = Form(None),
    q7_preferred_topics: Optional[str] = Form(None),
    q8_learning_style: Optional[str] = Form(None),
    q9_challenges: Optional[str] = Form(None),
    q10_previous_experience: Optional[str] = Form(None),
    q11_daily_time: Optional[str] = Form(None),
    q12_motivation: Optional[str] = Form(None),
    q13_pronunciation_focus: Optional[str] = Form(None),
    q14_additional_notes: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """Partially update registration quiz fields."""
    quiz = (
        db.query(UserQuizData)
        .filter(UserQuizData.user_id == user_id)
        .first()
    )
    if not quiz:
        return error(message="No registration quiz data found for this user")

    form_fields = {
        "q1_name": q1_name,
        "q2_age": q2_age,
        "q3_occupation": q3_occupation,
        "q4_learning_goal": q4_learning_goal,
        "q5_current_level": q5_current_level,
        "q6_study_frequency": q6_study_frequency,
        "q7_preferred_topics": q7_preferred_topics,
        "q8_learning_style": q8_learning_style,
        "q9_challenges": q9_challenges,
        "q10_previous_experience": q10_previous_experience,
        "q11_daily_time": q11_daily_time,
        "q12_motivation": q12_motivation,
        "q13_pronunciation_focus": q13_pronunciation_focus,
        "q14_additional_notes": q14_additional_notes,
    }

    updated_fields = []
    for field, value in form_fields.items():
        if value is not None:
            setattr(quiz, field, value)
            updated_fields.append(field)

    if updated_fields:
        quiz.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(quiz)

    return success(
        data={
            "updated_fields": updated_fields,
            "quiz": _quiz_to_dict(quiz),
        },
        message=f"Updated fields: {', '.join(updated_fields)}" if updated_fields else "No fields to update",
    )


# ---------------------------------------------------------------------------
# 6. DELETE /quiz/delete-registration/{user_id}
# ---------------------------------------------------------------------------

@router.delete("/quiz/delete-registration/{user_id}")
def delete_registration(user_id: str, db: Session = Depends(get_db)):
    """Delete registration quiz data."""
    quiz = (
        db.query(UserQuizData)
        .filter(UserQuizData.user_id == user_id)
        .first()
    )
    if not quiz:
        return error(message="No registration quiz data found for this user")

    db.delete(quiz)
    db.commit()
    return success(message="Registration quiz data deleted successfully")
