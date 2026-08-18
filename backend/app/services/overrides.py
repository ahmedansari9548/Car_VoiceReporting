"""
app/services/overrides.py

Deterministic slot extraction from the user's message.

  quick_extract()   — filter dict BEFORE LLM (does not touch slots)
  apply_overrides() — writes to slots AFTER LLM (user's word beats LLM)
  detect_sort()     — "cheapest" / "most expensive" → sort config

PRICE NOTE: all price parsing goes through app.services.prices.parse_price().
Numbers.py is NOT used for prices — it returns 1 for "1 karod".
"""

import re
import difflib
from datetime import datetime

from app.core.constants import SOURCE_SAID, SOURCE_DERIVED
from app.core.utils import slot_value
from app.services.catalog import resolve_model
from app.services.prices import parse_price


# ═══════════════════════════════════════════════════════════════
# LOOKUP TABLES
# ═══════════════════════════════════════════════════════════════

_MODELS = {
    "corolla": ("Toyota", "Corolla"), "civic": ("Honda", "Civic"),
    "honda city": ("Honda", "City"), "cultus": ("Suzuki", "Cultus"),
    "alto": ("Suzuki", "Alto"), "sportage": ("KIA", "Sportage"),
    "fortuner": ("Toyota", "Fortuner"), "tucson": ("Hyundai", "Tucson"),
    "yaris": ("Toyota", "Yaris"), "vitz": ("Toyota", "Vitz"),
    "swift": ("Suzuki", "Swift"), "mehran": ("Suzuki", "Mehran"),
    "alsvin": ("Changan", "Alsvin"), "brv": ("Honda", "BR-V"),
    "br-v": ("Honda", "BR-V"), "prius": ("Toyota", "Prius"),
    "aqua": ("Toyota", "Aqua"), "wagon r": ("Suzuki", "Wagon R"),
}

_CITIES = {
    "lahore": "Lahore", "karachi": "Karachi", "islamabad": "Islamabad",
    "rawalpindi": "Rawalpindi", "faisalabad": "Faisalabad",
    "multan": "Multan", "peshawar": "Peshawar",
}

_BODY_TYPES = {
    "suv": "SUV", "sedan": "Sedan", "hatchback": "Hatchback",
    "crossover": "Crossover", "mpv": "MPV", "van": "Mini Van",
    "minivan": "Mini Van", "pickup": "Pick Up", "truck": "Truck",
    "double cabin": "Double Cabin", "coupe": "Convertible",
}

_MAKES = {
    "toyota": "Toyota", "honda": "Honda", "suzuki": "Suzuki",
    "kia": "KIA", "hyundai": "Hyundai", "changan": "Changan",
    "mg": "MG", "proton": "Proton", "daihatsu": "Daihatsu",
    "mitsubishi": "Mitsubishi", "nissan": "Nissan",
}

_NEGATION_WORDS = {"nahi", "nhi", "nahin", "not", "cancel", "instead", "nhin", "na"}
_ALL_CAR_WORDS = list(_MODELS.keys()) + list(_MAKES.keys())

ANY_CITY_PHRASES = [
    "kisi bhi shehr", "kisi shehr", "any city", "all cities", "har shehr",
    "sab shehr", "anywhere", "sab shehron", "kisi bhi city", "har city",
    "kisi bhi shahar", "kisi shahar",
]


# ═══════════════════════════════════════════════════════════════
# "BRAND NEW" CONFIG
# ═══════════════════════════════════════════════════════════════

NEW_CAR_PHRASES = [
    "brand new", "brandnew", "bilkul nai", "bilkul naya", "bilkul new",
    "naya", "nayi", "nai gaari", "new car", "new gadi", "new gaari",
    "zero meter", "0 meter", "unregistered",
]
NEW_CAR_MAX_AGE_YEARS = 2
NEW_CAR_MAX_MILEAGE = 25_000


# ═══════════════════════════════════════════════════════════════
# SORT DETECTION
# ═══════════════════════════════════════════════════════════════

_EXPENSIVE_WORDS = {
    "mahangi", "mehngi", "mehnga", "expensive", "costly",
    "qeemti", "kimti", "highest", "مہنگی", "قیمتی",
}
_CHEAP_WORDS = {
    "sasti", "sasta", "cheap", "cheapest", "muft", "affordable",
    "lowest", "سستی", "سستا",
}
_SUPERLATIVE_WORDS = {"sabse", "most", "sab", "least", "cheapest", "سب", "سبسے"}


def detect_sort(text: str) -> dict | None:
    """Returns sort config or None. single=True → return one car, not a list."""
    tokens = _tokens(text)
    lower = text.lower()
    is_superlative = bool(tokens & _SUPERLATIVE_WORDS) or "cheapest" in lower

    if tokens & _EXPENSIVE_WORDS:
        return {"key": "price", "order": "desc", "single": is_superlative}
    if tokens & _CHEAP_WORDS or "cheapest" in lower:
        return {"key": "price", "order": "asc", "single": is_superlative}
    return None


# ═══════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════

def apply_overrides(text: str, slots: dict, turn_index: int) -> None:
    """Write extracted values into slots. Runs AFTER the LLM."""
    lower = text.lower()
    tokens = _tokens(text)

    _override_price(text, slots, turn_index)
    _override_mileage(lower, slots, turn_index)
    _override_new_car(lower, slots, turn_index)
    _override_year(lower, slots, turn_index)
    _override_city(lower, slots, turn_index)
    _override_make(lower, tokens, slots, turn_index)
    _override_model(lower, slots, turn_index)
    _override_transmission(tokens, slots, turn_index)
    _override_body_type(tokens, slots, turn_index)
    _derive_body_type(slots, turn_index)


def quick_extract(text: str, existing: dict, session_slots: dict) -> dict:
    """Build the filter dict for the pre-LLM search. Never touches slots."""
    lower = text.lower()
    tokens = _tokens(text)
    f = dict(existing)

    city = _find_city(lower)
    if city:
        f["city"] = city

    if not _match_model(lower, f):
        _fuzzy_match(lower, f)

    if "model" not in f:
        for kw, mk in _MAKES.items():
            if kw in tokens:
                f["make"] = mk
                break

    if "automatic" in tokens:
        f["transmission"] = "Automatic"
    elif "manual" in tokens:
        f["transmission"] = "Manual"

    for kw, bt in _BODY_TYPES.items():
        if kw in tokens:
            f["body_type"] = bt
            break

    # PRICE — authoritative parser, not Numbers.py
    p_min, p_max = parse_price(text)
    if p_min is not None:
        f["price_min"] = p_min
    if p_max is not None:
        f["price_max"] = p_max

    mil = _parse_mileage(lower)
    if mil is not None:
        f["mileage_max"] = mil

    yr = _parse_year_min(lower)
    if yr:
        f["year_min"] = yr

    if _wants_new(lower):
        now = datetime.now().year
        f["year_min"] = max(f.get("year_min", 0), now - NEW_CAR_MAX_AGE_YEARS)
        f["mileage_max"] = min(f.get("mileage_max", NEW_CAR_MAX_MILEAGE), NEW_CAR_MAX_MILEAGE)

    return f


# ═══════════════════════════════════════════════════════════════
# PARSERS
# ═══════════════════════════════════════════════════════════════

def _tokens(text):
    return set(re.findall(r"\w+", text.lower()))


def _safe_int(val):
    """Convert to int without crashing on strings like '1 crore'."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return int(val)
    try:
        return int(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        m = re.search(r"(\d+)", str(val))
        return int(m.group(1)) if m else None


def _match_model(lower, f):
    for kw, (mk, md) in _MODELS.items():
        if kw in lower:
            f["make"], f["model"] = mk, md
            return True
    return False


def _fuzzy_match(lower, f):
    for word in re.findall(r"\w{4,}", lower):
        close = difflib.get_close_matches(word, _ALL_CAR_WORDS, n=1, cutoff=0.7)
        if close:
            m = close[0]
            if m in _MODELS:
                f["make"], f["model"] = _MODELS[m]
            elif m in _MAKES:
                f["make"] = _MAKES[m]
            return


def _parse_mileage(lower):
    m = re.search(
        r"(\d+(?:\.\d+)?)\s*(lakh|lac|hazaar|hazar|thousand|k)\s*(?:km|kilometer|kilometre)",
        lower,
    )
    if m:
        num = float(m.group(1))
        return int(num * 100_000) if m.group(2) in ("lakh", "lac") else int(num * 1_000)

    m = re.search(r"(\d[\d,]*)\s*(k)?\s*(?:km|kilometer|kilometre|kilo)", lower)
    if not m:
        return None
    raw = m.group(1).replace(",", "")
    try:
        val = int(raw)
    except ValueError:
        return None
    if m.group(2) == "k":
        val *= 1_000
    return val


def _parse_year_min(lower):
    m = re.search(
        r"(20\d{2})\s*(?:ke baad|se upar|se oper|or newer|and newer|onwards|ya baad)", lower
    )
    if m:
        return int(m.group(1))
    m = re.search(r"(?:after|baad|since)\s*(20\d{2})", lower)
    return int(m.group(1)) if m else None


def _wants_new(lower):
    return any(p in lower for p in NEW_CAR_PHRASES)


def _find_city(lower):
    if any(p in lower for p in ANY_CITY_PHRASES):
        return "all"
    found = []
    for kw, val in _CITIES.items():
        pos = lower.find(kw)
        if pos != -1:
            after = lower[pos + len(kw):].strip().split()
            negated = bool(after) and after[0] in _NEGATION_WORDS
            found.append((pos, val, negated))
    ok = [f for f in found if not f[2]]
    return ok[-1][1] if ok else None


# ═══════════════════════════════════════════════════════════════
# SLOT WRITERS
# ═══════════════════════════════════════════════════════════════

def _s(slots, key, val, ti, conf=0.95, src=SOURCE_SAID):
    slots[key] = {"value": val, "source": src, "confidence": conf, "turn": ti}


def _override_price(text, slots, ti):
    """Uses the authoritative parser. Handles '1 karod', ranges, and rejects phones."""
    p_min, p_max = parse_price(text)

    if p_min is not None:
        old = _safe_int(slot_value(slots, "price_min"))
        if old != p_min:
            _s(slots, "price_min", p_min, ti)
            print(f">>> PRICE MIN: {p_min:,}")

    if p_max is not None:
        old = _safe_int(slot_value(slots, "price_max"))
        if old != p_max:
            _s(slots, "price_max", p_max, ti)
            print(f">>> PRICE MAX: {p_max:,}")


def _override_mileage(lower, slots, ti):
    m = _parse_mileage(lower)
    if m is not None:
        old = _safe_int(slot_value(slots, "mileage_max"))
        if old is None or old != m:
            _s(slots, "mileage_max", m, ti)


def _override_new_car(lower, slots, ti):
    if not _wants_new(lower):
        return
    now = datetime.now().year
    yr = now - NEW_CAR_MAX_AGE_YEARS
    ey = _safe_int(slot_value(slots, "year_min"))
    if ey is None or ey < yr:
        _s(slots, "year_min", yr, ti, src=SOURCE_DERIVED)
    em = _safe_int(slot_value(slots, "mileage_max"))
    if em is None or em > NEW_CAR_MAX_MILEAGE:
        _s(slots, "mileage_max", NEW_CAR_MAX_MILEAGE, ti, src=SOURCE_DERIVED)


def _override_year(lower, slots, ti):
    yr = _parse_year_min(lower)
    if yr:
        _s(slots, "year_min", yr, ti)


def _override_city(lower, slots, ti):
    c = _find_city(lower)
    if c and slot_value(slots, "city") != c:
        _s(slots, "city", c, ti)


def _override_make(lower, tokens, slots, ti):
    model_mentioned = any(kw in lower for kw in _MODELS)
    for kw, mk in _MAKES.items():
        if kw in tokens and not model_mentioned and slot_value(slots, "make") != mk:
            _s(slots, "make", mk, ti)
            slots.pop("model", None)
            return
    for word in re.findall(r"\w{4,}", lower):
        close = difflib.get_close_matches(word, list(_MAKES.keys()), n=1, cutoff=0.7)
        if close and not model_mentioned:
            _s(slots, "make", _MAKES[close[0]], ti, 0.8)
            slots.pop("model", None)
            return


def _override_model(lower, slots, ti):
    mentioned = []
    for kw, (mk, md) in _MODELS.items():
        pos = lower.find(kw)
        if pos != -1:
            after = lower[pos + len(kw):].strip().split()
            neg = bool(after) and after[0] in _NEGATION_WORDS
            mentioned.append((mk, md, neg))

    if not mentioned:
        for word in re.findall(r"\w{4,}", lower):
            close = difflib.get_close_matches(word, list(_MODELS.keys()), n=1, cutoff=0.7)
            if close:
                mk, md = _MODELS[close[0]]
                mentioned.append((mk, md, False))
                break

    ok = [m for m in mentioned if not m[2]]
    if ok:
        mk, md, _ = ok[-1]
        if slot_value(slots, "model") != md:
            _s(slots, "make", mk, ti)
            _s(slots, "model", md, ti)


def _override_transmission(tokens, slots, ti):
    if "automatic" in tokens:
        _s(slots, "transmission", "Automatic", ti)
    elif "manual" in tokens:
        _s(slots, "transmission", "Manual", ti)


def _override_body_type(tokens, slots, ti):
    for kw, bt in _BODY_TYPES.items():
        if kw in tokens:
            if slot_value(slots, "body_type") != bt:
                _s(slots, "body_type", bt, ti)
            return


def _derive_body_type(slots, ti):
    mv = slot_value(slots, "model")
    bt = slots.get("body_type")
    user_said = isinstance(bt, dict) and bt.get("source") == SOURCE_SAID
    if mv and not user_said:
        info = resolve_model(mv)
        if info and info.get("body_type"):
            _s(slots, "body_type", info["body_type"], ti, src=SOURCE_DERIVED)