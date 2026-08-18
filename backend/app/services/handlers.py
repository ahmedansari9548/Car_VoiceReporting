"""
app/services/handlers.py

Input classification: language, greetings, detail requests, frontend messages.
All pure functions — no database access.
"""

from __future__ import annotations

import re

# ═══════════════════════════════════════════════════════════════
# KEYWORD TABLES
# ═══════════════════════════════════════════════════════════════

_GREETINGS = {
    "hello", "hi", "hey", "good morning", "good evening", "good afternoon",
    "thank you", "thanks", "ok", "okay", "yes", "no", "bye", "goodbye",
    "salam", "aoa", "assalamualaikum", "assalam o alaikum",
    "walaikum assalam", "wa alaikum assalam",
    "kya haal hai", "kya haal", "sab theek", "theek hai",
    "shukriya", "ji", "haan", "nahi",
    "allah hafiz", "khuda hafiz",
    "السلام علیکم", "وعلیکم السلام", "شکریہ", "جی", "ہاں", "نہیں",
}

_CAR_WORDS = {
    "corolla", "civic", "alto", "cultus", "sportage", "fortuner",
    "suv", "sedan", "hatchback", "gaari", "car", "lakh", "crore",
    "automatic", "manual", "lahore", "karachi", "islamabad",
    "honda", "toyota", "suzuki", "kia", "hyundai", "changan",
    "گاڑی", "لاکھ", "کروڑ", "چاہیے",
}

# One match = Urdu
_STRONG_URDU = {
    "salam", "aoa", "assalamualaikum", "shukriya", "gaari", "gadi",
    "chahiye", "dikhao", "dikhayen", "batao", "pasand", "wali",
    "dikhaiye", "bataiye", "karwao", "lagwao", "mujhe",
    "khareedni", "bechni", "dekho", "dikhaye", "kimat",
}

# Two or more = Urdu
_WEAK_URDU = {
    "hai", "mein", "main", "theek", "lakh", "bhai",
    "haan", "nahi", "nahin", "nhin", "ji", "aur",
    "kya", "kis", "koi", "bhi", "tum", "isko", "yah", "yeh",
    "padi", "jitni", "sara", "kar", "de", "ho", "le", "na",
    "chahta", "chahti", "janna", "raha", "rahi",
    "wala", "wali", "dekh", "bol", "sun", "bus",
    "achcha", "kuch", "kuchh", "abhi", "tab", "kam", "se",
}

_ENGLISH_MARKERS = {
    "looking", "want", "need", "show", "find", "budget",
    "tell", "about", "which", "what", "where", "please",
}


# ═══════════════════════════════════════════════════════════════
# LANGUAGE
# ═══════════════════════════════════════════════════════════════

def detect_language(text: str) -> str | None:
    """Returns 'ur', 'en', or None (unknown). Single source of truth."""
    if any("\u0600" <= c <= "\u06FF" for c in text):
        return "ur"

    tokens = set(re.findall(r"\w+", text.lower()))

    if tokens & _STRONG_URDU:
        return "ur"
    if len(tokens & _WEAK_URDU) >= 2:
        return "ur"
    if tokens & _ENGLISH_MARKERS:
        return "en"
    return None


# ═══════════════════════════════════════════════════════════════
# MESSAGE CLASSIFICATION
# ═══════════════════════════════════════════════════════════════

def is_greeting(text: str) -> bool:
    cleaned = text.strip().lower().rstrip("!?.،۔")
    return cleaned in _GREETINGS or len(cleaned) <= 3


def has_car_keywords(text: str) -> bool:
    lower = text.lower()
    return any(w in lower for w in _CAR_WORDS)


def is_car_detail_request(text: str) -> bool:
    lower = text.lower()
    return any(p in lower for p in [
        "tell me about this car", "tell me about this", "is car ke baare",
        "ye gaari", "this car", "is gaari", "details", "more about",
        "iske baare", "ye wali batao", "yeh wali batao",
        "اس گاڑی", "اس کے بارے", "تفصیل",
    ])


def parse_ask_ai_message(text: str) -> dict | None:
    """
    Parse the frontend's "Ask AI about this car" message.

    Format:
      "Tell me about this car and answer my questions about it: 2017 Toyota
       Aqua S (id 32), 65000 km, Automatic, White, Lahore, Rs 29.00 lac."

    IMPORTANT: returns car_id so the caller can fetch the FULL row from the
    database (including image_url, which is not in this message).
    """
    pattern = (
        r"(?:tell me about this car|ask ai about this car)[^:]*:\s*"
        r"(\d{4})\s+"                                   # year
        r"(\w+)\s+"                                     # make
        r"(.+?)\s*"                                     # model + variant
        r"\(id\s*(\d+)\)"                               # id
        r",\s*(\d+)\s*km"                               # mileage
        r",\s*(\w+)"                                    # transmission
        r",\s*(\w+)"                                    # color
        r",\s*(\w+)"                                    # city
        r",\s*Rs\s*([\d.]+)\s*(?:lac|lakh|crore)"       # price
    )
    m = re.search(pattern, text, re.IGNORECASE)
    if not m:
        return None

    price_raw = float(m.group(9))
    price = int(price_raw * (10_000_000 if "crore" in text.lower() else 100_000))

    model_variant = m.group(3).strip()
    parts = model_variant.split(None, 1)

    return {
        "car_id": int(m.group(4)),        # ← use this to fetch the full row
        "id": int(m.group(4)),
        "year": int(m.group(1)),
        "make": m.group(2),
        "model": parts[0],
        "variant": parts[1] if len(parts) > 1 else "",
        "mileage": int(m.group(5)),
        "transmission": m.group(6),
        "color": m.group(7),
        "city": m.group(8),
        "price": price,
        "image_url": "",                  # filled in by the caller from DB
        "seller_type": "",
    }


# ═══════════════════════════════════════════════════════════════
# REPLIES
# ═══════════════════════════════════════════════════════════════

def greeting_reply(text: str, language: str = "en") -> str:
    lower = text.strip().lower()

    if language == "ur":
        if any(w in lower for w in ["salam", "aoa", "assalam", "السلام"]):
            return "وعلیکم السلام! کیا آپ گاڑی ڈھونڈ رہے ہیں؟ اپنا بجٹ اور شہر بتائیں۔"
        if any(w in lower for w in ["shukriya", "شکریہ", "thanks"]):
            return "آپ کا شکریہ! کچھ اور مدد چاہیے؟"
        return "جی بتائیں، کیا ڈھونڈ رہے ہیں؟"

    if any(w in lower for w in ["hello", "hi", "hey"]):
        return "Hello! Looking for a car? Tell me your budget, city, and what type of car you want."
    if any(w in lower for w in ["thanks", "thank"]):
        return "You're welcome! Need anything else?"
    return "Hi, what car are you looking for?"