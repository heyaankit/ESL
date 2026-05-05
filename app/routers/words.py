from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from app.database import get_db
from app.models.lesson import LessonItem

router = APIRouter()


@router.get("/random", response_model=dict)
def get_random_words(
    lesson: Optional[str] = Query(None),
    sub_topic: Optional[str] = Query(None),
    count: int = Query(1, ge=1, le=20),
    exclude_ids: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
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
        return {"words": []}

    import random
    all_ids = [r.id for r in query.all()]
    selected_ids = random.sample(all_ids, min(count, total))
    words = db.query(LessonItem).filter(LessonItem.id.in_(selected_ids)).all()

    return {
        "words": [
            {
                "id": w.id,
                "lesson": w.lesson,
                "vocabulary_word": w.vocabulary_word,
                "conversation_affirmative": w.conversation_affirmative,
            }
            for w in words
        ]
    }


@router.get("/{word_id}", response_model=dict)
def get_word(word_id: int, db: Session = Depends(get_db)):
    item = db.query(LessonItem).filter(LessonItem.id == word_id).first()

    if not item:
        raise HTTPException(status_code=404, detail=f"Word {word_id} not found")

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
    }