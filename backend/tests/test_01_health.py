"""Test 1: Backend is alive, DB connected, inventory seeded."""


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_debug_endpoint(client):
    r = client.get("/api/debug")
    assert r.status_code == 200
    data = r.json()
    assert data["db_connected"] is True


def test_inventory_seeded(client):
    r = client.get("/api/debug")
    data = r.json()
    assert data["counts"]["inventory"] >= 50, f"Only {data['counts']['inventory']} cars seeded"
