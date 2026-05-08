"""AI Quiz API — Bestie Live API Handoff Document.

Generates and evaluates quiz questions using AI service and lesson items.
All endpoints return the legacy format:
    {"status": "1", "data": ..., "message": ...}   — success
    {"status": "0", "data": null, "message": ...}   — failure
"""
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Form
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.quiz import QuizHistory, UserQuizData
from app.models.lesson import LessonItem
from app.services.ai_service import ai_service
from app.utils.response import success, error
from app.logger import logger

router = APIRouter(tags=["quiz"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _quiz_history_to_dict(row: QuizHistory) -> dict:
    """Serialise a QuizHistory ORM object to a plain dict."""
    options_raw = row.options
    if isinstance(options_raw, str):
        try:
            options_parsed = json.loads(options_raw)
        except (json.JSONDecodeError, TypeError):
            options_parsed = [options_raw] if options_raw else []
    elif isinstance(options_raw, list):
        options_parsed = options_raw
    else:
        options_parsed = []

    return {
        "id": row.id,
        "user_id": row.user_id,
        "lesson_topic": row.lesson_topic,
        "question": row.question,
        "options": options_parsed,
        "correct_answer": row.correct_answer,
        "user_answer": row.user_answer,
        "is_correct": row.is_correct,
        "mode": row.mode,
        "db_mode": row.db_mode,
        "attempts": row.attempts,
        "skipped": row.skipped,
        "offset": row.offset,
        "session_id": row.session_id,
        "feedback": row.feedback,
        "created_at": str(row.created_at) if row.created_at else None,
    }


def _get_user_difficulty(user_id: str, db: Session) -> str:
    """Determine user difficulty level from quiz data or user profile."""
    quiz_data = (
        db.query(UserQuizData)
        .filter(UserQuizData.user_id == user_id)
        .first()
    )
    if quiz_data and quiz_data.q5_current_level:
        level = quiz_data.q5_current_level.strip().lower()
        if level in ("advanced", "upper-intermediate", "intermediate", "elementary", "beginner"):
            return level
    return "beginner"


def _lesson_item_to_question(item: LessonItem, mode: str) -> dict:
    """Convert a LessonItem into a quiz question dict."""
    # Try conversation question first, then vocabulary
    question_text = item.conversation_question or f"What does '{item.vocabulary_word}' mean?"
    correct = item.conversation_affirmative or item.meaning or item.vocabulary_word

    # Build options from available fields
    options = []
    if item.conversation_yes:
        options.append(item.conversation_yes)
    if item.conversation_no:
        options.append(item.conversation_no)
    if item.conversation_interrogative:
        options.append(item.conversation_interrogative)

    # Ensure we have at least 4 options for multiple_choice
    if mode == "multiple_choice":
        options.insert(0, correct)
        # Pad with distractors if needed
        while len(options) < 4:
            options.append(f"(distractor {len(options) + 1})")
        # Remove duplicates preserving order
        seen = set()
        unique_options = []
        for o in options:
            if o not in seen:
                seen.add(o)
                unique_options.append(o)
        options = unique_options[:4]

    return {
        "question": question_text,
        "options": options,
        "correct_answer": correct,
        "feedback": item.grammar_explanation or f"This is about '{item.vocabulary_word}'.",
        "item_id": item.id,
        "db_mode": True,
    }


# ---------------------------------------------------------------------------
# 1. POST /quiz/next-question  (form-data)
# ---------------------------------------------------------------------------

@router.post("/quiz/next-question")
def next_question(
    user_id: str = Form(...),
    lesson_topic: str = Form(...),
    mode: str = Form("multiple_choice"),
    db_mode: str = Form(None),
    skip: str = Form("0"),
    offset: str = Form(None),
    db: Session = Depends(get_db),
):
    """Generate or retrieve the next quiz question for a lesson topic.

    - If skip=1, mark the current question as skipped first.
    - If db_mode is set, try to get question from lesson_items first.
    - Store generated question in quiz_history.
    - Return question with options.
    """
    try:
        skip_flag = skip == "1"
        offset_val = int(offset) if offset else None

        # If skip=1, mark the current question as skipped
        if skip_flag and offset_val is not None:
            current = (
                db.query(QuizHistory)
                .filter(
                    QuizHistory.user_id == user_id,
                    QuizHistory.lesson_topic == lesson_topic,
                    QuizHistory.offset == offset_val,
                )
                .first()
            )
            if current:
                current.skipped = 1
                db.commit()

        # Determine next offset
        if offset_val is not None:
            next_offset = offset_val + 1
        else:
            # Find max offset for this user/topic
            max_row = (
                db.query(QuizHistory)
                .filter(
                    QuizHistory.user_id == user_id,
                    QuizHistory.lesson_topic == lesson_topic,
                )
                .order_by(QuizHistory.offset.desc())
                .first()
            )
            next_offset = (max_row.offset + 1) if max_row else 0

        # Check if we already have this offset stored
        existing = (
            db.query(QuizHistory)
            .filter(
                QuizHistory.user_id == user_id,
                QuizHistory.lesson_topic == lesson_topic,
                QuizHistory.offset == next_offset,
            )
            .first()
        )
        if existing:
            return success(
                data=_quiz_history_to_dict(existing),
                message="Next question retrieved from history",
            )

        # Try to get question from lesson_items if db_mode is set
        question_data = None
        if db_mode:
            lesson_items = (
                db.query(LessonItem)
                .filter(LessonItem.lesson.ilike(f"%{lesson_topic}%"))
                .all()
            )
            if lesson_items:
                # Pick the item at next_offset (cycling if needed)
                idx = next_offset % len(lesson_items)
                question_data = _lesson_item_to_question(lesson_items[idx], mode)

        # Fall back to AI generation if no db_mode or no lesson items found
        if not question_data:
            difficulty = _get_user_difficulty(user_id, db)
            question_data = ai_service.generate_quiz_question(
                lesson_topic=lesson_topic,
                mode=mode,
                difficulty=difficulty,
            )
            question_data["db_mode"] = False

        # Store in quiz_history
        new_entry = QuizHistory(
            user_id=user_id,
            lesson_topic=lesson_topic,
            question=question_data.get("question", ""),
            options=json.dumps(question_data.get("options", [])),
            correct_answer=question_data.get("correct_answer", ""),
            mode=mode,
            db_mode="1" if question_data.get("db_mode") else None,
            offset=next_offset,
            feedback=question_data.get("feedback", ""),
        )
        db.add(new_entry)
        db.commit()
        db.refresh(new_entry)

        return success(
            data=_quiz_history_to_dict(new_entry),
            message="Next question generated",
        )

    except Exception as e:
        logger.error(f"Error generating next question: {e}")
        return error(message=f"Failed to generate next question: {str(e)}")


# ---------------------------------------------------------------------------
# 2. POST /quiz/previous-question  (form-data)
# ---------------------------------------------------------------------------

@router.post("/quiz/previous-question")
def previous_question(
    user_id: str = Form(...),
    offset: str = Form(...),
    db: Session = Depends(get_db),
):
    """Fetch prior quiz question by offset from quiz_history."""
    try:
        offset_val = int(offset)
        prev_offset = offset_val - 1

        if prev_offset < 0:
            return error(message="No previous question available")

        row = (
            db.query(QuizHistory)
            .filter(
                QuizHistory.user_id == user_id,
                QuizHistory.offset == prev_offset,
            )
            .order_by(QuizHistory.id.desc())
            .first()
        )

        if not row:
            return error(message="Previous question not found")

        return success(
            data=_quiz_history_to_dict(row),
            message="Previous question retrieved",
        )

    except ValueError:
        return error(message="Invalid offset value")
    except Exception as e:
        logger.error(f"Error fetching previous question: {e}")
        return error(message=f"Failed to fetch previous question: {str(e)}")


# ---------------------------------------------------------------------------
# 3. POST /quiz/answer  (form-data)
# ---------------------------------------------------------------------------

@router.post("/quiz/answer")
def submit_answer(
    user_id: str = Form(...),
    question_id: str = Form(...),
    answer: str = Form(...),
    mode: str = Form("multiple_choice"),
    db: Session = Depends(get_db),
):
    """Evaluate answer with exact/fuzzy/AI logic.

    - Record attempt, correctness, and progress.
    - Return feedback.
    """
    try:
        question_id_int = int(question_id)
    except ValueError:
        return error(message="Invalid question_id")

    try:
        row = (
            db.query(QuizHistory)
            .filter(
                QuizHistory.id == question_id_int,
                QuizHistory.user_id == user_id,
            )
            .first()
        )
        if not row:
            return error(message="Question not found")

        correct_answer = row.correct_answer or ""
        user_answer = answer.strip()

        # Increment attempt count
        row.attempts = (row.attempts or 0) + 1

        # Evaluate the answer
        evaluation = _evaluate_answer(
            question=row.question or "",
            user_answer=user_answer,
            correct_answer=correct_answer,
            mode=mode,
        )

        # Update quiz history
        row.user_answer = user_answer
        row.is_correct = 1 if evaluation["is_correct"] else 0
        row.feedback = evaluation.get("feedback", "")

        db.commit()
        db.refresh(row)

        result = _quiz_history_to_dict(row)
        result["evaluation"] = evaluation

        return success(
            data=result,
            message="Answer evaluated",
        )

    except Exception as e:
        logger.error(f"Error evaluating answer: {e}")
        return error(message=f"Failed to evaluate answer: {str(e)}")


def _evaluate_answer(
    question: str,
    user_answer: str,
    correct_answer: str,
    mode: str,
) -> dict:
    """Multi-strategy answer evaluation: exact → fuzzy → AI."""
    ua = user_answer.strip().lower()
    ca = correct_answer.strip().lower()

    # 1) Exact match
    if ua == ca:
        return {
            "is_correct": True,
            "feedback": "Correct! Well done!",
            "score": 100,
            "match_type": "exact",
        }

    # 2) Semicolon-delimited acceptable answers
    acceptable = [a.strip().lower() for a in correct_answer.split(";")]
    if ua in acceptable:
        return {
            "is_correct": True,
            "feedback": "Correct!",
            "score": 100,
            "match_type": "exact_list",
        }

    # 3) Fuzzy match — user answer contained in correct or vice versa
    if ua and ca and (ua in ca or ca in ua):
        return {
            "is_correct": True,
            "feedback": "Close enough! Your answer is acceptable.",
            "score": 80,
            "match_type": "fuzzy",
        }

    # 4) AI evaluation for fill_blank / conversation modes
    if mode in ("fill_blank", "conversation") and ai_service.is_available:
        try:
            ai_result = ai_service.evaluate_answer(question, user_answer, correct_answer)
            return {
                "is_correct": ai_result.get("is_correct", False),
                "feedback": ai_result.get("feedback", ""),
                "score": ai_result.get("score", 0),
                "match_type": "ai",
            }
        except Exception as e:
            logger.warning(f"AI evaluation failed, falling back: {e}")

    # 5) Default — incorrect
    return {
        "is_correct": False,
        "feedback": f"Incorrect. The correct answer is: {correct_answer}",
        "score": 0,
        "match_type": "none",
    }
