import traceback
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from app.api.schemas.turn import TurnOut
from app.clients.groq import transcribe
from app.db.database import get_db
from app.services.conversation import process_turn

router = APIRouter()


class VoiceTurnOut(TurnOut):
    transcript: str = ""


@router.post("", response_model=VoiceTurnOut)
async def voice_turn(
    file: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    db=Depends(get_db),
):
    if not session_id or session_id == "string":
        session_id = None
    try:
        audio_bytes = await file.read()
        transcript = transcribe(audio_bytes, filename=file.filename or "audio.webm")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Transcription failed: {str(e)}")
    if not transcript.strip():
        raise HTTPException(status_code=400, detail="Could not understand audio.")
    try:
        result = process_turn(db, session_id, transcript)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return VoiceTurnOut(
        session_id=result.session_id,
        reply=result.reply,
        slots=result.slots,
        pakwheels_url=result.pakwheels_url,
        cars=result.cars,
        total_results=result.total_results,
        transcript=transcript,
    )