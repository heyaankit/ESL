import pandas as pd
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models.lesson import LessonItem
from app.logger import logger
from app.config import settings


def import_data():
    df = pd.read_excel(settings.excel_file_path, sheet_name="All_Lessons")

    db = SessionLocal()
    try:
        existing_count = db.query(LessonItem).count()
        if existing_count > 0:
            logger.info(f"Data already exists ({existing_count} records). Skipping import.")
            return

        records = []
        for _, row in df.iterrows():
            vocab_word = row["vocabulary_word"]
            if pd.isna(vocab_word) or str(vocab_word).strip() == "":
                continue

            record = LessonItem(
                id=int(row["id"]),
                lesson=row["lesson"],
                sub_topic=row["sub_topic"],
                grammar_topic=row.get("grammar_topic"),
                word_number=row.get("word_number"),
                vocabulary_word=vocab_word,
                meaning=row.get("meaning"),
                example_sentence=row.get("example_sentence"),
                conversation_question=row.get("conversation_question"),
                conversation_affirmative=row.get("conversation_affirmative"),
                conversation_interrogative=row.get("conversation_interrogative"),
                conversation_yes=row.get("conversation_yes"),
                conversation_no=row.get("conversation_no"),
                grammar_explanation=row.get("grammar_explanation"),
                exercise_type=row.get("exercise_type"),
                exercise_answers=row.get("exercise_answers"),
                notes=row.get("notes"),
            )
            records.append(record)

        db.bulk_save_objects(records)
        db.commit()
        logger.info(f"Imported {len(records)} records successfully.")

    except Exception as e:
        db.rollback()
        logger.error(f"Error importing data: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import_data()