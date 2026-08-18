"""
app/services/guards.py

Deterministic validation guards. Each takes the LLM's reply and returns
a corrected reply (str) or None (reply is fine).

Run AFTER the LLM. The first guard that fires wins.
"""

from __future__ import annotations

from app.services.overrides import _MODELS as CAR_MODELS
from app.services.helpers import claims_no_cars, override_no_cars

# ═══════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════

INSPECTION_FIELDS = ["name", "phone", "date", "time"]

INSPECTION_QUESTIONS = {
    "en": {
        "name": "What name should I book the inspection under?",
        "phone": "What's your phone number?",
        "date": "Which date works for you?",
        "time": "What time suits you?",
    },
    "ur": {
        "name": "انسپکشن کس نام سے بک کریں؟",
        "phone": "اپنا فون نمبر بتائیں۔",
        "date": "کون سی تاریخ آپ کے لیے ٹھیک ہے؟",
        "time": "کس وقت آنا چاہیں گے؟",
    },
}

STALLING_PHRASES = [
    "any more information", "more details about", "anything else about",
    "any other information", "any specific questions", "let me know if",
    "aur koi maloomat", "aur kuch janna", "کچھ اور معلومات",
    "اور کیا جاننا", "کوئی اور سوال",
]

FIELD_KEYWORDS = {
    "name": ["name", "نام"],
    "phone": ["phone", "number", "نمبر", "فون"],
    "date": ["date", "day", "تاریخ", "دن"],
    "time": ["time", "وقت"],
}


# ═══════════════════════════════════════════════════════════════
# GUARDS
# ═══════════════════════════════════════════════════════════════

def guard_no_false_empty(reply: str, total: int, cars: list) -> str | None:
    """LLM claimed no cars exist, but they do."""
    if total and total > 0 and claims_no_cars(reply):
        print("[GUARD] false 'no cars' claim")
        return override_no_cars(total, (cars or [])[:3])
    return None


def guard_wrong_car(reply: str, selected_car: dict | None, language: str) -> str | None:
    """LLM talked about a different car than the selected one."""
    if not selected_car or not reply:
        return None

    lower = reply.lower()
    selected_model = (selected_car.get("model", "") or "").lower()

    for kw in CAR_MODELS:
        if kw in lower and kw != selected_model:
            print(f"[GUARD] reply mentioned '{kw}', selected is '{selected_model}'")
            c = selected_car
            if language == "ur":
                return (
                    f"آپ نے {c.get('year')} {c.get('make')} {c.get('model')} "
                    f"{c.get('variant', '')} منتخب کی ہے — Rs {c.get('price', 0):,}، "
                    f"{c.get('city')}۔ کیا آپ اس کی PakWheels انسپکشن بک کرنا چاہیں گے؟"
                )
            return (
                f"You've selected the {c.get('year')} {c.get('make')} {c.get('model')} "
                f"{c.get('variant', '')} — Rs {c.get('price', 0):,} in {c.get('city')}. "
                f"Would you like to book a PakWheels inspection?"
            )
    return None


def guard_inspection_repeat(reply: str, phase: str, collected: dict, language: str) -> str | None:
    """During inspection: LLM re-asked a collected field or stalled."""
    if phase != "inspection":
        return None

    missing = [f for f in INSPECTION_FIELDS if not collected.get(f)]
    if not missing:
        return None

    lower = reply.lower()
    next_field = missing[0]

    # Re-asked for a field we already have?
    for field, keywords in FIELD_KEYWORDS.items():
        if collected.get(field) and any(k in lower for k in keywords):
            print(f"[GUARD] re-asked for collected '{field}'")
            return INSPECTION_QUESTIONS[language][next_field]

    # Stalled instead of asking the next field?
    if any(p in lower for p in STALLING_PHRASES):
        print(f"[GUARD] stalled, forcing '{next_field}'")
        return INSPECTION_QUESTIONS[language][next_field]

    # Didn't ask for the missing field at all?
    if not any(k in lower for k in FIELD_KEYWORDS[next_field]):
        print(f"[GUARD] didn't ask for '{next_field}', forcing it")
        return INSPECTION_QUESTIONS[language][next_field]

    return None


def guard_selected_stalling(reply: str, phase: str, selected_car: dict | None, language: str) -> str | None:
    """In selected phase: LLM keeps asking 'need more info?' instead of offering inspection."""
    if phase != "selected" or not selected_car or not reply:
        return None

    lower = reply.lower()

    # Don't override if reply is providing actual car facts (price, mileage, year, city)
    has_facts = any(k in lower for k in ["rs", "rupay", "km", "lac", "lakh", "lahore", "karachi", "islamabad", "automatic", "manual"])
    if has_facts:
        return None

    if any(p in lower for p in STALLING_PHRASES) and "inspection" not in lower:
        print("[GUARD] stalling in selected phase")
        if language == "ur":
            return "کیا آپ اس گاڑی کی PakWheels انسپکشن بک کرنا چاہیں گے؟"
        return "Would you like to book a PakWheels inspection for this car?"
    return None


def run_all_guards(reply: str, total: int, cars: list,
                   selected_car: dict | None, phase: str,
                   collected: dict, language: str) -> str:
    """Run every guard. First hit wins. Returns original reply if all pass."""
    for result in [
        guard_no_false_empty(reply, total or 0, cars or []),
        guard_wrong_car(reply, selected_car if phase != "searching" else None, language),
        guard_inspection_repeat(reply, phase, collected, language),
        guard_selected_stalling(reply, phase, selected_car, language),
    ]:
        if result:
            return result
    return reply