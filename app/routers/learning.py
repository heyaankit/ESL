"""Learning router — hardcoded learning content categories and content retrieval.

All endpoints return the legacy response format:
    {"status": "1", "data": ..., "message": ...}   — success
    {"status": "0", "data": null, "message": ...}   — failure
"""
from fastapi import APIRouter, Depends, Form
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.lesson import LessonItem
from app.models.content import Content
from app.utils.response import success, error
from app.logger import logger

router = APIRouter(tags=["learning"])


# ---------------------------------------------------------------------------
# Hardcoded category / training-type / word-type maps
# ---------------------------------------------------------------------------

CATEGORIES = [
    "Vocabulary",
    "Grammar",
    "Conversation",
    "Pronunciation",
    "Reading",
]

TRAINING_TYPES = {
    "Vocabulary": ["Flashcards", "Fill-in-the-blank", "Matching", "Spelling"],
    "Grammar": ["Multiple Choice", "Sentence Correction", "Fill-in-the-blank"],
    "Conversation": ["Dialog Practice", "Role Play", "Free Chat"],
    "Pronunciation": ["Listen & Repeat", "Minimal Pairs", "Tongue Twisters"],
    "Reading": ["Comprehension", "Cloze Test", "Vocabulary in Context"],
}

DEFAULT_WORD_TYPES = [
    "Nouns", "Verbs", "Adjectives", "Prepositions", "Adverbs", "Conjunctions"
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _lesson_item_to_dict(item: LessonItem) -> dict:
    """Serialise a LessonItem ORM object into a plain dict."""
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


def _content_to_dict(c: Content) -> dict:
    """Serialise a Content ORM object into a plain dict."""
    return {
        "id": c.id,
        "category": c.category,
        "training_type": c.training_type,
        "word_type": c.word_type,
        "key": c.key,
        "value": c.value,
        "language": c.language,
        "created_at": str(c.created_at) if c.created_at else None,
    }


# ---------------------------------------------------------------------------
# POST /learning/categories  — return high-level learning categories
# ---------------------------------------------------------------------------

@router.post("/learning/categories")
def get_categories(
    user_id: str = Form(..., description="User ID"),
):
    """Return hardcoded high-level learning categories."""
    return success(
        data=CATEGORIES,
        message="Categories fetched successfully",
    )


# ---------------------------------------------------------------------------
# POST /learning/training-types  — return training types for a category
# ---------------------------------------------------------------------------

@router.post("/learning/training-types")
def get_training_types(
    category: str = Form(..., description="Learning category"),
):
    """Return hardcoded training types for a given category."""
    types = TRAINING_TYPES.get(category)
    if types is None:
        return error(message=f"Unknown category: {category}. Valid categories: {', '.join(CATEGORIES)}")

    return success(
        data=types,
        message="Training types fetched successfully",
    )


# ---------------------------------------------------------------------------
# POST /learning/word-types  — return word types for a training type
# ---------------------------------------------------------------------------

@router.post("/learning/word-types")
def get_word_types(
    category: str = Form(..., description="Learning category"),
    training_type: str = Form(..., description="Training type"),
):
    """Return hardcoded word types for a training type (currently same defaults for all)."""
    # Validate category
    if category not in TRAINING_TYPES:
        return error(message=f"Unknown category: {category}. Valid categories: {', '.join(CATEGORIES)}")

    # Validate training_type belongs to the category
    valid_types = TRAINING_TYPES[category]
    if training_type not in valid_types:
        return error(
            message=f"Unknown training type '{training_type}' for category '{category}'. "
                    f"Valid types: {', '.join(valid_types)}"
        )

    return success(
        data=DEFAULT_WORD_TYPES,
        message="Word types fetched successfully",
    )


# ---------------------------------------------------------------------------
# POST /learning/content  — return content rows from Content table or lesson_items
# ---------------------------------------------------------------------------

@router.post("/learning/content")
def get_learning_content(
    category: str = Form(..., description="Learning category"),
    training_type: str = Form(..., description="Training type"),
    word_type: str = Form(..., description="Word type"),
    user_id: str = Form(..., description="User ID"),
    db: Session = Depends(get_db),
):
    """Return existing/generated content rows from the Content table or from
    lesson_items filtered by grammar_topic."""
    # First, try to find content from the Content table
    content_query = db.query(Content).filter(
        Content.category == category,
        Content.training_type == training_type,
    )
    if word_type:
        content_query = content_query.filter(Content.word_type == word_type)

    content_rows = content_query.all()

    if content_rows:
        return success(
            data=[_content_to_dict(c) for c in content_rows],
            message="Content fetched from content table",
        )

    # Fallback: try to find content from lesson_items filtered by grammar_topic
    # Map category names to possible grammar_topic values in lesson_items
    grammar_topic_filter = None
    if category == "Grammar":
        grammar_topic_filter = training_type  # e.g. "Multiple Choice"
    elif category == "Vocabulary":
        grammar_topic_filter = word_type  # e.g. "Nouns"

    lesson_query = db.query(LessonItem)
    if grammar_topic_filter:
        lesson_query = lesson_query.filter(
            LessonItem.grammar_topic.ilike(f"%{grammar_topic_filter}%")
        )

    lesson_items = lesson_query.limit(50).all()

    if lesson_items:
        return success(
            data=[_lesson_item_to_dict(item) for item in lesson_items],
            message="Content fetched from lesson items",
        )

    # No content found anywhere
    return success(
        data=[],
        message="No content found for the given category, training type, and word type",
    )
