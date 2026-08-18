"""
app/repositories/turn_repo.py

All SQL for turns and corrections tables.
"""

import json
from typing import Optional

import psycopg2.extras


def log_turn(
    conn,
    session_id: str,
    turn_index: int,
    role: str,
    text: str,
    transcript_raw: Optional[str] = None,
    slots_extracted: Optional[dict] = None,
    latency_ms: Optional[int] = None,
) -> int:
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO turns "
        "(session_id, turn_index, role, text, transcript_raw, slots_extracted, latency_ms) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (
            session_id, turn_index, role, text, transcript_raw,
            json.dumps(slots_extracted) if slots_extracted else None,
            latency_ms,
        ),
    )
    row_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    return row_id


def log_correction(
    conn,
    session_id: str,
    turn_index: int,
    slot: str,
    extracted: str,
    corrected: str,
) -> None:
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO corrections "
        "(session_id, turn_index, slot, extracted, corrected) "
        "VALUES (%s, %s, %s, %s, %s)",
        (session_id, turn_index, slot, extracted, corrected),
    )
    conn.commit()
    cur.close()


def get_history(conn, session_id: str, last_n: int = 12) -> list[dict]:
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT role, text FROM turns "
        "WHERE session_id = %s ORDER BY turn_index DESC LIMIT %s",
        (session_id, last_n),
    )
    rows = cur.fetchall()
    cur.close()
    return [{"role": r["role"], "text": r["text"]} for r in reversed(rows)]