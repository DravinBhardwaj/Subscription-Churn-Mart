
from sqlalchemy import create_engine, text

from app.config import get_database_url


engine = create_engine(
    get_database_url(),
    pool_pre_ping=True,
)


def check_connection():
    """Check whether PostgreSQL is reachable."""

    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        return result.scalar() == 1


def read_sql_file(filename):
    """Read a SQL script from the sql folder."""

    from app.config import BASE_DIR

    path = BASE_DIR / "sql" / filename
    return path.read_text(encoding="utf-8")
