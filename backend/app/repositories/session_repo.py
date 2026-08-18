import json
import uuid
import psycopg2.extras


def create(conn) -> str:
    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    cur = conn.cursor()
    cur.execute("INSERT INTO sessions (id) VALUES (%s)", (session_id,))
    conn.commit()
    cur.close()
    return session_id


def get(conn, session_id: str) -> dict:
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM sessions WHERE id = %s", (session_id,))
    row = cur.fetchone()
    cur.close()
    if row is None:
        raise KeyError(f"Session {session_id} not found")
    result = dict(row)
    if isinstance(result["slots"], str):
        result["slots"] = json.loads(result["slots"])
    if isinstance(result.get("selected_car"), str):
        result["selected_car"] = json.loads(result["selected_car"])
    return result


def save_slots(conn, session_id: str, slots: dict) -> None:
    cur = conn.cursor()
    cur.execute(
        "UPDATE sessions SET slots = %s, updated_at = now() WHERE id = %s",
        (json.dumps(slots), session_id),
    )
    conn.commit()
    cur.close()


def set_phase(conn, session_id: str, phase: str) -> None:
    cur = conn.cursor()
    cur.execute(
        "UPDATE sessions SET phase = %s, updated_at = now() WHERE id = %s",
        (phase, session_id),
    )
    conn.commit()
    cur.close()


def set_selected_car(conn, session_id: str, car: dict) -> None:
    """Set the selected car AND move to selected phase."""
    cur = conn.cursor()
    cur.execute(
        "UPDATE sessions SET selected_car = %s, phase = 'selected', "
        "updated_at = now() WHERE id = %s",
        (json.dumps(car), session_id),
    )
    conn.commit()
    cur.close()


def clear_selected_car(conn, session_id: str) -> None:
    """
    Clear the selected car WITHOUT touching phase.

    CRITICAL: do NOT use set_selected_car(conn, sid, None) for this —
    that version hardcodes phase='selected', which silently undoes any
    set_phase('searching') call and leaves the session in a broken state
    (phase=selected with no car), causing the next search to show a
    random car.
    """
    cur = conn.cursor()
    cur.execute(
        "UPDATE sessions SET selected_car = NULL, updated_at = now() WHERE id = %s",
        (session_id,),
    )
    conn.commit()
    cur.close()


def increment_turn(conn, session_id: str) -> None:
    cur = conn.cursor()
    cur.execute(
        "UPDATE sessions SET turn_count = turn_count + 1, "
        "updated_at = now() WHERE id = %s",
        (session_id,),
    )
    conn.commit()
    cur.close()


def set_status(conn, session_id: str, status: str) -> None:
    cur = conn.cursor()
    cur.execute(
        "UPDATE sessions SET status = %s, updated_at = now() WHERE id = %s",
        (status, session_id),
    )
    conn.commit()
    cur.close()


def set_language(conn, session_id: str, language: str) -> None:
    cur = conn.cursor()
    cur.execute(
        "UPDATE sessions SET language = %s WHERE id = %s",
        (language, session_id),
    )
    conn.commit()
    cur.close()