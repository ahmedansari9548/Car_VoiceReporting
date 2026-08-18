"""
app/api/schemas/search.py

Buy flow output. Filters, real URL, matching cars.
"""

from typing import Optional
from pydantic import BaseModel


class SearchOut(BaseModel):
    filters: dict[str, str]
    pakwheels_url: str
    cars: list[dict]
    total_results: int
    summary: str