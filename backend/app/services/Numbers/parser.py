"""
WHY THIS IS DETERMINISTIC AND NOT AN LLM JOB
--------------------------------------------
Every other component fails loudly. If the catalog can't resolve "Oriel",
we ask a question. If the LLM returns bad JSON, we retry. But if a price is
misparsed, nothing complains -- a wrong number simply goes into a live ad.
That is the only silent, expensive failure in this system, so it gets code
with assertions rather than a model with a temperature.

It also removes the weakest area of an open-weight model (Roman Urdu
numerals) from the critical path. The LLM never has to do arithmetic; it
receives pre-parsed hints and only has to decide which slot they belong to.

USAGE
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from .data import (
    Unit,
    WORD_NUMBERS,
    FRACTION_PREFIXES,
    MULTIPLIERS,
    MILEAGE_WORDS,
    PRICE_WORDS,
    YEAR_WORDS,
    CC_WORDS,
    EXPECTING_TO_UNIT,
    YEAR_MIN,
    YEAR_MAX,
    PLAUSIBLE,
)

@dataclass
class ParsedNumber:
    raw: str            # the exact text span that produced this
    value: int          # normalised integer value
    unit: Unit          # what we think it refers to
    confidence: float   # 0.0 - 1.0
    start: int          # token index, for debugging
    end: int

    @property
    def is_ambiguous(self) -> bool:
        return self.unit == "unknown" or self.confidence < 0.5


# ---------------------------------------------------------------------------
# Tokenisation
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9.,]*", re.IGNORECASE)


def _tokenize(text: str) -> list[str]:
    """Lowercase, strip punctuation, split '45k' into '45' + 'k'."""
    raw = _TOKEN_RE.findall(text.lower())
    out: list[str] = []
    for tok in raw:
        tok = tok.strip(".,")
        if not tok:
            continue
        m = re.fullmatch(r"(\d+(?:\.\d+)?)(k|cc)", tok)
        if m:
            out.extend([m.group(1), m.group(2)])
        else:
            out.append(tok)
    return out


def _as_number(token: str) -> Optional[float]:
    """A single token's numeric value, digits or Roman Urdu word."""
    cleaned = token.replace(",", "")
    if re.fullmatch(r"\d+(?:\.\d+)?", cleaned):
        return float(cleaned)
    return WORD_NUMBERS.get(token)


# ---------------------------------------------------------------------------
# Core scanner
# ---------------------------------------------------------------------------

def _scan_expression(tokens: list[str], i: int) -> Optional[tuple[float, int, Unit]]:
    """
    Try to read one number expression starting at index i.
    Returns (value, next_index, forced_unit) or None.
    """
    start = i
    fraction = 0.0

    if tokens[i] in FRACTION_PREFIXES:
        fraction = FRACTION_PREFIXES[tokens[i]]
        i += 1
        if i >= len(tokens):
            return None

    core = _as_number(tokens[i])
    if core is None:
        # "sawa crore" / "saarhe lakh" -- no explicit core, implied 1.
        if tokens[i] in MULTIPLIERS and fraction != 0.0:
            core = 1.0
        else:
            return None
    else:
        i += 1

    # "ek sau bees" = 120  (small number + sau + remainder)
    if i < len(tokens) and tokens[i] == "sau" and core < 10:
        core *= 100
        i += 1
        if i < len(tokens):
            nxt = _as_number(tokens[i])
            if nxt is not None and nxt < 100 and not _is_multiplier_at(tokens, i + 1):
                core += nxt
                i += 1

    core += fraction

    multiplier = 1
    if i < len(tokens) and tokens[i] in MULTIPLIERS:
        multiplier = MULTIPLIERS[tokens[i]]
        i += 1
    elif core < 100 and i < len(tokens) and tokens[i] in {"se", "to", "say", "tak", "and"}:
        if i + 1 < len(tokens):
            nxt_val = _as_number(tokens[i + 1])
            if nxt_val is not None and i + 2 < len(tokens) and tokens[i + 2] in MULTIPLIERS:
                multiplier = MULTIPLIERS[tokens[i + 2]]

    value = core * multiplier

    # Year said as "do hazaar bees" = 2020. Must be checked BEFORE the
    # lakh-remainder rule, or 2020 becomes 22,000.
    if multiplier == 1_000 and core in (1, 2) and i < len(tokens):
        nxt = _as_number(tokens[i])
        if nxt is not None and nxt < 100:
            candidate = value + nxt
            if YEAR_MIN <= candidate <= YEAR_MAX:
                return candidate, i + 1, "year"

    # "22 lac 50" = 2,250,000 -- trailing remainder is thousands.
    # Only for lakh/crore; "45 hazaar 20" is not a thing.
    if multiplier >= 100_000 and i < len(tokens):
        nxt = _as_number(tokens[i])
        if nxt is not None and nxt < 100:
            follows_hazaar = (
                i + 1 < len(tokens)
                and tokens[i + 1] in MULTIPLIERS
                and MULTIPLIERS[tokens[i + 1]] == 1_000
            )
            if follows_hazaar or not _is_multiplier_at(tokens, i + 1):
                value += nxt * 1_000
                i += 2 if follows_hazaar else 1

    # A bare 4-digit number in range is almost always a model year.
    forced: Unit = "unknown"
    if multiplier == 1 and fraction == 0.0 and float(value).is_integer():
        if YEAR_MIN <= value <= YEAR_MAX and re.fullmatch(r"\d{4}", tokens[start]):
            forced = "year"

    return value, i, forced


def _is_multiplier_at(tokens: list[str], i: int) -> bool:
    return 0 <= i < len(tokens) and tokens[i] in MULTIPLIERS


# ---------------------------------------------------------------------------
# Unit inference
# ---------------------------------------------------------------------------


def _plausible(unit: Unit, value: float) -> bool:
    bounds = PLAUSIBLE.get(unit)
    return bounds is None or bounds[0] <= value <= bounds[1]


def _infer_unit(
    tokens: list[str],
    start: int,
    end: int,
    value: float,
    forced: Unit,
    expecting: Optional[str],
) -> tuple[Unit, float]:
    """Decide what this number refers to, and how sure we are."""
    window = set(tokens[max(0, start - 3): min(len(tokens), end + 4)])
    expr_tokens = set(tokens[start:end])

    def settle(unit: Unit, confidence: float) -> tuple[Unit, float]:
        # Right unit, implausible magnitude -> keep the unit, force a confirm.
        if not _plausible(unit, value):
            return unit, 0.40
        return unit, confidence

    # Any expression explicitly containing monetary multipliers without mileage words is price
    if (expr_tokens & {"lakh", "lac", "lakhs", "lacs", "crore", "crores", "cr"}) and not (window & MILEAGE_WORDS):
        return settle("price", 0.95)

    if window & CC_WORDS:
        return settle("cc", 0.95)
    if window & MILEAGE_WORDS:
        return settle("mileage", 0.95)
    if window & PRICE_WORDS:
        return settle("price", 0.95)
    if forced == "year" and (window & YEAR_WORDS):
        return settle("year", 0.97)
    if forced == "year":
        return settle("year", 0.90)

    # No keyword in the sentence -- fall back to whatever the assistant asked.
    if expecting:
        unit = EXPECTING_TO_UNIT.get(expecting)
        if unit:
            return settle(unit, 0.85)

    # Plausible large prices without mileage words
    if value >= 100_000 and not (window & MILEAGE_WORDS):
        return settle("price", 0.90)

    # Deliberately give up. The assistant will ask:
    # "Paintalees hazaar kilometre?"
    return "unknown", 0.40


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse(text: str, expecting: Optional[str] = None) -> list[ParsedNumber]:
    """
    Extract every number expression from an utterance.

    `expecting` is the slot the assistant's last question targeted
    (e.g. "mileage_km"). It only breaks ties -- an explicit keyword in the
    text always wins over it.
    """
    tokens = _tokenize(text)
    results: list[ParsedNumber] = []
    i = 0
    while i < len(tokens):
        scanned = _scan_expression(tokens, i)
        if scanned is None:
            i += 1
            continue
        value, next_i, forced = scanned
        unit, confidence = _infer_unit(tokens, i, next_i, value, forced, expecting)
        results.append(
            ParsedNumber(
                raw=" ".join(tokens[i:next_i]),
                value=int(round(value)),
                unit=unit,
                confidence=round(confidence, 2),
                start=i,
                end=next_i,
            )
        )
        i = next_i
    return results


def hint_line(text: str, expecting: Optional[str] = None) -> str:
    """
    Render parsed numbers as a single line for the LLM prompt.

    The model never does arithmetic -- it just picks which slot each
    pre-computed value belongs to.
    """
    parsed = parse(text, expecting)
    if not parsed:
        return ""
    parts = [f"'{p.raw}' = {p.value} ({p.unit})" for p in parsed]
    return "NUMBER HINTS: " + " | ".join(parts)


def first_of(parsed: list[ParsedNumber], unit: Unit) -> Optional[int]:
    """Convenience: first confident value of a given unit."""
    for p in parsed:
        if p.unit == unit and p.confidence >= 0.5:
            return p.value
    return None
