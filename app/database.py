from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, DeclarativeBase
from app.config import settings


class Base(DeclarativeBase):
    pass


# Ensure we use the correct database URL even if a parent .env overrides it
_db_url = settings.database_url_with_params
if not _db_url or not _db_url.startswith(("sqlite", "postgresql", "mysql")):
    _db_url = "sqlite:///esl.db?check_same_thread=false"

engine = create_engine(
    _db_url,
    echo=settings.database_echo,
    connect_args={"check_same_thread": False} if _db_url.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
