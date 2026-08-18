from fastapi import APIRouter
from app.api.routes import turn, transcribe, search, voice, cars

api_router = APIRouter()
api_router.include_router(turn.router,      prefix="/turns",      tags=["turns"])
api_router.include_router(voice.router,      prefix="/voice-turn", tags=["voice"])
api_router.include_router(transcribe.router, prefix="/transcribe", tags=["stt"])
api_router.include_router(search.router,     prefix="/search",     tags=["search"])
api_router.include_router(cars.router,       prefix="/cars",       tags=["cars"])