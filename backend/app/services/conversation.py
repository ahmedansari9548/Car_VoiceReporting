"""
app/services/conversation.py

The pipeline. Each numbered step does ONE thing.
Logic lives in guards.py, phases.py, overrides.py, prices.py.

CRITICAL INVARIANT:
  Once phase == "inspection", the selected car is LOCKED. Nothing in this
  file may change it. Every reset path is gated behind that check.
"""

from __future__ import annotations

import re
import time
from typing import Optional

from app.api.schemas.turn import TurnOut
from app.core.utils import slot_value
from app.repositories import session_repo, turn_repo
from app.services.helpers import (
    missing_filters, slots_to_filters, to_schema,
    is_detail_or_selection, parse_selection, fallback_reply,
)
from app.services.handlers import (
    detect_language, is_greeting, has_car_keywords,
    is_car_detail_request, greeting_reply, parse_ask_ai_message,
)
from app.services.overrides import (
    apply_overrides, quick_extract, detect_sort, _MODELS as CAR_MODELS,
)
from app.services.context import (
    build_state_context, build_catalog_context, build_inventory_context_from_cars,
)
from app.services.guards import run_all_guards
from app.services.phases import (
    run_search, call_llm, handle_searching, handle_inspection, handle_ask_ai,
)


# ═══════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════

INSPECTION_SLOT_MAP = {
    "buyer_name": "name", "buyer_phone": "phone",
    "preferred_date": "date", "preferred_time": "time",
}

SEARCH_INTENT_WORDS = {
    "dikhao", "dikha", "dikhaye", "dikhayen", "dikhaiye", "dikhado",
    "show", "find", "search", "dhundho", "dhundo", "chahiye",
    "batayen", "bata", "de", "do", "give", "list", "sab", "sara", "all",
    "koi", "aur", "alava", "dusri", "doosri", "other",
}

# Words meaning "I want to book / keep this car" — these BLOCK a reset
INSPECTION_INTENT_WORDS = {
    "inspection", "inspect", "book", "booking", "schedule",
    "karwao", "karwana", "karani", "karna", "karwani", "lagwao",
    "muayna", "chek", "check",
}

REJECTION_WORDS = {"nahi", "nhi", "nahin", "not", "cancel", "chhodo", "chodo", "skip"}
CAR_REF_WORDS = {"ye", "yeh", "is", "this", "car", "gaari", "gadi", "gari", "wali"}
BODY_TYPE_WORDS = {"suv", "sedan", "hatchback", "crossover", "mpv", "pickup", "van"}
GENERIC_CAR_WORDS = {"car", "cars", "gadi", "gaari", "gari", "gaariyan", "vehicle", "گاڑی", "گاڑیاں"}

RESEARCH_KEYS = {
    "make", "model", "city", "price_max", "price_min",
    "mileage_max", "year_min", "year_max", "transmission", "body_type", "color",
}


# ═══════════════════════════════════════════════════════════════
# PHASE RESET
# ═══════════════════════════════════════════════════════════════

def _should_reset(text: str, selected_car: dict | None, phase: str) -> bool:
    """
    Is the user asking for DIFFERENT cars?

    HARD RULE: during inspection, only an explicit rejection of the car
    can reset. Everything else (names, phone numbers, dates, cities,
    "nahi", stray model words in a name) is booking data, not a new search.
    """
    lower = text.lower()
    tokens = set(re.findall(r"\w+", lower))
    sel_model = (selected_car.get("model", "") if selected_car else "").lower()

    # ── 0. INSPECTION LOCK ──
    # Mid-booking, the user is supplying details. Do not reset unless they
    # clearly reject the car ("ye gaari nahi chahiye", "cancel this car").
    if phase == "inspection":
        explicit_reject = bool(tokens & REJECTION_WORDS) and bool(tokens & CAR_REF_WORDS)
        wants_other = bool(tokens & SEARCH_INTENT_WORDS) and bool(tokens & GENERIC_CAR_WORDS)
        if explicit_reject or wants_other:
            print("[RESET] user rejected car during inspection")
            return True
        return False

    # ── 1. Inspection intent → never reset (they want THIS car) ──
    # "Nahin yah pehli gadi hi, iska inspection book karani hai"
    if tokens & INSPECTION_INTENT_WORDS:
        return False

    # ── 2. Different model named → reset ──
    for kw in CAR_MODELS:
        if kw in lower and kw != sel_model:
            return True

    # ── 3. Different city + search intent → reset ──
    from app.services.overrides import _find_city
    mentioned_city = _find_city(lower)
    if mentioned_city and mentioned_city != "all" and selected_car:
        sel_city = (selected_car.get("city", "") or "").lower()
        if mentioned_city.lower() != sel_city:
            if tokens & SEARCH_INTENT_WORDS or len(tokens) > 5:
                return True

    # ── 4. Sort intent → new search ──
    if detect_sort(text):
        return True

    # ── 5. Rejection of THE CAR (needs both a rejection AND a car word) ──
    if tokens & REJECTION_WORDS and tokens & CAR_REF_WORDS:
        return True

    # ── 6. Short message = an answer, not a new search ──
    if len(tokens) <= 3:
        return False

    if selected_car is None:
        return True

    # ── 7. Search intent words ──
    if tokens & SEARCH_INTENT_WORDS:
        return True

    # ── 8. Different body type ──
    mentioned = tokens & BODY_TYPE_WORDS
    if mentioned:
        sel_body = (selected_car.get("body_type", "") or "").lower()
        if not any(b == sel_body for b in mentioned):
            return True

    return False


# ═══════════════════════════════════════════════════════════════
# STALE FILTER CLEARING
# ═══════════════════════════════════════════════════════════════

def _clear_stale_filters(text: str, slots: dict) -> None:
    lower = text.lower()
    tokens = set(re.findall(r"\w+", lower))

    current_model = slot_value(slots, "model")
    if not current_model:
        return

    if any(kw in lower for kw in CAR_MODELS):
        return  # a specific model was named — overrides will handle it

    should_clear = bool(tokens & GENERIC_CAR_WORDS) or bool(tokens & BODY_TYPE_WORDS) or bool(detect_sort(text))

    if should_clear:
        old_model = current_model
        slots.pop("model", None)
        slots.pop("make", None)
        bt = slots.get("body_type")
        if isinstance(bt, dict) and bt.get("source") != "said":
            slots.pop("body_type", None)
        print(f"[CLEAR] model={old_model} cleared (fresh search)")


# ═══════════════════════════════════════════════════════════════
# PIPELINE
# ═══════════════════════════════════════════════════════════════

def process_turn(conn, session_id: Optional[str], text: str) -> TurnOut:
    start = time.time()
    print(f"\n{'='*60}\n[TURN] '{text[:80]}'")

    # ── 1. LOAD ──
    if not session_id:
        session_id = session_repo.create(conn)

    session = session_repo.get(conn, session_id)
    slots = session["slots"]
    phase = session.get("phase", "searching")
    selected_car = session.get("selected_car")
    lang = session.get("language") or "en"
    turn = session["turn_count"] + 1
    last_shown = slots.get("_last_shown") or []

    # Self-heal: phase says a car is selected but none is stored.
    # Without this, the search runs and a random car (the cheapest) appears.
    if phase in ("selected", "inspection") and not selected_car:
        print(f"[HEAL] phase={phase} but no selected_car — reverting to searching")
        phase = "searching"
        session_repo.set_phase(conn, session_id, "searching")

    print(f"[STATE] phase={phase} car={selected_car.get('model') if selected_car else 'none'}")

    # ── 2. LANGUAGE ──
    det = detect_language(text)
    if det and det != lang:
        lang = det
        session_repo.set_language(conn, session_id, lang)

    # ── 3. EARLY EXITS ──
    if is_greeting(text) and phase == "searching" and not has_car_keywords(text):
        reply = greeting_reply(text, lang)
        _persist(conn, session_id, turn, text, reply, slots)
        return TurnOut(session_id=session_id, reply=reply, slots=to_schema(slots),
                       phase=phase, cars=None, total_results=None,
                       selected_car=selected_car, inspection=None)

    ask_ai = parse_ask_ai_message(text)
    if ask_ai:
        return handle_ask_ai(conn, session_id, text, ask_ai, slots, lang, turn)

    # ── 4. PHASE RESET ──
    if phase in ("selected", "inspection") and _should_reset(text, selected_car, phase):
        print(f"[RESET] {phase} → searching")
        phase, selected_car, last_shown = "searching", None, []
        # ORDER MATTERS: clear the car first (it does not touch phase),
        # then set the phase. Using set_selected_car(None) here would
        # write phase='selected' and corrupt the session.
        session_repo.clear_selected_car(conn, session_id)
        session_repo.set_phase(conn, session_id, "searching")
        for k in list(slots):
            if k.startswith("_") or k in INSPECTION_SLOT_MAP:
                slots.pop(k, None)

    # ── 5. SELECTION SHORTCUT ──
    is_detail = is_car_detail_request(text)

    if is_detail_or_selection(text) and last_shown and phase == "searching":
        idx = parse_selection(text, last_shown)
        if idx is not None:
            selected_car = last_shown[idx]
            session_repo.set_selected_car(conn, session_id, selected_car)
            phase = "selected"
            print(f"[SELECT] #{idx}: {selected_car.get('make')} {selected_car.get('model')}")

    # ── 5.5. CLEAR STALE FILTERS ──
    if phase == "searching":
        _clear_stale_filters(text, slots)

    # ── 6. SEARCH (pre-LLM) ──
    cars, total, url = None, None, None
    pre_filters = {}
    sort = detect_sort(text) if phase == "searching" else None

    if phase == "searching":
        pre_filters = quick_extract(text, slots_to_filters(slots), slots)
        cars, total, url = run_search(conn, pre_filters, sort)
        slots["_last_shown"] = cars
        print(f"[SEARCH] {pre_filters} sort={sort} → {total} total")
    else:
        # LOCKED: only ever the selected car in these phases
        cars = [selected_car] if selected_car else None
        total = 1 if selected_car else 0

    # ── 7. LLM ──
    from app.services.Numbers import hint_line
    missing = missing_filters(slots)
    hints = hint_line(text, missing[0] if missing else None)

    ctx = "\n\n".join(filter(None, [
        build_state_context(phase, slots, selected_car, lang),
        build_catalog_context(slots),
        build_inventory_context_from_cars(cars or []),
    ]))

    action = call_llm(conn, session_id, text, slots, missing, ctx, hints)

    # ── 8. OVERRIDES (searching only — never rewrite filters mid-booking) ──
    if not is_detail and phase == "searching":
        apply_overrides(text, slots, turn)

    # ── 9. RE-SEARCH if filters changed ──
    if phase == "searching":
        post = slots_to_filters(slots)
        if any(str(pre_filters.get(k)) != str(post.get(k)) for k in RESEARCH_KEYS):
            print("[RE-SEARCH] filters changed")
            cars, total, url = run_search(conn, post, sort)
            slots["_last_shown"] = cars

    # ── 10. PHASE TRANSITIONS ──
    inspection = None
    car_before = selected_car

    if phase == "searching":
        cars, total, url, selected_car, phase = handle_searching(
            conn, session_id, action, text, slots, cars, total,
            url, last_shown, selected_car, phase, turn,
        )
    else:
        phase, inspection = handle_inspection(
            conn, session_id, action, text, slots, selected_car, phase,
        )
        # Belt and braces: handle_inspection must never swap the car.
        if selected_car is not car_before:
            print("[GUARD] selected_car changed during inspection — restoring")
            selected_car = car_before
        cars = [selected_car] if selected_car else None
        total = 1 if selected_car else 0

    # ── 11. VALIDATE ──
    reply = (action.get("reply") or "").strip()
    collected = slots.get("_inspection", {})
    reply = run_all_guards(reply, total or 0, cars or [],
                           selected_car, phase, collected, lang) or reply

    if not reply:
        reply = fallback_reply(cars, total or 0, slots, phase, lang)

    # ── 12. PERSIST ──
    _persist(conn, session_id, turn, text, reply, slots)

    ms = int((time.time() - start) * 1000)
    print(f"[DONE] {ms}ms phase={phase} lang={lang} cars={len(cars) if cars else 0}\n{'='*60}\n")

    return TurnOut(
        session_id=session_id, reply=reply, slots=to_schema(slots),
        phase=phase, pakwheels_url=url, cars=cars,
        total_results=total, selected_car=selected_car, inspection=inspection,
    )


def _persist(conn, session_id, turn_index, user_text, reply, slots):
    session_repo.save_slots(conn, session_id, slots)
    session_repo.increment_turn(conn, session_id)
    turn_repo.log_turn(conn, session_id, turn_index, "user", user_text)
    turn_repo.log_turn(conn, session_id, turn_index, "assistant", reply)