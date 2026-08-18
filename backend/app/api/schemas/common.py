"""
app/api/schemas/common.py

Shared types across all schemas.

SlotValue carries not just the value but HOW we know it:
  - "said"    → the buyer told us
  - "derived" → we inferred it (e.g. "family car" → Sedan)

This drives the SAID / DERIVED badges in the UI.
"""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel


class Source(str, Enum):
    SAID = "said"
    DERIVED = "derived"


class SlotValue(BaseModel):
    value: Any
    source: Source
    confidence: float = 1.0
    turn: Optional[int] = None