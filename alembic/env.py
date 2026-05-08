from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, create_engine
from alembic import context
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base
from app.config import settings

# Import ALL models so Alembic can detect them
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

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url_with_params)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # Use the URL from settings directly to avoid parent .env interference
    connectable = create_engine(
        settings.database_url_with_params,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
