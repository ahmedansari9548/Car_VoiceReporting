"""
app/services/tools.py

Tool schemas and executors for LLM tool calling.

Numeric slots are sanitized here — the LLM sends "1 crore" as a string,
and downstream code expects an int. Values outside believable ranges are
dropped entirely (a phone number is not a price).
"""

from __future__ import annotations

import re
import traceback
from typing import Callable

from app.core.utils import slot_value
from app.core.constants import SOURCE_SAID
from app.services.prices import normalize_price_value


class ToolRegistry:
    def __init__(self):
        self._schemas: dict[str, dict] = {}
        self._handlers: dict[str, Callable] = {}

    def register(self, name: str, schema: dict, handler: Callable):
        self._schemas[name] = schema
        self._handlers[name] = handler

    def get_schemas(self) -> list[dict]:
        return [
            {"type": "function", "function": {"name": name, **schema}}
            for name, schema in self._schemas.items()
        ]

    def execute(self, conn, name: str, arguments: dict, slots: dict | None = None) -> dict:
        handler = self._handlers.get(name)
        if not handler:
            return {"success": False, "error": f"Unknown tool: {name}"}
        try:
            result = handler(conn, arguments, slots)
            return {"success": True, "data": result}
        except Exception as e:
            print(f"[TOOL ERROR] {name}: {e}")
            traceback.print_exc()
            return {"success": False, "error": str(e)}


registry = ToolRegistry()


# ═══════════════════════════════════════════════════════════════
# SLOT SANITIZATION
# ═══════════════════════════════════════════════════════════════

PRICE_SLOTS = {"price_max", "price_min"}
MILEAGE_SLOTS = {"mileage_max"}
YEAR_SLOTS = {"year_min", "year_max"}

MILEAGE_RANGE = (0, 1_500_000)
YEAR_RANGE = (1950, 2030)


def _sanitize(slot_name: str, value):
    """
    Returns (clean_value, ok).
    ok=False means the value is nonsense and the update should be skipped.
    """
    if value is None:
        return None, False

    if slot_name in PRICE_SLOTS:
        clean = normalize_price_value(value)
        if clean is None:
            print(f"  [SLOT REJECT] {slot_name}={value!r} is not a valid price")
            return None, False
        return clean, True

    if slot_name in MILEAGE_SLOTS or slot_name in YEAR_SLOTS:
        try:
            clean = int(str(value).replace(",", "").strip())
        except (ValueError, TypeError):
            m = re.search(r"(\d+)", str(value))
            if not m:
                print(f"  [SLOT REJECT] {slot_name}={value!r} is not numeric")
                return None, False
            clean = int(m.group(1))

        low, high = MILEAGE_RANGE if slot_name in MILEAGE_SLOTS else YEAR_RANGE
        if not (low <= clean <= high):
            print(f"  [SLOT REJECT] {slot_name}={clean} outside {low}-{high}")
            return None, False
        return clean, True

    return value, True


# ═══════════════════════════════════════════════════════════════
# TOOL: update_slots
# ═══════════════════════════════════════════════════════════════

UPDATE_SLOTS_SCHEMA = {
    "description": (
        "Extract or update slot values from the user's latest message. "
        "Only include slots explicitly mentioned or corrected. "
        "For price_max/price_min, ALWAYS send a plain integer in rupees "
        "(1 crore = 10000000, 30 lakh = 3000000). Never send text like '1 crore'."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "slot_updates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "slot": {"type": "string"},
                        "value": {"type": "string"},
                        "confidence": {"type": "number"},
                        "is_correction": {"type": "boolean"},
                    },
                    "required": ["slot", "value"],
                },
            }
        },
        "required": ["slot_updates"],
    },
}


def _execute_update_slots(conn, arguments: dict, slots: dict | None) -> dict:
    if slots is None:
        raise ValueError("slots required")

    applied = []

    for update in arguments.get("slot_updates", []):
        name = update.get("slot")
        raw_val = update.get("value")
        if name is None:
            continue

        clean_val, ok = _sanitize(name, raw_val)
        if not ok:
            continue  # nonsense value — leave the existing slot alone

        old = slot_value(slots, name)
        is_correction = update.get("is_correction", False) or (
            old is not None and str(old) != str(clean_val)
        )

        slots[name] = {
            "value": clean_val,
            "source": SOURCE_SAID,
            "confidence": update.get("confidence", 0.9),
            "turn": update.get("turn", 0),
        }
        applied.append({"slot": name, "old": old, "new": clean_val,
                        "is_correction": is_correction})
        print(f"  [SLOT] {name} = {clean_val}")

    return {"applied_updates": applied}


registry.register("update_slots", UPDATE_SLOTS_SCHEMA, _execute_update_slots)


# ═══════════════════════════════════════════════════════════════
# TOOL: select_car
# ═══════════════════════════════════════════════════════════════

SELECT_CAR_SCHEMA = {
    "description": (
        "Select a car from INVENTORY RESULTS by its 0-based index. "
        "Use when the user says 'first one', 'this car', 'ye wali', 'pasand hai'."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "index": {"type": "integer", "description": "0-based index from INVENTORY RESULTS"}
        },
        "required": ["index"],
    },
}


def _execute_select_car(conn, arguments: dict, slots: dict | None = None) -> dict:
    return {"selected_index": arguments.get("index", 0)}


registry.register("select_car", SELECT_CAR_SCHEMA, _execute_select_car)


# ═══════════════════════════════════════════════════════════════
# TOOL: determine_action
# ═══════════════════════════════════════════════════════════════

DETERMINE_ACTION_SCHEMA = {
    "description": (
        "Decide the next action and generate the assistant's reply. "
        "Call this LAST, after update_slots. ALWAYS call this tool."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["search", "select_car", "schedule_inspection",
                         "confirm_inspection", "ask_question", "greet"],
            },
            "need": {
                "type": "string",
                "description": "Implicit need: family, 7_seater, first_car, offroad, luxury, commercial",
            },
            "car_index": {"type": "integer"},
            "reply": {
                "type": "string",
                "description": "The reply to send. Must follow REPLY_LANGUAGE strictly.",
            },
            "detected_language": {"type": "string", "enum": ["en", "ur"]},
        },
        "required": ["action", "reply"],
    },
}


def _execute_determine_action(conn, arguments: dict, slots: dict | None = None) -> dict:
    return arguments


registry.register("determine_action", DETERMINE_ACTION_SCHEMA, _execute_determine_action)


# ═══════════════════════════════════════════════════════════════
# TOOL: extract_inspection
# ═══════════════════════════════════════════════════════════════

EXTRACT_INSPECTION_SCHEMA = {
    "description": "Extract inspection booking details: name, phone, date, or time.",
    "parameters": {
        "type": "object",
        "properties": {
            "buyer_name": {"type": "string"},
            "buyer_phone": {"type": "string"},
            "preferred_date": {"type": "string"},
            "preferred_time": {"type": "string"},
        },
        "required": [],
    },
}


def _execute_extract_inspection(conn, arguments: dict, slots: dict | None = None) -> dict:
    return {k: v for k, v in arguments.items() if v is not None}


registry.register("extract_inspection", EXTRACT_INSPECTION_SCHEMA, _execute_extract_inspection)


# ═══════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════

def get_tool_schemas() -> list[dict]:
    return registry.get_schemas()


def execute_tool(conn, tool_name: str, arguments: dict, slots: dict | None = None) -> dict:
    return registry.execute(conn, tool_name, arguments, slots)