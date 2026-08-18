"""
app/repositories/inventory_repo.py

Queries the inventory table for the buy flow.
"""

import psycopg2.extras


def search(conn, filters: dict, limit: int = 20) -> list[dict]:
    """Search inventory with filters. Returns matching cars, cheapest first."""
    conditions, params = [], []

    if filters.get("id"):
        conditions.append("id = %s")
        params.append(int(filters["id"]))

    text_filters = {
        "make": "make", "model": "model", "city": "city",
        "transmission": "transmission", "body_type": "body_type",
        "assembly": "assembly", "engine_type": "engine_type", "color": "color",
    }
    for key, column in text_filters.items():
        if filters.get(key) and str(filters[key]).lower() != "all":
            conditions.append(f"{column} ILIKE %s")
            params.append(filters[key])

    range_filters = [
        ("price_max", "price <= %s"),
        ("price_min", "price >= %s"),
        ("mileage_max", "mileage_km <= %s"),
        ("year_min", "model_year >= %s"),
        ("year_max", "model_year <= %s"),
    ]
    for key, clause in range_filters:
        if filters.get(key):
            conditions.append(clause)
            params.append(int(filters[key]))

    where = " AND ".join(conditions) if conditions else "TRUE"
    params.append(limit)

    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        f"SELECT * FROM inventory WHERE {where} ORDER BY price ASC LIMIT %s",
        params,
    )
    rows = cur.fetchall()
    cur.close()
    return [dict(r) for r in rows]


def count(conn, filters: dict) -> int:
    """Count matching cars without fetching them."""
    conditions, params = [], []

    if filters.get("id"):
        conditions.append("id = %s")
        params.append(int(filters["id"]))

    for key in ["make", "model", "city", "transmission", "body_type",
                "assembly", "engine_type", "color"]:
        if filters.get(key) and str(filters[key]).lower() != "all":
            conditions.append(f"{key} ILIKE %s")
            params.append(filters[key])

    for key, clause in [
        ("price_max", "price <= %s"), ("price_min", "price >= %s"),
        ("mileage_max", "mileage_km <= %s"),
        ("year_min", "model_year >= %s"), ("year_max", "model_year <= %s"),
    ]:
        if filters.get(key):
            conditions.append(clause)
            params.append(int(filters[key]))

    where = " AND ".join(conditions) if conditions else "TRUE"
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM inventory WHERE {where}", params)
    result = cur.fetchone()[0]
    cur.close()
    return result


def get_by_id(conn, car_id: int) -> dict | None:
    """Fetch a single car by id."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM inventory WHERE id = %s", (car_id,))
    row = cur.fetchone()
    cur.close()
    return dict(row) if row else None