"""Bestie Chat API — Bestie Live API Handoff Document.

Conversational AI chat with corrections, dialog practice, and level assessment.
All endpoints return the legacy format:
    {"status": "1", "data": ..., "message": ...}   — success
    {"status": "0", "data": null, "message": ...}   — failure
"""
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Form
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.chat import (
    ChatHistory,
    SentenceCorrection,
    UserLearningState,
    UserRelationship,
    Dialog,
    UserDialogProgress,
    UserLevelAssessment,
)
from app.services.ai_service import ai_service
from app.utils.response import success, error
from app.logger import logger

router = APIRouter(tags=["chat"])


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HARDCODED_THEMES = [
    "greetings",
    "shopping",
    "restaurant",
    "travel",
    "doctor",
    "school",
    "work",
    "hobbies",
    "weather",
    "family",
]

PROMPT_MODES = [
    {"prompt_number": 1, "mode": "chat", "description": "Free conversation with Bestie"},
    {"prompt_number": 2, "mode": "dialog", "description": "Guided dialog practice"},
    {"prompt_number": 3, "mode": "practice", "description": "Grammar and vocabulary practice"},
    {"prompt_number": 4, "mode": "correction", "description": "Sentence correction mode"},
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _chat_to_dict(row: ChatHistory) -> dict:
    return {
        "id": row.id,
        "user_id": row.user_id,
        "role": row.role,
        "message": row.message,
        "mode": row.mode,
        "theme": row.theme,
        "dialog_id": row.dialog_id,
        "is_correction": row.is_correction,
        "corrected_text": row.corrected_text,
        "created_at": str(row.created_at) if row.created_at else None,
    }


def _correction_to_dict(row: SentenceCorrection) -> dict:
    return {
        "id": row.id,
        "user_id": row.user_id,
        "original": row.original,
        "corrected": row.corrected,
        "explanation": row.explanation,
        "chat_message_id": row.chat_message_id,
        "created_at": str(row.created_at) if row.created_at else None,
    }


def _learning_state_to_dict(row: UserLearningState) -> dict:
    return {
        "id": row.id,
        "user_id": row.user_id,
        "level": row.level,
        "stage": row.stage,
        "theme": row.theme,
        "known_words": row.known_words,
        "words_to_review": row.words_to_review,
        "last_lesson_topic": row.last_lesson_topic,
        "updated_at": str(row.updated_at) if row.updated_at else None,
    }


def _relationship_to_dict(row: UserRelationship) -> dict:
    return {
        "id": row.id,
        "user_id": row.user_id,
        "stage": row.stage,
        "rapport_score": row.rapport_score,
        "interaction_count": row.interaction_count,
        "last_interaction": str(row.last_interaction) if row.last_interaction else None,
        "updated_at": str(row.updated_at) if row.updated_at else None,
    }


def _dialog_progress_to_dict(row: UserDialogProgress) -> dict:
    return {
        "id": row.id,
        "user_id": row.user_id,
        "theme": row.theme,
        "current_line": row.current_line,
        "completed": row.completed,
        "started_at": str(row.started_at) if row.started_at else None,
        "updated_at": str(row.updated_at) if row.updated_at else None,
    }


def _assessment_to_dict(row: UserLevelAssessment) -> dict:
    return {
        "id": row.id,
        "user_id": row.user_id,
        "assessment_score": row.assessment_score,
        "vocabulary_score": row.vocabulary_score,
        "grammar_score": row.grammar_score,
        "fluency_score": row.fluency_score,
        "level_assigned": row.level_assigned,
        "notes": row.notes,
        "created_at": str(row.created_at) if row.created_at else None,
    }


def _get_or_create_learning_state(user_id: str, db: Session) -> UserLearningState:
    """Get or create a UserLearningState row."""
    state = (
        db.query(UserLearningState)
        .filter(UserLearningState.user_id == user_id)
        .first()
    )
    if not state:
        state = UserLearningState(user_id=user_id)
        db.add(state)
        db.commit()
        db.refresh(state)
    return state


def _get_or_create_relationship(user_id: str, db: Session) -> UserRelationship:
    """Get or create a UserRelationship row."""
    rel = (
        db.query(UserRelationship)
        .filter(UserRelationship.user_id == user_id)
        .first()
    )
    if not rel:
        rel = UserRelationship(user_id=user_id)
        db.add(rel)
        db.commit()
        db.refresh(rel)
    return rel


def _update_relationship_stage(rel: UserRelationship) -> None:
    """Update relationship stage based on interaction count and rapport."""
    count = rel.interaction_count or 0
    rapport = rel.rapport_score or 0.0

    if count >= 50 and rapport >= 80:
        rel.stage = "bestie"
    elif count >= 20 and rapport >= 50:
        rel.stage = "friend"
    elif count >= 5 and rapport >= 20:
        rel.stage = "acquaintance"
    else:
        rel.stage = "stranger"


def _build_chat_system_prompt(user_id: str, theme: Optional[str], mode: str, db: Session) -> str:
    """Build the system prompt for the AI chat, incorporating level and context."""
    state = (
        db.query(UserLearningState)
        .filter(UserLearningState.user_id == user_id)
        .first()
    )
    level = state.level if state else "beginner"
    rel = (
        db.query(UserRelationship)
        .filter(UserRelationship.user_id == user_id)
        .first()
    )
    stage = rel.stage if rel else "stranger"

    prompt = (
        f"You are Bestie, a friendly and supportive English learning assistant for Mongolian speakers. "
        f"The user's current level is {level}. "
        f"Your relationship stage with the user is: {stage}. "
    )

    if theme:
        prompt += f"The conversation theme is: {theme}. "

    if mode == "dialog":
        prompt += "You are in dialog practice mode. Guide the user through a realistic conversation scenario. "
    elif mode == "practice":
        prompt += "You are in practice mode. Help the user practice grammar and vocabulary with exercises. "
    elif mode == "correction":
        prompt += (
            "You are in correction mode. If the user makes grammar or vocabulary mistakes, "
            "gently correct them and explain why. Always show the corrected version clearly. "
        )
    else:
        prompt += (
            "Chat naturally. If the user makes significant errors, gently provide corrections. "
            "Use simple English appropriate for the user's level. "
        )

    return prompt


# ---------------------------------------------------------------------------
# 1. GET /chat/themes
# ---------------------------------------------------------------------------

@router.get("/chat/themes")
def list_themes(db: Session = Depends(get_db)):
    """List available conversation themes (from Dialog table distinct themes, or hardcoded list)."""
    try:
        db_themes = db.query(Dialog.theme).distinct().all()
        theme_list = [t.theme for t in db_themes if t.theme]

        # Merge with hardcoded themes (deduplicate)
        all_themes = list(dict.fromkeys(theme_list + HARDCODED_THEMES))

        return success(
            data={"themes": all_themes, "count": len(all_themes)},
            message="Themes retrieved",
        )
    except Exception as e:
        logger.error(f"Error listing themes: {e}")
        return error(message=f"Failed to list themes: {str(e)}")


# ---------------------------------------------------------------------------
# 2. GET /chat/dialogs/{theme}
# ---------------------------------------------------------------------------

@router.get("/chat/dialogs/{theme}")
def get_dialogs(theme: str, db: Session = Depends(get_db)):
    """Return authored dialog lines for a theme."""
    try:
        dialogs = (
            db.query(Dialog)
            .filter(Dialog.theme == theme)
            .order_by(Dialog.line_number)
            .all()
        )

        if not dialogs:
            return error(message=f"No dialogs found for theme: {theme}")

        lines = [
            {
                "id": d.id,
                "theme": d.theme,
                "line_number": d.line_number,
                "role": d.role,
                "text": d.text,
                "hint": d.hint,
            }
            for d in dialogs
        ]

        return success(
            data={"theme": theme, "lines": lines, "total_lines": len(lines)},
            message="Dialog lines retrieved",
        )
    except Exception as e:
        logger.error(f"Error getting dialogs: {e}")
        return error(message=f"Failed to get dialogs: {str(e)}")


# ---------------------------------------------------------------------------
# 3. GET /chat/dialog-progress/{user_id}/{theme}
# ---------------------------------------------------------------------------

@router.get("/chat/dialog-progress/{user_id}/{theme}")
def get_dialog_progress(user_id: str, theme: str, db: Session = Depends(get_db)):
    """Return user dialog progress row."""
    try:
        progress = (
            db.query(UserDialogProgress)
            .filter(
                UserDialogProgress.user_id == user_id,
                UserDialogProgress.theme == theme,
            )
            .first()
        )

        if not progress:
            return success(
                data={
                    "user_id": user_id,
                    "theme": theme,
                    "current_line": 0,
                    "completed": 0,
                    "status": "not_started",
                },
                message="No dialog progress found; not started yet",
            )

        return success(
            data=_dialog_progress_to_dict(progress),
            message="Dialog progress retrieved",
        )
    except Exception as e:
        logger.error(f"Error getting dialog progress: {e}")
        return error(message=f"Failed to get dialog progress: {str(e)}")


# ---------------------------------------------------------------------------
# 4. POST /chat/start-dialog  (form-data: user_id, theme)
# ---------------------------------------------------------------------------

@router.post("/chat/start-dialog")
def start_dialog(
    user_id: str = Form(...),
    theme: str = Form(...),
    db: Session = Depends(get_db),
):
    """Start dialog practice, initialize user_dialog_progress."""
    try:
        # Check if dialog exists for the theme
        dialog_count = db.query(Dialog).filter(Dialog.theme == theme).count()
        if dialog_count == 0:
            return error(message=f"No dialog script found for theme: {theme}")

        # Check if progress already exists
        existing = (
            db.query(UserDialogProgress)
            .filter(
                UserDialogProgress.user_id == user_id,
                UserDialogProgress.theme == theme,
            )
            .first()
        )

        if existing:
            # Reset progress
            existing.current_line = 0
            existing.completed = 0
            existing.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return success(
                data=_dialog_progress_to_dict(existing),
                message="Dialog progress reset",
            )

        # Create new progress entry
        progress = UserDialogProgress(
            user_id=user_id,
            theme=theme,
            current_line=0,
            completed=0,
        )
        db.add(progress)
        db.commit()
        db.refresh(progress)

        # Get the first dialog line (assistant's opening)
        first_line = (
            db.query(Dialog)
            .filter(Dialog.theme == theme)
            .order_by(Dialog.line_number)
            .first()
        )

        opening_text = None
        if first_line and first_line.role == "assistant":
            opening_text = first_line.text
            progress.current_line = first_line.line_number
            db.commit()

        return success(
            data={
                "progress": _dialog_progress_to_dict(progress),
                "opening_line": opening_text,
            },
            message="Dialog practice started",
        )
    except Exception as e:
        logger.error(f"Error starting dialog: {e}")
        return error(message=f"Failed to start dialog: {str(e)}")


# ---------------------------------------------------------------------------
# 5. POST /chat/send-message  (form-data)
# ---------------------------------------------------------------------------

@router.post("/chat/send-message")
def send_message(
    user_id: str = Form(...),
    message: str = Form(...),
    theme: str = Form(None),
    mode: str = Form("chat"),
    db: Session = Depends(get_db),
):
    """Main Bestie chat endpoint.

    - Send message to AI with level/theme context
    - Store chat, corrections, learning state, progress
    - Update user_relationship interaction count
    - Return AI response with corrections
    """
    try:
        now = datetime.utcnow()

        # --- Store user message ---
        user_chat = ChatHistory(
            user_id=user_id,
            role="user",
            message=message,
            mode=mode,
            theme=theme,
        )
        db.add(user_chat)
        db.commit()
        db.refresh(user_chat)

        # --- Build AI prompt ---
        system_prompt = _build_chat_system_prompt(user_id, theme, mode, db)

        # Get recent chat context (last 10 messages)
        recent = (
            db.query(ChatHistory)
            .filter(ChatHistory.user_id == user_id)
            .order_by(ChatHistory.id.desc())
            .limit(10)
            .all()
        )
        recent.reverse()

        messages = [{"role": "system", "content": system_prompt}]
        for msg in recent:
            role = msg.role if msg.role in ("user", "assistant") else "user"
            messages.append({"role": role, "content": msg.message or ""})

        # Add current message
        messages.append({"role": "user", "content": message})

        # --- Call AI service ---
        ai_response_text = ai_service.chat_completion(
            messages=messages,
            temperature=0.7,
            max_tokens=500,
        )

        # --- Detect corrections ---
        correction = None
        corrected_text = None
        is_correction = 0

        # Simple heuristic: if AI response contains correction markers
        # Try to extract structured correction from AI response
        if mode in ("correction", "practice", "chat"):
            correction_data = _try_extract_correction(message, ai_response_text)
            if correction_data:
                correction = correction_data
                corrected_text = correction_data.get("corrected", "")
                is_correction = 1

                # Store in sentence_corrections
                sc = SentenceCorrection(
                    user_id=user_id,
                    original=message,
                    corrected=correction_data.get("corrected", ""),
                    explanation=correction_data.get("explanation", ""),
                    chat_message_id=user_chat.id,
                )
                db.add(sc)

        # --- Store assistant message ---
        assistant_chat = ChatHistory(
            user_id=user_id,
            role="assistant",
            message=ai_response_text,
            mode=mode,
            theme=theme,
            is_correction=is_correction,
            corrected_text=corrected_text,
        )
        db.add(assistant_chat)

        # --- Update learning state ---
        state = _get_or_create_learning_state(user_id, db)
        if theme:
            state.theme = theme
        state.updated_at = now

        # --- Update relationship ---
        rel = _get_or_create_relationship(user_id, db)
        rel.interaction_count = (rel.interaction_count or 0) + 1
        rel.rapport_score = min(100.0, (rel.rapport_score or 0.0) + 0.5)
        rel.last_interaction = now
        _update_relationship_stage(rel)
        rel.updated_at = now

        # --- Update dialog progress if in dialog mode ---
        if mode == "dialog" and theme:
            progress = (
                db.query(UserDialogProgress)
                .filter(
                    UserDialogProgress.user_id == user_id,
                    UserDialogProgress.theme == theme,
                )
                .first()
            )
            if progress:
                progress.current_line = (progress.current_line or 0) + 1
                # Check if dialog is completed
                total_lines = db.query(Dialog).filter(Dialog.theme == theme).count()
                if progress.current_line >= total_lines:
                    progress.completed = 1
                progress.updated_at = now

        db.commit()
        db.refresh(assistant_chat)

        # --- Build response ---
        result = {
            "message": _chat_to_dict(assistant_chat),
            "correction": correction,
            "relationship": _relationship_to_dict(rel),
        }

        return success(data=result, message="Message sent")

    except Exception as e:
        logger.error(f"Error in send-message: {e}")
        return error(message=f"Failed to process message: {str(e)}")


def _try_extract_correction(user_message: str, ai_response: str) -> Optional[dict]:
    """Try to extract a correction from the AI response using heuristics.

    Looks for common correction patterns like:
    - "Correct: ..." or "Correction: ..."
    - "You should say: ..."
    - "The correct way is: ..."
    """
    lower_response = ai_response.lower()

    # Check if AI seems to be correcting
    correction_markers = [
        "correct:", "correction:", "you should say:",
        "the correct way", "instead of", "it should be",
        "better way to say", "more natural:",
    ]

    is_correcting = any(marker in lower_response for marker in correction_markers)

    if not is_correcting:
        return None

    # Try to extract the corrected text
    corrected = None
    explanation = None

    for marker in ["Correct:", "Correction:", "You should say:", "It should be:", "More natural:"]:
        if marker.lower() in lower_response:
            idx = lower_response.index(marker.lower())
            # Get text after the marker until the next sentence
            after_marker = ai_response[idx + len(marker):].strip()
            # Take until period or newline
            end_chars = [".", "\n", "!"]
            end_idx = len(after_marker)
            for ec in end_chars:
                ei = after_marker.find(ec)
                if ei != -1 and ei < end_idx:
                    end_idx = ei
            corrected = after_marker[:end_idx].strip().strip('"').strip("'")
            break

    if corrected:
        explanation = ai_response
    else:
        # Fallback: just mark the whole response as the explanation
        corrected = user_message  # No specific correction found
        explanation = ai_response

    return {
        "original": user_message,
        "corrected": corrected,
        "explanation": explanation,
    }


# ---------------------------------------------------------------------------
# 6. GET /chat/history/{user_id}
# ---------------------------------------------------------------------------

@router.get("/chat/history/{user_id}")
def get_chat_history(user_id: str, db: Session = Depends(get_db)):
    """Return recent chat history (limit 50)."""
    try:
        history = (
            db.query(ChatHistory)
            .filter(ChatHistory.user_id == user_id)
            .order_by(ChatHistory.id.desc())
            .limit(50)
            .all()
        )
        history.reverse()

        messages = [_chat_to_dict(h) for h in history]

        return success(
            data={"messages": messages, "count": len(messages)},
            message="Chat history retrieved",
        )
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        return error(message=f"Failed to get chat history: {str(e)}")


# ---------------------------------------------------------------------------
# 7. GET /chat/prompts
# ---------------------------------------------------------------------------

@router.get("/chat/prompts")
def list_prompts():
    """List available prompt numbers/modes."""
    return success(
        data={"prompts": PROMPT_MODES},
        message="Available prompts retrieved",
    )


# ---------------------------------------------------------------------------
# 8. GET /chat/progress/{user_id}
# ---------------------------------------------------------------------------

@router.get("/chat/progress/{user_id}")
def get_chat_progress(user_id: str, db: Session = Depends(get_db)):
    """Return chat-specific progress (message count, level, relationship stage)."""
    try:
        # Message count
        message_count = (
            db.query(ChatHistory)
            .filter(ChatHistory.user_id == user_id)
            .count()
        )

        # Learning state
        state = (
            db.query(UserLearningState)
            .filter(UserLearningState.user_id == user_id)
            .first()
        )

        # Relationship
        rel = (
            db.query(UserRelationship)
            .filter(UserRelationship.user_id == user_id)
            .first()
        )

        # Correction count
        correction_count = (
            db.query(SentenceCorrection)
            .filter(SentenceCorrection.user_id == user_id)
            .count()
        )

        progress = {
            "user_id": user_id,
            "message_count": message_count,
            "correction_count": correction_count,
            "level": state.level if state else "beginner",
            "stage": state.stage if state else 1,
            "relationship_stage": rel.stage if rel else "stranger",
            "rapport_score": rel.rapport_score if rel else 0.0,
            "interaction_count": rel.interaction_count if rel else 0,
        }

        return success(data=progress, message="Chat progress retrieved")
    except Exception as e:
        logger.error(f"Error getting chat progress: {e}")
        return error(message=f"Failed to get chat progress: {str(e)}")


# ---------------------------------------------------------------------------
# 9. GET /chat/corrections/{user_id}
# ---------------------------------------------------------------------------

@router.get("/chat/corrections/{user_id}")
def get_corrections(user_id: str, db: Session = Depends(get_db)):
    """Return stored grammar/sentence corrections."""
    try:
        corrections = (
            db.query(SentenceCorrection)
            .filter(SentenceCorrection.user_id == user_id)
            .order_by(SentenceCorrection.id.desc())
            .limit(50)
            .all()
        )

        items = [_correction_to_dict(c) for c in corrections]

        return success(
            data={"corrections": items, "count": len(items)},
            message="Corrections retrieved",
        )
    except Exception as e:
        logger.error(f"Error getting corrections: {e}")
        return error(message=f"Failed to get corrections: {str(e)}")


# ---------------------------------------------------------------------------
# 10. GET /chat/assessment/{user_id}
# ---------------------------------------------------------------------------

@router.get("/chat/assessment/{user_id}")
def get_assessment(user_id: str, db: Session = Depends(get_db)):
    """Return latest level assessment."""
    try:
        assessment = (
            db.query(UserLevelAssessment)
            .filter(UserLevelAssessment.user_id == user_id)
            .order_by(UserLevelAssessment.id.desc())
            .first()
        )

        if not assessment:
            return success(
                data={
                    "user_id": user_id,
                    "assessment_score": 0.0,
                    "vocabulary_score": 0.0,
                    "grammar_score": 0.0,
                    "fluency_score": 0.0,
                    "level_assigned": "beginner",
                    "notes": None,
                    "status": "no_assessment",
                },
                message="No assessment found; default values returned",
            )

        return success(
            data=_assessment_to_dict(assessment),
            message="Assessment retrieved",
        )
    except Exception as e:
        logger.error(f"Error getting assessment: {e}")
        return error(message=f"Failed to get assessment: {str(e)}")


# ---------------------------------------------------------------------------
# 11. GET /chat/health
# ---------------------------------------------------------------------------

@router.get("/chat/health")
def chat_health(db: Session = Depends(get_db)):
    """Return chat table counts and status."""
    try:
        chat_count = db.query(ChatHistory).count()
        correction_count = db.query(SentenceCorrection).count()
        state_count = db.query(UserLearningState).count()
        rel_count = db.query(UserRelationship).count()
        dialog_count = db.query(Dialog).count()
        progress_count = db.query(UserDialogProgress).count()
        assessment_count = db.query(UserLevelAssessment).count()

        return success(
            data={
                "tables": {
                    "chat_history": chat_count,
                    "sentence_corrections": correction_count,
                    "user_learning_state": state_count,
                    "user_relationship": rel_count,
                    "dialogs": dialog_count,
                    "user_dialog_progress": progress_count,
                    "user_level_assessments": assessment_count,
                },
                "ai_service_available": ai_service.is_available,
                "status": "healthy",
            },
            message="Chat service health check",
        )
    except Exception as e:
        logger.error(f"Error in chat health check: {e}")
        return error(message=f"Health check failed: {str(e)}")
