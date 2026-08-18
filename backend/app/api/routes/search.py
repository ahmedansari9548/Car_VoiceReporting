from fastapi import APIRouter, Depends, HTTPException
from app.api.schemas.search import SearchOut
from app.api.schemas.turn import TurnIn
from app.db.database import get_db
from app.services.conversation import process_turn
from app.services.search_url import summarize_filters

router = APIRouter()


@router.post("", response_model=SearchOut)
def search(payload: TurnIn, db=Depends(get_db)):
    session_id = payload.session_id
    if not session_id or session_id == "string":
        session_id = None
    try:
        result = process_turn(db, session_id, payload.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    filters = {k: v.value for k, v in result.slots.items() if v.value is not None}
    return SearchOut(
        filters=filters,
        pakwheels_url=result.pakwheels_url or "",
        cars=result.cars or [],
        total_results=result.total_results or 0,
        summary=summarize_filters(filters),
    )