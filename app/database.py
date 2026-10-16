
from sqlalchemy import create_engine, text

from app.config import BASE_DIR, get_database_url

engine = create_engine(
    get_database_url(),
    pool_pre_ping=True,
)


def check_connection():
    with engine.connect() as connection:
        return connection.execute(
            text("SELECT 1")
        ).scalar_one() == 1


def read_sql_file(filename):
    path = BASE_DIR / "sql" / filename
    return path.read_text(encoding="utf-8")
