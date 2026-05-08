from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from app.database import engine, Base
from app.models.lesson import LessonItem
from app.models.user import User, UserProgress
from app.services.excel_importer import import_data
from app.logger import logger
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting ESL application")
    Base.metadata.create_all(bind=engine)
    import_data()
    yield
    logger.info("Shutting down ESL application")


app = FastAPI(
    title="ESL API",
    description="English Learning for Mongolian Speakers API",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation error on {request.url}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error(f"Database error on {request.url}: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Database error occurred"},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.url}: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


from app.routers import lessons, words, grammar, exercises, progress, auth, tts

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(lessons.router, prefix="/api/v1/lessons", tags=["lessons"])
app.include_router(words.router, prefix="/api/v1/words", tags=["words"])
app.include_router(grammar.router, prefix="/api/v1/grammar", tags=["grammar"])
app.include_router(exercises.router, prefix="/api/v1/exercises", tags=["exercises"])
app.include_router(progress.router, prefix="/api/v1/users", tags=["progress"])
app.include_router(tts.router, prefix="/api/v1/tts", tags=["tts"])


@app.get("/")
def root():
    return {"message": "ESL API - English Learning for Mongolian Speakers"}


@app.get("/health")
def health():
    return {"status": "ok"}