"""
app/services/prices.py

THE authoritative price parser. One function, used everywhere.

Why this exists:
  Numbers.py returns value=1 for "1 karod" — it reads the digit but not
  the unit. Any code that trusts it stores price_max=1 and finds nothing.
  This module parses the unit itself and never guesses.

Also rejects phone numbers, which look like large integers but are not prices.
"""

from __future__ import annotations

import re

# ═══════════════════════════════════════════════════════════════
# CONFIG — tune these
# ═══════════════════════════════════════════════════════════════

CRORE = 10_000_000
LAKH = 100_000
HAZAAR = 1_000

# A price must fall inside this range to be believable
MIN_VALID_PRICE = 50_000
MAX_VALID_PRICE = 500_000_000

# Unit spellings (Roman + Urdu script)
_CRORE_WORDS = r"crore|croar|karod|karor|karore|kror|کروڑ"
_LAKH_WORDS = r"lakh|lac|lakhs|lacs|lakhon|لاکھ"
_HAZAAR_WORDS = r"hazaar|hazar|hazaro|thousand|ہزار"

# Urdu number words → integer
_URDU_NUMBERS = {
    "aik": 1, "ek": 1, "ik": 1, "one": 1,
    "do": 2, "two": 2,
    "teen": 3, "three": 3,
    "char": 4, "chaar": 4, "four": 4,
    "panch": 5, "paanch": 5, "five": 5,
    "chhe": 6, "che": 6, "chey": 6, "six": 6,
    "saat": 7, "seven": 7,
    "aath": 8, "aat": 8, "eight": 8,
    "nau": 9, "no": 9, "nine": 9,
    "das": 10, "dus": 10, "ten": 10,
    "gyarah": 11, "barah": 12, "terah": 13, "chaudah": 14,
    "pandrah": 15, "solah": 16, "satrah": 17, "athrah": 18,
    "unees": 19, "bees": 20, "bis": 20,
    "ikees": 21, "bayees": 22, "teyees": 23, "chobees": 24,
    "pachees": 25, "pacchees": 25,
    "chabees": 26, "sattayees": 27, "athayees": 28, "untees": 29,
    "tees": 30, "tis": 30,
    "paintees": 35, "paintalees": 45,
    "chalees": 40, "chaalees": 40,
    "pachaas": 50, "pachas": 50,
    "saath": 60, "sath": 60,
    "sattar": 70, "assi": 80, "nabbe": 90, "nabbay": 90,
    "sau": 100, "hundred": 100,
}

# Words that signal an upper bound ("under 30 lakh")
_UPPER_BOUND_WORDS = [
    "se kam", "sy kam", "se neeche", "se niche", "se nichay",
    "below", "under", "less than", "upto", "up to", "tak",
    "max", "maximum", "budget", "andar", "ke andar", "se kum",
]

# Words that signal a lower bound ("above 20 lakh")
_LOWER_BOUND_WORDS = [
    "se upar", "se oper", "se zyada", "above", "over",
    "more than", "at least", "minimum", "se ziada",
]


# ═══════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════

def parse_price(text: str) -> tuple[int | None, int | None]:
    """
    Extract (price_min, price_max) from user text.

    Examples:
      "1 karod"                 → (None, 10000000)
      "ek crore se kam"         → (None, 10000000)
      "30 lakh tak"             → (None, 3000000)
      "20 se 25 lakh"           → (2000000, 2500000)
      "budget 45 lakh"          → (None, 4500000)
      "paintalees lakh"         → (None, 4500000)
      "3500000"                 → (None, 3500000)
      "phone number 123678945"  → (None, None)  ← rejected
      "03218888"                → (None, None)  ← rejected
      "20000 km se kam"         → (None, None)  ← that's mileage, not price
    """
    if not text:
        return None, None

    lower = text.lower()

    # Never parse a price out of a phone/contact context
    if _is_contact_context(lower):
        return None, None

    amounts = _find_all_amounts(lower)
    if not amounts:
        return None, None

    # Range: "20 se 25 lakh" → two amounts
    if len(amounts) >= 2:
        lo, hi = min(amounts), max(amounts)
        if _valid(lo) and _valid(hi) and lo != hi:
            return lo, hi

    value = amounts[0]
    if not _valid(value):
        return None, None

    # Lower bound ("30 lakh se upar")
    if any(w in lower for w in _LOWER_BOUND_WORDS):
        return value, None

    # Default: treat as an upper bound (the common case in car shopping)
    return None, value


def parse_single_price(text: str) -> int | None:
    """Convenience: just the max price, or None."""
    _, hi = parse_price(text)
    return hi


def normalize_price_value(value) -> int | None:
    """
    Convert a single value (possibly a string like "1 crore") to an int.
    Used to sanitize LLM tool output before it reaches slots.
    """
    if value is None:
        return None

    if isinstance(value, (int, float)):
        v = int(value)
        return v if _valid(v) else None

    text = str(value).strip().lower()

    # Plain number, possibly comma-formatted
    plain = text.replace(",", "").replace(" ", "")
    if plain.isdigit():
        v = int(plain)
        return v if _valid(v) else None

    amounts = _find_all_amounts(text)
    if amounts and _valid(amounts[0]):
        return amounts[0]

    return None


# ═══════════════════════════════════════════════════════════════
# INTERNALS
# ═══════════════════════════════════════════════════════════════

def _valid(value: int | None) -> bool:
    return value is not None and MIN_VALID_PRICE <= value <= MAX_VALID_PRICE


def _is_contact_context(lower: str) -> bool:
    """
    True if the text is about a phone number / CNIC / name — anything
    where a big integer is definitely not a price.
    """
    contact_words = [
        "phone", "number", "mobile", "cell", "contact", "whatsapp",
        "naam", "nam ", "name", "cnic", "id card", "شناختی", "نمبر", "فون",
    ]
    return any(w in lower for w in contact_words)


def _find_all_amounts(lower: str) -> list[int]:
    """
    Find every money amount in the text, in order of appearance.
    Skips anything attached to 'km' (that's mileage) or year-like values.
    """
    amounts: list[int] = []

    # Strip mileage phrases so "20000 km" never becomes a price
    cleaned = re.sub(r"\d[\d,.]*\s*(?:k\s*)?(?:km|kilometer|kilometre|kilo)\b", " ", lower)

    # ── 1. digit + unit: "1.5 crore", "30 lakh", "50 hazaar" ──
    for match in re.finditer(
        rf"(\d+(?:\.\d+)?)\s*({_CRORE_WORDS}|{_LAKH_WORDS}|{_HAZAAR_WORDS})",
        cleaned,
    ):
        num = float(match.group(1))
        unit = match.group(2)
        amounts.append(int(num * _unit_multiplier(unit)))

    # ── 2. Urdu word + unit: "ek karod", "paintalees lakh" ──
    for word, num in _URDU_NUMBERS.items():
        for match in re.finditer(
            rf"\b{word}\b\s*({_CRORE_WORDS}|{_LAKH_WORDS}|{_HAZAAR_WORDS})",
            cleaned,
        ):
            amounts.append(int(num * _unit_multiplier(match.group(1))))

    # ── 3. Shared unit across a range: "20 se 25 lakh" ──
    # The "20" has no unit of its own — borrow the one from "25 lakh".
    range_match = re.search(
        rf"(\d+)\s*(?:se|to|say|-|–)\s*(\d+)\s*({_CRORE_WORDS}|{_LAKH_WORDS}|{_HAZAAR_WORDS})",
        cleaned,
    )
    if range_match:
        mult = _unit_multiplier(range_match.group(3))
        amounts = [int(range_match.group(1)) * mult, int(range_match.group(2)) * mult]
        return sorted(amounts)

    if amounts:
        return amounts

    # ── 4. Bare large number: "3500000" or "3,500,000" ──
    for match in re.finditer(r"\b(\d[\d,]{4,})\b", cleaned):
        raw = match.group(1).replace(",", "")
        # Reject leading-zero numbers (phone numbers: 0321…)
        if raw.startswith("0"):
            continue
        # Reject 4-digit values that look like years
        if len(raw) == 4 and raw.startswith(("19", "20")):
            continue
        try:
            value = int(raw)
        except ValueError:
            continue
        if _valid(value):
            amounts.append(value)

    return amounts


def _unit_multiplier(unit: str) -> int:
    unit = unit.lower()
    if re.fullmatch(_CRORE_WORDS, unit):
        return CRORE
    if re.fullmatch(_LAKH_WORDS, unit):
        return LAKH
    return HAZAAR