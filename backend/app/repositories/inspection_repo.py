import json
import psycopg2.extras


def create(conn, session_id: str, car: dict, details: dict) -> int:
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO inspections "
        "(session_id, car_id, car_details, buyer_name, buyer_phone, "
        "preferred_date, preferred_time, location) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (
            session_id,
            car.get("id"),
            json.dumps(car),
            details.get("name"),
            details.get("phone"),
            details.get("date"),
            details.get("time"),
            details.get("location", car.get("city")),
        ),
    )
    row_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    return row_id


def get_by_session(conn, session_id: str) -> dict | None:
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT * FROM inspections WHERE session_id = %s ORDER BY created_at DESC LIMIT 1",
        (session_id,),
    )
    row = cur.fetchone()
    cur.close()
    return dict(row) if row else None