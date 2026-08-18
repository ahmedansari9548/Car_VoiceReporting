"""
POST /api/transcribe — speech to text via Whisper on Groq.

Phase 2 endpoint. Ready now so the contract is defined.
The frontend will send recorded audio here, get back text,
then send that text to POST /turns — same pipeline.
"""

from fastapi import APIRouter, UploadFile, File

from app.api.schemas.transcribe import TranscribeOut
from app.clients.groq import transcribe

router = APIRouter()


@router.post("", response_model=TranscribeOut)
async def transcribe_audio(file: UploadFile = File(...)):
    audio_bytes = await file.read()
    text = transcribe(audio_bytes, filename=file.filename or "audio.webm")
    return TranscribeOut(text=text)