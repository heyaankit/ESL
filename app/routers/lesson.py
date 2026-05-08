"""Dynamic Lesson API — Bestie Live API Handoff Document.

Excel-backed dynamic lessons with progress tracking, TTS audio, and voice answers.
All endpoints return the legacy format:
    {"status": "1", "data": ..., "message": ...}   — success
    {"status": "0", "data": null, "message": ...}   — failure
"""
import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Form, File, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.lesson import (
    LessonItem,
    LessonProgress,
    LessonAnswer,
    QuestionAttempt,
)
from app.services.audio_service import audio_service
from app.config import settings
from app.utils.response import success, error
from app.logger import logger

router = APIRouter(tags=["lesson"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _progress_to_dict(row: LessonProgress) -> dict:
    return {
        "id": row.id,
        "user_id": row.user_id,
        "lesson_id": row.lesson_id,
        "current_question_index": row.current_question_index,
        "total_questions": row.total_questions,
        "correct_count": row.correct_count,
        "incorrect_count": row.incorrect_count,
        "completed": row.completed,
        "started_at": row.started_at,
        "last_activity": row.last_activity,
    }


def _answer_to_dict(row: LessonAnswer) -> dict:
    return {
        "id": row.id,
        "user_id": row.user_id,
        "lesson_id": row.lesson_id,
        "item_id": row.item_id,
        "user_answer": row.user_answer,
        "expected_answer": row.expected_answer,
        "is_correct": row.is_correct,
        "attempt_number": row.attempt_number,
        "answered_at": row.answered_at,
    }


def _attempt_to_dict(row: QuestionAttempt) -> dict:
    return {
        "id": row.id,
        "user_id": row.user_id,
        "lesson_id": row.lesson_id,
        "item_id": row.item_id,
        "attempts": row.attempts,
        "revealed": row.revealed,
        "last_attempt_at": row.last_attempt_at,
    }


def _item_to_dict(item: LessonItem) -> dict:
    return {
        "id": item.id,
        "lesson": item.lesson,
        "sub_topic": item.sub_topic,
        "grammar_topic": item.grammar_topic,
        "word_number": item.word_number,
        "vocabulary_word": item.vocabulary_word,
        "meaning": item.meaning,
        "example_sentence": item.example_sentence,
        "conversation_question": item.conversation_question,
        "conversation_affirmative": item.conversation_affirmative,
        "conversation_interrogative": item.conversation_interrogative,
        "conversation_yes": item.conversation_yes,
        "conversation_no": item.conversation_no,
        "grammar_explanation": item.grammar_explanation,
        "exercise_type": item.exercise_type,
        "exercise_answers": item.exercise_answers,
        "notes": item.notes,
    }


def _get_lesson_items(db: Session, lesson_id: str) -> list:
    """Get all items for a lesson, matching by prefix."""
    all_lessons = db.query(LessonItem.lesson).distinct().all()
    matching_lesson = None
    for l in all_lessons:
        if l.lesson.startswith(lesson_id):
            matching_lesson = l.lesson
            break

    if not matching_lesson:
        return []

    return (
        db.query(LessonItem)
        .filter(LessonItem.lesson == matching_lesson)
        .order_by(LessonItem.id)
        .all()
    )


def _get_or_create_progress(
    user_id: str, lesson_id: str, db: Session
) -> Optional[LessonProgress]:
    """Get or create a LessonProgress row."""
    progress = (
        db.query(LessonProgress)
        .filter(
            LessonProgress.user_id == user_id,
            LessonProgress.lesson_id == lesson_id,
        )
        .first()
    )
    return progress


def _check_answer(user_answer: str, expected_answer: str) -> bool:
    """Check if user answer matches expected answer (fuzzy)."""
    ua = user_answer.strip().lower()
    ea = expected_answer.strip().lower()

    if not ua or not ea:
        return False

    # Exact match
    if ua == ea:
        return True

    # Semicolon-delimited acceptable answers
    acceptable = [a.strip().lower() for a in expected_answer.split(";")]
    if ua in acceptable:
        return True

    # Fuzzy: user answer contained in expected or vice versa
    if ua in ea or ea in ua:
        return True

    return False


def _now_str() -> str:
    return datetime.utcnow().isoformat()


# ---------------------------------------------------------------------------
# 1. GET /lesson/list
# ---------------------------------------------------------------------------

@router.get("/list")
def list_lessons(db: Session = Depends(get_db)):
    """List dynamic Excel-backed lessons (from lesson_items distinct lessons with counts)."""
    try:
        lessons_data = (
            db.query(
                LessonItem.lesson,
                func.count(LessonItem.id).label("total_items"),
            )
            .group_by(LessonItem.lesson)
            .all()
        )

        result = []
        for row in lessons_data:
            lesson_id = row.lesson.split()[0] if row.lesson else ""
            result.append({
                "lesson_id": lesson_id,
                "lesson_name": row.lesson,
                "total_items": row.total_items,
            })

        return success(
            data={"lessons": result, "count": len(result)},
            message="Lessons listed",
        )
    except Exception as e:
        logger.error(f"Error listing lessons: {e}")
        return error(message=f"Failed to list lessons: {str(e)}")


# ---------------------------------------------------------------------------
# 2. POST /lesson/start  (form-data: user_id, lesson_id)
# ---------------------------------------------------------------------------

@router.post("/start")
def start_lesson(
    user_id: str = Form(...),
    lesson_id: str = Form(...),
    db: Session = Depends(get_db),
):
    """Start a dynamic lesson, initialize lesson_progress."""
    try:
        items = _get_lesson_items(db, lesson_id)
        if not items:
            return error(message=f"Lesson not found: {lesson_id}")

        # Check existing progress
        existing = _get_or_create_progress(user_id, lesson_id, db)
        if existing and existing.completed == 0:
            return success(
                data=_progress_to_dict(existing),
                message="Lesson already in progress",
            )

        if existing and existing.completed == 1:
            # Reset completed lesson
            existing.current_question_index = 0
            existing.correct_count = 0
            existing.incorrect_count = 0
            existing.completed = 0
            existing.started_at = _now_str()
            existing.last_activity = _now_str()
            db.commit()
            db.refresh(existing)
            return success(
                data=_progress_to_dict(existing),
                message="Lesson restarted",
            )

        # Create new progress
        # Use the full lesson name as the lesson_id in progress
        full_lesson_name = items[0].lesson

        progress = LessonProgress(
            user_id=user_id,
            lesson_id=lesson_id,
            current_question_index=0,
            total_questions=len(items),
            correct_count=0,
            incorrect_count=0,
            completed=0,
            started_at=_now_str(),
            last_activity=_now_str(),
        )
        db.add(progress)
        db.commit()
        db.refresh(progress)

        return success(
            data=_progress_to_dict(progress),
            message="Lesson started",
        )
    except Exception as e:
        logger.error(f"Error starting lesson: {e}")
        return error(message=f"Failed to start lesson: {str(e)}")


# ---------------------------------------------------------------------------
# 3. POST /lesson/next  (form-data: user_id, lesson_id)
# ---------------------------------------------------------------------------

@router.post("/next")
def next_question(
    user_id: str = Form(...),
    lesson_id: str = Form(...),
    db: Session = Depends(get_db),
):
    """Return next question from dynamic lesson, update current question state."""
    try:
        progress = _get_or_create_progress(user_id, lesson_id, db)
        if not progress:
            return error(message="Lesson not started. Call /lesson/start first.")

        items = _get_lesson_items(db, lesson_id)
        if not items:
            return error(message=f"Lesson not found: {lesson_id}")

        idx = progress.current_question_index or 0

        # Check if lesson is completed
        if idx >= len(items):
            progress.completed = 1
            progress.last_activity = _now_str()
            db.commit()
            db.refresh(progress)
            return success(
                data={
                    "progress": _progress_to_dict(progress),
                    "question": None,
                    "status": "completed",
                },
                message="Lesson completed! No more questions.",
            )

        item = items[idx]

        # Build question payload — don't reveal the answer
        question_data = {
            "item_id": item.id,
            "question_index": idx,
            "total_questions": len(items),
            "sub_topic": item.sub_topic,
            "vocabulary_word": item.vocabulary_word,
            "exercise_type": item.exercise_type,
            "conversation_question": item.conversation_question,
            "example_sentence": item.example_sentence,
            "grammar_explanation": item.grammar_explanation,
        }

        # Add conversation prompts for conversation-type exercises
        if item.exercise_type in ("conversation", "conversation_question"):
            question_data["conversation_affirmative"] = item.conversation_affirmative
            question_data["conversation_interrogative"] = item.conversation_interrogative

        progress.last_activity = _now_str()
        db.commit()

        return success(
            data={
                "progress": _progress_to_dict(progress),
                "question": question_data,
            },
            message="Next question retrieved",
        )
    except Exception as e:
        logger.error(f"Error getting next question: {e}")
        return error(message=f"Failed to get next question: {str(e)}")


# ---------------------------------------------------------------------------
# 4. POST /lesson/next-with-audio  (form-data: user_id, lesson_id)
# ---------------------------------------------------------------------------

@router.post("/next-with-audio")
def next_question_with_audio(
    user_id: str = Form(...),
    lesson_id: str = Form(...),
    db: Session = Depends(get_db),
):
    """Same as next plus generated TTS audio URL."""
    try:
        # Get the next question first (reuse logic)
        progress = _get_or_create_progress(user_id, lesson_id, db)
        if not progress:
            return error(message="Lesson not started. Call /lesson/start first.")

        items = _get_lesson_items(db, lesson_id)
        if not items:
            return error(message=f"Lesson not found: {lesson_id}")

        idx = progress.current_question_index or 0

        if idx >= len(items):
            progress.completed = 1
            progress.last_activity = _now_str()
            db.commit()
            db.refresh(progress)
            return success(
                data={
                    "progress": _progress_to_dict(progress),
                    "question": None,
                    "audio_url": None,
                    "status": "completed",
                },
                message="Lesson completed! No more questions.",
            )

        item = items[idx]

        # Build question data
        question_data = {
            "item_id": item.id,
            "question_index": idx,
            "total_questions": len(items),
            "sub_topic": item.sub_topic,
            "vocabulary_word": item.vocabulary_word,
            "exercise_type": item.exercise_type,
            "conversation_question": item.conversation_question,
            "example_sentence": item.example_sentence,
            "grammar_explanation": item.grammar_explanation,
        }

        if item.exercise_type in ("conversation", "conversation_question"):
            question_data["conversation_affirmative"] = item.conversation_affirmative
            question_data["conversation_interrogative"] = item.conversation_interrogative

        # Generate TTS audio for the question text
        audio_url = None
        tts_text = item.conversation_question or item.vocabulary_word or item.example_sentence or ""
        if tts_text:
            audio_result = audio_service.generate_tts_audio(tts_text)
            if audio_result:
                filename = f"{user_id}_{lesson_id}_{idx}_{uuid.uuid4().hex[:8]}.mp3"
                file_path = audio_service.save_audio_file(
                    audio_result["audio_content"],
                    filename,
                    subdir="lesson_tts",
                )
                if file_path:
                    audio_url = f"/uploads/lesson_tts/{filename}"

        progress.last_activity = _now_str()
        db.commit()

        return success(
            data={
                "progress": _progress_to_dict(progress),
                "question": question_data,
                "audio_url": audio_url,
            },
            message="Next question with audio retrieved",
        )
    except Exception as e:
        logger.error(f"Error getting next question with audio: {e}")
        return error(message=f"Failed to get next question with audio: {str(e)}")


# ---------------------------------------------------------------------------
# 5. POST /lesson/submit-answer  (form-data: user_id, lesson_id, item_id, answer)
# ---------------------------------------------------------------------------

@router.post("/submit-answer")
def submit_answer(
    user_id: str = Form(...),
    lesson_id: str = Form(...),
    item_id: str = Form(...),
    answer: str = Form(...),
    db: Session = Depends(get_db),
):
    """Check text answer, track attempts, store answer, update progress, may reveal/hint."""
    try:
        item_id_int = int(item_id)
    except ValueError:
        return error(message="Invalid item_id")

    try:
        progress = _get_or_create_progress(user_id, lesson_id, db)
        if not progress:
            return error(message="Lesson not started. Call /lesson/start first.")

        # Get the lesson item
        item = db.query(LessonItem).filter(LessonItem.id == item_id_int).first()
        if not item:
            return error(message="Lesson item not found")

        # Determine expected answer
        expected = (
            item.conversation_affirmative
            or item.vocabulary_word
            or item.meaning
            or item.exercise_answers
            or ""
        )

        # Check answer
        is_correct = _check_answer(answer, expected)

        # Get or create attempt tracker
        attempt = (
            db.query(QuestionAttempt)
            .filter(
                QuestionAttempt.user_id == user_id,
                QuestionAttempt.lesson_id == lesson_id,
                QuestionAttempt.item_id == item_id_int,
            )
            .first()
        )

        if attempt:
            attempt.attempts = (attempt.attempts or 0) + 1
            attempt.last_attempt_at = _now_str()
        else:
            attempt = QuestionAttempt(
                user_id=user_id,
                lesson_id=lesson_id,
                item_id=item_id_int,
                attempts=1,
                revealed=0,
                last_attempt_at=_now_str(),
            )
            db.add(attempt)

        # Store answer
        answer_record = LessonAnswer(
            user_id=user_id,
            lesson_id=lesson_id,
            item_id=item_id_int,
            user_answer=answer,
            expected_answer=expected,
            is_correct=1 if is_correct else 0,
            attempt_number=attempt.attempts,
            answered_at=_now_str(),
        )
        db.add(answer_record)

        # Update progress
        if is_correct:
            progress.correct_count = (progress.correct_count or 0) + 1
            progress.current_question_index = (progress.current_question_index or 0) + 1
        else:
            progress.incorrect_count = (progress.incorrect_count or 0) + 1
            # After 3 failed attempts, reveal hint
            if attempt.attempts >= 3:
                attempt.revealed = 1

        progress.last_activity = _now_str()

        # Check if lesson completed
        items = _get_lesson_items(db, lesson_id)
        if progress.current_question_index >= len(items):
            progress.completed = 1

        db.commit()

        # Build feedback
        feedback = {
            "is_correct": is_correct,
            "your_answer": answer,
            "expected_answer": expected if not is_correct or attempt.attempts > 1 else None,
            "attempts": attempt.attempts,
            "hint_revealed": attempt.revealed == 1,
        }

        # Add hint if revealed
        if attempt.revealed == 1 and not is_correct:
            hint_text = item.grammar_explanation or item.example_sentence or ""
            feedback["hint"] = hint_text

        return success(
            data={
                "feedback": feedback,
                "progress": _progress_to_dict(progress),
            },
            message="Answer submitted",
        )
    except Exception as e:
        logger.error(f"Error submitting answer: {e}")
        return error(message=f"Failed to submit answer: {str(e)}")


# ---------------------------------------------------------------------------
# 6. POST /lesson/submit-voice-answer  (form-data + file)
# ---------------------------------------------------------------------------

@router.post("/submit-voice-answer")
def submit_voice_answer(
    user_id: str = Form(...),
    lesson_id: str = Form(...),
    item_id: str = Form(...),
    audio_file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Accept audio file, transcribe via audio_service, check against expected answer, store audio answer."""
    try:
        item_id_int = int(item_id)
    except ValueError:
        return error(message="Invalid item_id")

    try:
        progress = _get_or_create_progress(user_id, lesson_id, db)
        if not progress:
            return error(message="Lesson not started. Call /lesson/start first.")

        # Get the lesson item
        item = db.query(LessonItem).filter(LessonItem.id == item_id_int).first()
        if not item:
            return error(message="Lesson item not found")

        # Read and save the audio file
        audio_content = audio_file.file.read()

        # Save the recorded audio
        ext = os.path.splitext(audio_file.filename or ".wav")[1]
        audio_filename = f"{user_id}_{lesson_id}_{item_id_int}_{uuid.uuid4().hex[:8]}{ext}"
        saved_path = audio_service.save_audio_file(
            audio_content,
            audio_filename,
            subdir="voice_answers",
        )

        if not saved_path:
            return error(message="Failed to save audio file")

        # Transcribe the audio
        transcription = audio_service.transcribe_audio(audio_content)
        if not transcription:
            return error(message="Failed to transcribe audio")

        # Determine expected answer
        expected = (
            item.conversation_affirmative
            or item.vocabulary_word
            or item.meaning
            or item.exercise_answers
            or ""
        )

        # Check answer
        is_correct = _check_answer(transcription, expected)

        # Track attempt
        attempt = (
            db.query(QuestionAttempt)
            .filter(
                QuestionAttempt.user_id == user_id,
                QuestionAttempt.lesson_id == lesson_id,
                QuestionAttempt.item_id == item_id_int,
            )
            .first()
        )

        if attempt:
            attempt.attempts = (attempt.attempts or 0) + 1
            attempt.last_attempt_at = _now_str()
        else:
            attempt = QuestionAttempt(
                user_id=user_id,
                lesson_id=lesson_id,
                item_id=item_id_int,
                attempts=1,
                revealed=0,
                last_attempt_at=_now_str(),
            )
            db.add(attempt)

        # Store answer
        answer_record = LessonAnswer(
            user_id=user_id,
            lesson_id=lesson_id,
            item_id=item_id_int,
            user_answer=transcription,
            expected_answer=expected,
            is_correct=1 if is_correct else 0,
            attempt_number=attempt.attempts,
            answered_at=_now_str(),
        )
        db.add(answer_record)

        # Update progress
        if is_correct:
            progress.correct_count = (progress.correct_count or 0) + 1
            progress.current_question_index = (progress.current_question_index or 0) + 1
        else:
            progress.incorrect_count = (progress.incorrect_count or 0) + 1
            if attempt.attempts >= 3:
                attempt.revealed = 1

        progress.last_activity = _now_str()

        # Check completion
        items = _get_lesson_items(db, lesson_id)
        if progress.current_question_index >= len(items):
            progress.completed = 1

        db.commit()

        audio_url = f"/uploads/voice_answers/{audio_filename}"

        feedback = {
            "is_correct": is_correct,
            "transcription": transcription,
            "expected_answer": expected if not is_correct else None,
            "attempts": attempt.attempts,
            "audio_url": audio_url,
        }

        if attempt.revealed == 1 and not is_correct:
            feedback["hint"] = item.grammar_explanation or item.example_sentence or ""

        return success(
            data={
                "feedback": feedback,
                "progress": _progress_to_dict(progress),
            },
            message="Voice answer submitted",
        )
    except Exception as e:
        logger.error(f"Error submitting voice answer: {e}")
        return error(message=f"Failed to submit voice answer: {str(e)}")


# ---------------------------------------------------------------------------
# 7. POST /lesson/reset  (form-data: user_id, lesson_id)
# ---------------------------------------------------------------------------

@router.post("/reset")
def reset_lesson(
    user_id: str = Form(...),
    lesson_id: str = Form(...),
    db: Session = Depends(get_db),
):
    """Reset lesson progress and attempts."""
    try:
        progress = _get_or_create_progress(user_id, lesson_id, db)
        if not progress:
            return error(message="No lesson progress found to reset")

        # Reset progress
        progress.current_question_index = 0
        progress.correct_count = 0
        progress.incorrect_count = 0
        progress.completed = 0
        progress.started_at = _now_str()
        progress.last_activity = _now_str()

        # Delete attempts for this lesson
        db.query(QuestionAttempt).filter(
            QuestionAttempt.user_id == user_id,
            QuestionAttempt.lesson_id == lesson_id,
        ).delete()

        # Delete answers for this lesson
        db.query(LessonAnswer).filter(
            LessonAnswer.user_id == user_id,
            LessonAnswer.lesson_id == lesson_id,
        ).delete()

        db.commit()
        db.refresh(progress)

        return success(
            data=_progress_to_dict(progress),
            message="Lesson progress reset",
        )
    except Exception as e:
        logger.error(f"Error resetting lesson: {e}")
        return error(message=f"Failed to reset lesson: {str(e)}")


# ---------------------------------------------------------------------------
# 8. GET /lesson/progress/{user_id}
# ---------------------------------------------------------------------------

@router.get("/progress/{user_id}")
def get_lesson_progress(user_id: str, db: Session = Depends(get_db)):
    """Return dynamic lesson progress for user."""
    try:
        progress_rows = (
            db.query(LessonProgress)
            .filter(LessonProgress.user_id == user_id)
            .all()
        )

        if not progress_rows:
            return success(
                data={"user_id": user_id, "lessons": [], "total": 0},
                message="No lesson progress found",
            )

        lessons = [_progress_to_dict(p) for p in progress_rows]

        return success(
            data={"user_id": user_id, "lessons": lessons, "total": len(lessons)},
            message="Lesson progress retrieved",
        )
    except Exception as e:
        logger.error(f"Error getting lesson progress: {e}")
        return error(message=f"Failed to get lesson progress: {str(e)}")


# ---------------------------------------------------------------------------
# 9. GET /lesson/audio-stats/{user_id}
# ---------------------------------------------------------------------------

@router.get("/audio-stats/{user_id}")
def get_audio_stats(user_id: str, db: Session = Depends(get_db)):
    """Return generated/recorded audio statistics."""
    try:
        upload_dir = os.path.join(os.getcwd(), settings.upload_dir)
        tts_dir = os.path.join(upload_dir, "lesson_tts")
        voice_dir = os.path.join(upload_dir, "voice_answers")

        tts_count = 0
        voice_count = 0

        if os.path.isdir(tts_dir):
            tts_count = len([
                f for f in os.listdir(tts_dir)
                if f.startswith(f"{user_id}_")
            ])

        if os.path.isdir(voice_dir):
            voice_count = len([
                f for f in os.listdir(voice_dir)
                if f.startswith(f"{user_id}_")
            ])

        return success(
            data={
                "user_id": user_id,
                "tts_audio_generated": tts_count,
                "voice_answers_recorded": voice_count,
                "total_audio_files": tts_count + voice_count,
            },
            message="Audio stats retrieved",
        )
    except Exception as e:
        logger.error(f"Error getting audio stats: {e}")
        return error(message=f"Failed to get audio stats: {str(e)}")


# ---------------------------------------------------------------------------
# 10. POST /lesson/fix-progress/{user_id}
# ---------------------------------------------------------------------------

@router.post("/fix-progress/{user_id}")
def fix_progress(user_id: str, db: Session = Depends(get_db)):
    """Recompute progress counters."""
    try:
        progress_rows = (
            db.query(LessonProgress)
            .filter(LessonProgress.user_id == user_id)
            .all()
        )

        if not progress_rows:
            return success(
                data={"user_id": user_id, "fixed": 0},
                message="No progress rows to fix",
            )

        fixed_count = 0
        for progress in progress_rows:
            # Recompute correct/incorrect counts from answers
            answers = (
                db.query(LessonAnswer)
                .filter(
                    LessonAnswer.user_id == user_id,
                    LessonAnswer.lesson_id == progress.lesson_id,
                )
                .all()
            )

            # Get unique answered items (latest attempt per item)
            latest_answers = {}
            for a in answers:
                key = a.item_id
                if key not in latest_answers or a.attempt_number > latest_answers[key].attempt_number:
                    latest_answers[key] = a

            correct = sum(1 for a in latest_answers.values() if a.is_correct == 1)
            incorrect = sum(1 for a in latest_answers.values() if a.is_correct == 0)

            old_correct = progress.correct_count
            old_incorrect = progress.incorrect_count

            progress.correct_count = correct
            progress.incorrect_count = incorrect
            progress.current_question_index = correct
            progress.last_activity = _now_str()

            # Recompute total questions
            items = _get_lesson_items(db, progress.lesson_id)
            if items:
                progress.total_questions = len(items)
                if correct >= len(items):
                    progress.completed = 1

            if old_correct != correct or old_incorrect != incorrect:
                fixed_count += 1

        db.commit()

        return success(
            data={"user_id": user_id, "fixed": fixed_count, "total_rows": len(progress_rows)},
            message=f"Progress fixed: {fixed_count} rows updated",
        )
    except Exception as e:
        logger.error(f"Error fixing progress: {e}")
        return error(message=f"Failed to fix progress: {str(e)}")


# ---------------------------------------------------------------------------
# 11. GET /lesson/debug/progress/{user_id}/{lesson_id}
# ---------------------------------------------------------------------------

@router.get("/debug/progress/{user_id}/{lesson_id}")
def debug_progress(
    user_id: str,
    lesson_id: str,
    db: Session = Depends(get_db),
):
    """Debug progress row for a specific lesson."""
    try:
        progress = _get_or_create_progress(user_id, lesson_id, db)

        # Get attempts
        attempts = (
            db.query(QuestionAttempt)
            .filter(
                QuestionAttempt.user_id == user_id,
                QuestionAttempt.lesson_id == lesson_id,
            )
            .all()
        )

        # Get answers
        answers = (
            db.query(LessonAnswer)
            .filter(
                LessonAnswer.user_id == user_id,
                LessonAnswer.lesson_id == lesson_id,
            )
            .order_by(LessonAnswer.id)
            .all()
        )

        # Get lesson items count
        items = _get_lesson_items(db, lesson_id)

        return success(
            data={
                "user_id": user_id,
                "lesson_id": lesson_id,
                "progress": _progress_to_dict(progress) if progress else None,
                "attempts": [_attempt_to_dict(a) for a in attempts],
                "answers": [_answer_to_dict(a) for a in answers],
                "total_items_in_lesson": len(items),
            },
            message="Debug progress data",
        )
    except Exception as e:
        logger.error(f"Error in debug progress: {e}")
        return error(message=f"Failed to get debug progress: {str(e)}")


# ---------------------------------------------------------------------------
# 12. GET /lesson/health
# ---------------------------------------------------------------------------

@router.get("/health")
def lesson_health(db: Session = Depends(get_db)):
    """Return lesson API health, table counts, loaded lesson count."""
    try:
        item_count = db.query(LessonItem).count()
        progress_count = db.query(LessonProgress).count()
        answer_count = db.query(LessonAnswer).count()
        attempt_count = db.query(QuestionAttempt).count()

        distinct_lessons = db.query(LessonItem.lesson).distinct().count()

        return success(
            data={
                "tables": {
                    "lesson_items": item_count,
                    "lesson_progress": progress_count,
                    "lesson_answers": answer_count,
                    "question_attempts": attempt_count,
                },
                "loaded_lesson_count": distinct_lessons,
                "audio_service_available": audio_service.is_tts_available,
                "stt_available": audio_service.is_stt_available,
                "status": "healthy",
            },
            message="Lesson service health check",
        )
    except Exception as e:
        logger.error(f"Error in lesson health check: {e}")
        return error(message=f"Health check failed: {str(e)}")
