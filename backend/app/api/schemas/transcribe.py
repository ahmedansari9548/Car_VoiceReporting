"""
app/api/schemas/transcribe.py

Speech-to-text response. Phase 2 (voice) only — but the schema
exists now so the route contract is defined.
"""

from typing import Optional

from pydantic import BaseModel


class TranscribeOut(BaseModel):
    text: str
    language: Optional[str] = None
