import traceback
from fastapi import APIRouter, Depends, HTTPException
from app.api.schemas.turn import TurnIn, TurnOut
from app.db.database import get_db
from app.services.conversation import process_turn

router = APIRouter()


@router.post("", response_model=TurnOut)
def create_turn(payload: TurnIn, db=Depends(get_db)):
    session_id = payload.session_id
    if not session_id or session_id == "string":
        session_id = None
    try:
        return process_turn(db, session_id, payload.text)
    except Exception as e:
        tb = traceback.format_exc()
        print(f"\n{'='*60}\n{tb}\n{'='*60}")
        raise HTTPException(status_code=500, detail=str(e))