from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, DeclarativeBase
from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.database_url_with_params,
    echo=settings.database_echo,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()