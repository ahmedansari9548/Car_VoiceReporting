import sys
from pathlib import Path

# Ensure src directory is in sys.path so 'app' imports work
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.api.routes.ws import router as ws_router
from app.core.config import settings
from app.db.database import init_db
from app.db.seed import seed_inventory
from app.services.catalog import load as load_catalog

app = FastAPI(title="PakWheels Car Finder", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()
    seed_inventory()
    load_catalog()


app.include_router(api_router, prefix="/api")
app.include_router(ws_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/debug")
def debug():
    """Debug info for the frontend debug panel."""
    from app.db.database import get_connection
    try:
        conn = get_connection()
        cur = conn.cursor()
        counts = {}
        for t in ["sessions", "turns", "inventory", "inspections", "corrections"]:
            cur.execute(f"SELECT COUNT(*) FROM {t}")
            counts[t] = cur.fetchone()[0]
        cur.execute("SELECT id, phase, turn_count, status FROM sessions ORDER BY created_at DESC LIMIT 5")
        recent = [{"id": r[0], "phase": r[1], "turns": r[2], "status": r[3]} for r in cur.fetchall()]
        cur.execute("SELECT id, buyer_name, buyer_phone, preferred_date, status FROM inspections ORDER BY created_at DESC LIMIT 5")
        inspections = [{"id": r[0], "name": r[1], "phone": r[2], "date": r[3], "status": r[4]} for r in cur.fetchall()]
        cur.close()
        conn.close()
        return {
            "db_connected": True,
            "model": settings.LLM_MODEL,
            "counts": counts,
            "recent_sessions": recent,
            "recent_inspections": inspections,
        }
    except Exception as e:
        return {"db_connected": False, "error": str(e)}