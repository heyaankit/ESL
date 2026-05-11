from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError
import os

from app.database import engine, Base
from app.logger import logger
from app.config import settings

# ─── Import all models so Base.metadata.create_all() creates all tables ───
from app.models.user import User, OTPStore, UserProgress, UserPreferences
from app.models.lesson import (
    LessonItem, LessonProgress, LessonAnswer,
    QuestionAttempt, LessonAppProgress, LessonAppAnswer,
)
from app.models.quiz import UserQuizData, QuizHistory
from app.models.chat import (
    ChatHistory, SentenceCorrection, UserLearningState,
    UserRelationship, Dialog, UserDialogProgress, UserLevelAssessment,
)
from app.models.audio import AudioFile, AudioAnswer
from app.models.notification import UserNotification
from app.models.content import PrivacyPolicy, FAQ, ContactUs, UserSubscription, Content

# ─── Import data seeding ───
from app.services.excel_importer import import_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: create tables, seed data, ensure dirs exist."""
    logger.info("Starting Bestie ESL application")

    # Ensure uploads directory exists
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(os.path.join(settings.upload_dir, "profiles"), exist_ok=True)
    os.makedirs(os.path.join(settings.upload_dir, "tts"), exist_ok=True)
    os.makedirs(os.path.join(settings.upload_dir, "voice_answers"), exist_ok=True)

    # Create all database tables
    Base.metadata.create_all(bind=engine)

    # Seed Excel lesson data if DB is empty
    import_data()

    yield

    logger.info("Shutting down Bestie ESL application")


app = FastAPI(
    title="Bestie ESL API",
    description="English Learning for Mongolian Speakers — Live API",
    version="2.0.0",
    lifespan=lifespan,
)

# ─── CORS middleware ───
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.is_development else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Exception handlers ───
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation error on {request.url}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"status": "0", "data": None, "message": "Validation error", "errors": exc.errors()},
    )


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error(f"Database error on {request.url}: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"status": "0", "data": None, "message": "Database error occurred"},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.url}: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"status": "0", "data": None, "message": "Internal server error"},
    )


# ─── Mount static files for uploads ───
if os.path.exists(settings.upload_dir):
    app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")


# ─── Register routers ───
from app.routers import auth, words, grammar, exercises, progress, tts

# Phase 1: Health (replaces root /health)
from app.routers.health import router as health_router

# Phase 2: Auth (expanded)
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])

# Phase 3: Onboarding + Lessons + Dynamic Lessons
from app.routers.onboarding import router as onboarding_router
from app.routers.lesson import router as lesson_router
from app.routers.learning import router as learning_router

app.include_router(onboarding_router, prefix="/api/v1", tags=["onboarding"])
app.include_router(lesson_router, prefix="/api/v1/lesson", tags=["lesson"])
app.include_router(learning_router, prefix="/api/v1", tags=["learning"])
app.include_router(words.router, prefix="/api/v1/words", tags=["words"])
app.include_router(grammar.router, prefix="/api/v1/grammar", tags=["grammar"])
app.include_router(exercises.router, prefix="/api/v1/exercises", tags=["exercises"])
app.include_router(progress.router, prefix="/api/v1/users", tags=["progress"])

# Phase 4: Quiz + Chat
from app.routers.quiz import router as quiz_router
from app.routers.chat import router as chat_router

app.include_router(quiz_router, prefix="/api/v1", tags=["quiz"])
app.include_router(chat_router, prefix="/api/v1", tags=["chat"])

# Phase 5: TTS + Notifications
app.include_router(tts.router, prefix="/api/v1/tts", tags=["tts"])
from app.routers.notifications import router as notifications_router
app.include_router(notifications_router, prefix="/api/v1", tags=["notifications"])

# Phase 6: CMS/Support
from app.routers.cms import router as cms_router
app.include_router(cms_router, prefix="/api/v1", tags=["cms"])

# Health endpoint
app.include_router(health_router, tags=["health"])


# ─── Root endpoint ───
@app.get("/")
def root():
    return {
        "status": "1",
        "data": {
            "message": "Bestie ESL API - English Learning for Mongolian Speakers",
            "version": "2.0.0",
            "docs": "/docs",
        },
        "message": "Welcome",
    }
