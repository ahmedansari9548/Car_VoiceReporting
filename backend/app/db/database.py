"""
app/db/database.py

Postgres connection, init, and FastAPI dependency.
The only file that knows which database we use.
"""

import psycopg2
import psycopg2.extras
from pathlib import Path

from app.core.config import settings

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_connection():
    conn = psycopg2.connect(settings.DATABASE_URL)
    conn.autocommit = False
    return conn


def init_db() -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(_SCHEMA_PATH.read_text())
    conn.commit()
    cur.close()
    conn.close()


def get_db():
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()