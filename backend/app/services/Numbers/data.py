"""
app/services/Numbers/data.py

Pure lexicon and constants for the Roman Urdu number parser. No logic lives
here — that's parser.py. This file exists so the word lists (which grow
often, as new spellings turn up) are separate from the scanning logic
(which should change rarely).
"""
from __future__ import annotations

from typing import Literal

Unit = Literal["price", "mileage", "year", "cc", "unknown"]

# ---------------------------------------------------------------------------
# Lexicon
# ---------------------------------------------------------------------------

# Roman Urdu numerals 1-100. Spelling is not standardised in Pakistan, so the
# common variants are all mapped to the same value. Add freely -- this dict is
# the single place new spellings belong.
WORD_NUMBERS: dict[str, float] = {
    # 0-10
    "sifar": 0, "zero": 0,
    "ek": 1, "aik": 1, "one": 1,
    "do": 2, "two": 2,
    "teen": 3, "three": 3,
    "chaar": 4, "char": 4, "four": 4,
    "paanch": 5, "panch": 5, "five": 5,
    "chay": 6, "che": 6, "chhay": 6, "six": 6,
    "saat": 7, "seven": 7,
    "aath": 8, "ath": 8, "eight": 8,
    "nau": 9, "no": 9, "nine": 9,
    "das": 10, "dus": 10, "ten": 10,
    # 11-20
    "gyarah": 11, "gyara": 11, "barah": 12, "bara": 12,
    "terah": 13, "tera": 13, "chodah": 14, "chauda": 14,
    "pandrah": 15, "pandra": 15, "solah": 16, "sola": 16,
    "satrah": 17, "satra": 17, "atharah": 18, "athara": 18,
    "unnees": 19, "unees": 19, "bees": 20, "bis": 20,
    # 21-30
    "ikkees": 21, "ikees": 21, "baees": 22, "bais": 22,
    "teiees": 23, "teis": 23, "chobees": 24, "chobis": 24,
    "pachees": 25, "pachis": 25, "chabees": 26, "chabis": 26,
    "sataees": 27, "satais": 27, "athaees": 28, "athais": 28,
    "unattees": 29, "tees": 30, "tis": 30,
    # 31-40
    "ikattees": 31, "battees": 32, "batees": 32,
    "taintees": 33, "chauntees": 34,
    "paintees": 35, "pentees": 35, "chattees": 36,
    "saintees": 37, "athtees": 38, "untalees": 39,
    "chalees": 40, "chalis": 40, "chaalis": 40,
    # 41-50
    "iktalees": 41, "bayalees": 42, "taintalees": 43, "chawalees": 44,
    "paintalees": 45, "paintalis": 45, "pentalees": 45,
    "chayalees": 46, "saintalees": 47, "athtalees": 48,
    "unchaas": 49, "pachaas": 50, "pachas": 50, "pachass": 50,
    # 51-60
    "ikyawan": 51, "bawan": 52, "tirpan": 53, "chauwan": 54,
    "pachpan": 55, "chappan": 56, "satawan": 57, "athawan": 58,
    "unsath": 59, "saath": 60, "sath": 60,
    # 61-70
    "iksath": 61, "basath": 62, "tirsath": 63, "chausath": 64,
    "painsath": 65, "pensath": 65, "chiyasath": 66, "sarsath": 67,
    "arsath": 68, "unhattar": 69, "sattar": 70,
    # 71-80
    "ikhattar": 71, "bahattar": 72, "tihattar": 73, "chauhattar": 74,
    "pachhattar": 75, "pachattar": 75, "chihattar": 76, "satattar": 77,
    "athhattar": 78, "unasi": 79, "assi": 80, "asi": 80,
    # 81-90
    "ikyasi": 81, "bayasi": 82, "tirasi": 83, "chaurasi": 84,
    "pachasi": 85, "chiyasi": 86, "satasi": 87, "athasi": 88,
    "nawasi": 89, "nabbe": 90, "nabey": 90,
    # 91-99
    "ikyanwe": 91, "banwe": 92, "tiranwe": 93, "chauranwe": 94,
    "pachanwe": 95, "chiyanwe": 96, "satanwe": 97, "athanwe": 98,
    "ninyanwe": 99,
    # standalone fraction words (these are values, not prefixes)
    "aadha": 0.5, "adha": 0.5, "half": 0.5,
    "derh": 1.5, "dedh": 1.5,
    "dhai": 2.5, "dhaai": 2.5, "dahi": 2.5,
}

FRACTION_PREFIXES: dict[str, float] = {
    "sawa": +0.25,      # quarter past
    "sawwa": +0.25,
    "saarhe": +0.5,     # half past
    "sarhe": +0.5,
    "saray": +0.5,
    "pauney": -0.25,    # quarter to
    "pone": -0.25,
    "paune": -0.25,
}

MULTIPLIERS: dict[str, int] = {
    "sau": 100, "hundred": 100,
    "hazaar": 1_000, "hazar": 1_000, "hazzar": 1_000,
    "thousand": 1_000, "k": 1_000,
    "lakh": 100_000, "lac": 100_000, "lakhs": 100_000, "lacs": 100_000,
    "crore": 10_000_000, "karor": 10_000_000, "cr": 10_000_000,
}

# Context keywords. Presence of any of these near a number pins its unit.
MILEAGE_WORDS = {
    "km", "kms", "kilometre", "kilometres", "kilometer", "kilometers",
    "chali", "chala", "chalay", "chali_hai", "meter", "mileage",
    "driven", "running", "odometer",
}
PRICE_WORDS = {
    "price", "demand", "demanding", "maang", "mang", "maangta", "maang_raha",
    "rupay", "rupees", "rs", "pkr", "keemat", "qeemat", "budget",
    "bech", "bechni", "bechna", "afford", "deni", "dunga", "lunga", "cost",
    "lakh", "lac", "lakhs", "lacs", "crore", "crores", "cr",
    "kam", "tak", "range", "under", "below", "se", "andar", "niche", "neeche",
}
YEAR_WORDS = {"model", "saal", "year", "make"}
CC_WORDS = {"cc", "engine", "capacity"}

# Slot name -> unit, used when the assistant just asked a targeted question.
EXPECTING_TO_UNIT: dict[str, Unit] = {
    "mileage_km": "mileage",
    "price_pkr": "price",
    "price_min": "price",
    "price_max": "price",
    "model_year": "year",
    "year_min": "year",
    "engine_capacity_cc": "cc",
}

YEAR_MIN, YEAR_MAX = 1950, 2030

# A value outside these bounds for its unit means we probably heard a
# shorthand -- "paintalees" meaning "paintalees hazaar". We never scale it
# silently; parser.py lowers confidence instead so the assistant asks.
PLAUSIBLE: dict[Unit, tuple[float, float]] = {
    "price":   (50_000, 500_000_000),
    "mileage": (1_000, 1_500_000),
    "cc":      (50, 8_000),
    "year":    (YEAR_MIN, YEAR_MAX),
}
