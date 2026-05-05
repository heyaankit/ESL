from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import engine, Base
from app.models.lesson import LessonItem
from app.models.user import User, UserProgress
from app.services.excel_importer import import_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    import_data()
    yield


app = FastAPI(lifespan=lifespan)

from app.routers import lessons, words, grammar, exercises, progress

app.include_router(lessons.router, prefix="/lessons", tags=["lessons"])
app.include_router(words.router, prefix="/words", tags=["words"])
app.include_router(grammar.router, prefix="/grammar", tags=["grammar"])
app.include_router(exercises.router, prefix="/exercises", tags=["exercises"])
app.include_router(progress.router, prefix="/users", tags=["progress"])


@app.get("/")
def root():
    return {"message": "ESL API - English Learning for Mongolian Speakers"}


@app.get("/health")
def health():
    return {"status": "ok"}