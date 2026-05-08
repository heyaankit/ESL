import io
import wave
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
from app.database import get_db
from app.models.lesson import LessonItem
from app.models.user import User
from app.auth import get_current_user
from app.services.tts import generate_speech
from app.utils.response import success, error

router = APIRouter()


@router.get("/random")
def get_random_words(
    lesson: Optional[str] = Query(None),
    sub_topic: Optional[str] = Query(None),
    count: int = Query(1, ge=1, le=20),
    exclude_ids: Optional[str] = Query(None),
    db: Session = Depends(get_db)
) -> dict:
    """Get random words with optional filters."""
    query = db.query(LessonItem)

    if lesson:
        query = query.filter(LessonItem.lesson.like(f"{lesson}%"))

    if sub_topic:
        query = query.filter(LessonItem.sub_topic == sub_topic)

    if exclude_ids:
        exclude_list = [int(x) for x in exclude_ids.split(",") if x.isdigit()]
        if exclude_list:
            query = query.filter(~LessonItem.id.in_(exclude_list))

    total = query.count()
    if total == 0:
        return success(data={"words": []}, message="No words found")

    sample_count = min(count, total)
    words = query.order_by(func.random()).limit(sample_count).all()

    return success(data={
        "words": [
            {
                "id": w.id,
                "lesson": w.lesson,
                "vocabulary_word": w.vocabulary_word,
                "conversation_affirmative": w.conversation_affirmative,
            }
            for w in words
        ]
    }, message=f"{len(words)} random words retrieved")


@router.get("/{word_id}")
def get_word(word_id: int, db: Session = Depends(get_db)) -> dict:
    """Get full detail for a single word/item."""
    item = db.query(LessonItem).filter(LessonItem.id == word_id).first()

    if not item:
        return error(message=f"Word {word_id} not found")

    return success(data={
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
    }, message="Word details retrieved")


@router.get("/{word_id}/speak")
def speak_word(
    word_id: int,
    speed: float = 1.0,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate TTS audio (WAV) for the word's conversation_question."""
    item = db.query(LessonItem).filter(LessonItem.id == word_id).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"Word {word_id} not found")

    question = item.conversation_question
    if not question:
        raise HTTPException(status_code=400, detail="No question available for this word")

    # Intentional: opposite-gender voice for learning contrast
    voice = "af_bella" if user.gender == "male" else "am_onyx"

    text = question.replace("/", " or ").strip()
    pcm_data, sample_rate = generate_speech(text, voice=voice, speed=speed)

    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_data)

    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="audio/wav",
        headers={"Content-Disposition": f"attachment; filename=word_{word_id}.wav"}
    )
