"""Test 10: Database persistence — sessions, turns, and slots saved correctly."""


def test_session_created_in_db(client, new_chat):
    result, sid = new_chat("Corolla Lahore 30 lakh")

    r = client.get("/api/debug")
    data = r.json()
    assert data["counts"]["sessions"] > 0, "No sessions in database"

    # check the session exists in recent list
    session_ids = [s["id"] for s in data["recent_sessions"]]
    assert sid in session_ids, f"Session {sid} not found in DB"


def test_turns_logged(client, new_chat, turn):
    result, sid = new_chat("Civic Lahore 50 lakh")
    turn("only automatic", sid)
    turn("white color", sid)

    r = client.get("/api/debug")
    data = r.json()

    # should have turns logged
    assert data["counts"]["turns"] > 0, "No turns logged"


def test_inventory_unchanged(client):
    """Tests should not accidentally modify inventory."""
    r = client.get("/api/debug")
    data = r.json()
    assert data["counts"]["inventory"] >= 50, \
        f"Inventory shrunk to {data['counts']['inventory']}"
