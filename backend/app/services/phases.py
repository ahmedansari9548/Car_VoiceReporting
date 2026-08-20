"""
app/services/phases.py

Phase-specific handlers. Each takes state in, returns updated state.
"""

from __future__ import annotations

import re

from app.core.constants import SOURCE_DERIVED, SOURCE_SAID
from app.core.utils import slot_value
from app.repositories import session_repo, turn_repo, inventory_repo, inspection_repo
from app.services.search_url import apply_need, build_url

from app.services.helpers import (
    format_car, slots_to_filters, to_schema,
    user_selecting, parse_selection, wants_inspection,
)
from app.services.context import (
    build_state_context, build_catalog_context, build_inventory_context_from_cars,
)
from app.services.guards import guard_wrong_car
from app.services.tools import get_tool_schemas, execute_tool
from app.clients.groq import call_with_tools
from app.api.schemas.turn import TurnOut


# ═══════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════

SEARCH_LIMIT = 10
HISTORY_TURNS = 12
INSPECTION_FIELDS = ["name", "phone", "date", "time"]
INSPECTION_SLOT_MAP = {
    "buyer_name": "name",
    "buyer_phone": "phone",
    "preferred_date": "date",
    "preferred_time": "time",
}

# "yes" to an inspection offer
AFFIRMATIVE_WORDS = {
    "haan", "han", "ha", "yes", "yep", "yeah", "sure", "ok", "okay",
    "ji", "jee", "thik", "theek", "bilkul", "zaroor", "karo", "kardo",
    "chalo", "chalain", "lelo", "book", "karwao", "karani", "karna",
    "ہاں", "جی", "ٹھیک", "بالکل", "ضرور",
}

_MONTHS = ("january|february|march|april|may|june|july|august|september|"
           "october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec")


# ═══════════════════════════════════════════════════════════════
# SEARCH
# ═══════════════════════════════════════════════════════════════

def run_search(conn, filters: dict, sort: dict | None = None):
    """Run one inventory search. Returns (cars, total, url)."""
    url = build_url(filters)
    total = inventory_repo.count(conn, filters)
    rows = inventory_repo.search(conn, filters, limit=SEARCH_LIMIT)
    cars = [format_car(r) for r in rows]

    # Always sort by price. Cheapest first unless the user asked otherwise.
    if cars:
        reverse = sort.get("order") == "desc" if sort else False
        cars.sort(key=lambda c: c.get("price") or 0, reverse=reverse)
        if sort and sort.get("single"):
            cars = cars[:1]
            total = 1

    return cars, total, url


# ═══════════════════════════════════════════════════════════════
# LLM CALL
# ═══════════════════════════════════════════════════════════════

def call_llm(conn, session_id, text, slots, missing, context, hints, language: str = "en") -> dict:
    action = {
        "action": "ask_question", "reply": "", "need": None,
        "car_index": 0, "inspection_data": {},
    }

    try:
        response = call_with_tools(
            text=text, current_slots=slots, missing=missing,
            catalog_context=context, number_hints=hints,
            history=turn_repo.get_history(conn, session_id, last_n=HISTORY_TURNS),
            tools=get_tool_schemas(),
            language=language,
        )
        tool_calls = response.get("tool_calls", [])
    except Exception as e:
        print(f"[LLM ERROR] {e}")
        return action

    if not tool_calls and response.get("fallback_reply"):
        action["reply"] = response["fallback_reply"]
        return action

    for tc in tool_calls:
        name = tc.get("name")
        result = execute_tool(conn, name, tc.get("arguments", {}), slots)
        if not result.get("success", True):
            print(f"[TOOL FAIL] {name}: {result.get('error')}")
            continue

        data = result.get("data", {})
        if name == "determine_action":
            action.update(data)
        elif name == "select_car":
            action["action"] = "select_car"
            action["car_index"] = data.get("selected_index", 0)
        elif name == "extract_inspection":
            action["inspection_data"] = data

    return action


# ═══════════════════════════════════════════════════════════════
# SEARCHING PHASE
# ═══════════════════════════════════════════════════════════════

def handle_searching(conn, session_id, action, text, slots, cars, total,
                     url, last_shown, selected_car, phase, turn_index):
    # Implicit need ("family car" → sedan/hatchback)
    need = action.get("need")
    if need and cars is not None:
        need_filters = apply_need(slots_to_filters(slots), need)
        if "body_type" in need_filters and not slot_value(slots, "body_type"):
            slots["body_type"] = {
                "value": need_filters["body_type"], "source": SOURCE_DERIVED,
                "confidence": 0.8, "turn": turn_index,
            }
        cars, total, url = run_search(conn, need_filters)
        slots["_last_shown"] = cars

    # Selection via LLM tool call
    if action.get("action") == "select_car" and not selected_car:
        idx = action.get("car_index", 0)
        source = cars or last_shown
        if source and 0 <= idx < len(source):
            selected_car = source[idx]
            session_repo.set_selected_car(conn, session_id, selected_car)
            phase = "selected"
            cars, total = [selected_car], 1

    # Selection via keyword fallback
    elif not selected_car and user_selecting(text) and (cars or last_shown):
        source = cars or last_shown
        idx = parse_selection(text, source)
        if idx is not None:
            selected_car = source[idx]
            session_repo.set_selected_car(conn, session_id, selected_car)
            phase = "selected"
            cars, total = [selected_car], 1

    return cars, total, url, selected_car, phase


# ═══════════════════════════════════════════════════════════════
# INSPECTION DETAIL EXTRACTION
# ═══════════════════════════════════════════════════════════════

def extract_booking_details(text: str) -> dict:
    """
    Pull name / phone / date / time out of raw text.

    Runs alongside the LLM, not instead of it. The LLM regularly misses
    "August 30th around 7:00 p.m." — this does not.
    """
    result: dict[str, str] = {}
    lower = text.lower()

    # ── Phone ──
    compact = re.sub(r"[\s\-()]", "", text)
    phone = re.search(r"\b(0\d{9,10}|\+92\d{10}|\d{11})\b", compact)
    if phone:
        result["phone"] = phone.group(1)
    else:
        # "phone number 123678945" — labelled, so accept 7-11 digits
        labelled = re.search(r"(?:phone|number|mobile|cell|نمبر)\D{0,10}(\d{7,11})", lower)
        if labelled:
            result["phone"] = labelled.group(1)

    # ── Date ──
    # Order matters: day-before-month first, and never let a clock time
    # ("September 3:30") be read as a day number.
    date_patterns = [
        rf"(\d{{1,2}})(?:st|nd|rd|th)?\s+({_MONTHS})",          # 15 September
        rf"({_MONTHS})\s+(\d{{1,2}})(?:st|nd|rd|th)?(?!\s*:)",  # August 30th
        r"(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)",                # 30/08/2026
    ]
    for pattern in date_patterns:
        m = re.search(pattern, lower)
        if m:
            result["date"] = m.group(0).strip()
            break
    else:
        relative = re.search(
            r"\b(kal|parson|parso|aaj|today|tomorrow|day after tomorrow|"
            r"monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
            r"peer|mangal|budh|jumeraat|juma|hafta|itwaar)\b",
            lower,
        )
        if relative:
            result["date"] = relative.group(1)

    # ── Time ──
    time_match = re.search(
        r"(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.?|p\.m\.?|بجے))", lower
    )
    if time_match:
        result["time"] = time_match.group(1).strip()
    else:
        part = re.search(r"\b(subah|dopahar|shaam|raat|morning|afternoon|evening|night)\b", lower)
        if part:
            result["time"] = part.group(1)

    # ── Name ──
    name_match = re.search(
        r"(?:mera naam|my name is|naam|name is|name)\s+(?:hai\s+)?"
        r"([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)",
        text,
    )
    if name_match:
        candidate = name_match.group(1).strip()
        if candidate.lower() not in {"hai", "is", "phone", "number"}:
            result["name"] = candidate

    return result


# ═══════════════════════════════════════════════════════════════
# INSPECTION PHASE
# ═══════════════════════════════════════════════════════════════

def handle_inspection(conn, session_id, action, text, slots, selected_car, phase):
    """
    Collect booking details. Returns (phase, inspection).

    This function MUST NOT change selected_car. The caller passes it in
    only so the booking can be written against the right vehicle.
    """
    inspection = None
    tokens = set(re.findall(r"\w+", text.lower()))

    # ── Enter inspection phase ──
    # Three signals: LLM action, explicit inspection words, or a plain
    # "haan"/"yes" while a car is selected (they are answering the offer).
    should_enter = (
        action.get("action") == "schedule_inspection"
        or wants_inspection(text)
        or (phase == "selected" and bool(tokens & AFFIRMATIVE_WORDS))
    )

    if should_enter and phase != "inspection":
        phase = "inspection"
        session_repo.set_phase(conn, session_id, "inspection")
        print("[INSPECTION] entered")

    # ── Gather details: LLM tool output ──
    new_data = dict(action.get("inspection_data") or {})
    for slot_name, key in INSPECTION_SLOT_MAP.items():
        val = slot_value(slots, slot_name)
        if val:
            new_data[key] = val

    # ── Gather details: deterministic text parsing (fills LLM gaps) ──
    if phase == "inspection":
        for key, value in extract_booking_details(text).items():
            if value and not new_data.get(key):
                new_data[key] = value
                print(f"[INSPECTION] parsed {key}={value} from text")

    # ── Merge and check completeness ──
    if action.get("action") == "confirm_inspection" or (phase == "inspection" and new_data):
        collected = dict(slots.get("_inspection", {}))
        collected.update({k: v for k, v in new_data.items() if v})
        slots["_inspection"] = collected

        still_missing = [f for f in INSPECTION_FIELDS if not collected.get(f)]

        if not still_missing:
            if not selected_car:
                print("[INSPECTION] ABORT — no selected car, refusing to book")
                return phase, None

            insp_id = inspection_repo.create(conn, session_id, selected_car, collected)
            phase = "confirmed"
            session_repo.set_phase(conn, session_id, "confirmed")
            session_repo.set_status(conn, session_id, "completed")
            inspection = collected
            print(f"[INSPECTION] booked #{insp_id} for "
                  f"{selected_car.get('year')} {selected_car.get('make')} {selected_car.get('model')}")
        else:
            phase = "inspection"
            session_repo.set_phase(conn, session_id, "inspection")
            print(f"[INSPECTION] have={list(collected)} need={still_missing}")

    return phase, inspection


# ═══════════════════════════════════════════════════════════════
# "ASK AI ABOUT THIS CAR" BUTTON
# ═══════════════════════════════════════════════════════════════

def handle_ask_ai(conn, session_id, text, parsed_car, slots, language, turn_index):
    """Frontend button. Fetches the full DB row so the image survives."""
    car = parsed_car
    car_id = parsed_car.get("car_id")

    if car_id:
        try:
            rows = inventory_repo.search(conn, {"id": car_id}, limit=1)
            if rows:
                car = format_car(rows[0])
                print(f"[ASK AI] loaded id={car_id}")
        except Exception as e:
            print(f"[ASK AI] lookup failed ({e}), using parsed data")

    session_repo.set_selected_car(conn, session_id, car)
    phase = "selected"

    for field in ["make", "model", "city"]:
        if car.get(field):
            slots[field] = {"value": car[field], "source": SOURCE_SAID,
                            "confidence": 1.0, "turn": turn_index}

    context = "\n\n".join(filter(None, [
        build_state_context(phase, slots, car, language),
        build_catalog_context(slots),
        build_inventory_context_from_cars([car]),
    ]))

    action = call_llm(conn, session_id, text, slots, [], context, "", language)
    reply = (action.get("reply") or "").strip()

    wrong = guard_wrong_car(reply, car, language)
    if wrong:
        reply = wrong

    if not reply:
        if language == "ur":
            reply = (f"یہ {car['year']} {car['make']} {car['model']} {car.get('variant', '')} ہے — "
                     f"Rs {car['price']:,}، {car['city']}، {car.get('mileage', 0)} کلومیٹر۔ "
                     f"کیا آپ اس کی PakWheels انسپکشن بک کرنا چاہیں گے؟")
        else:
            reply = (f"This is the {car['year']} {car['make']} {car['model']} {car.get('variant', '')} — "
                     f"Rs {car['price']:,} in {car['city']}, {car.get('mileage', 0)} km. "
                     f"Would you like to book a PakWheels inspection?")

    _persist(conn, session_id, turn_index, text, reply, slots)

    return TurnOut(
        session_id=session_id, reply=reply, slots=to_schema(slots),
        phase=phase, cars=[car], total_results=1,
        selected_car=car, inspection=None,
    )


# ═══════════════════════════════════════════════════════════════
# SHARED
# ═══════════════════════════════════════════════════════════════

def _persist(conn, session_id, turn_index, user_text, reply, slots):
    session_repo.save_slots(conn, session_id, slots)
    session_repo.increment_turn(conn, session_id)
    turn_repo.log_turn(conn, session_id, turn_index, "user", user_text)
    turn_repo.log_turn(conn, session_id, turn_index, "assistant", reply)