from typing import Optional
from pydantic import BaseModel
from .common import SlotValue


class TurnIn(BaseModel):
    session_id: Optional[str] = None
    text: str

class TurnOut(BaseModel):
    session_id: str
    reply: str
    slots: dict[str, SlotValue]

    done: bool = False
    intent: str = "buy"

    phase: str = "searching"

    pakwheels_url: Optional[str] = None
    cars: Optional[list[dict]] = None
    total_results: Optional[int] = None

    selected_car: Optional[dict] = None
    inspection: Optional[dict] = None