"""
app/services/tts_normalize.py

Normalizes LLM reply text before it is sent to TTS.

Problems this solves:
  1. Abbreviations like BR-V, VXR, GLi, AGS, SUV are read letter-by-letter.
  2. Raw numbers like 3500000 or Rs 3,500,000 are read as digits.
  3. Prices should be spoken as "35 lakh" not "thirty five hundred thousand".
  4. Model year ranges like "2020-2023" cause pause issues.

This module is intentionally simple / regex-based — no LLM needed here.
"""

from __future__ import annotations

import re


# ---------------------------------------------------------------------------
# Abbreviation expansion table
# Keys are the patterns as they appear in LLM output.
# Values are the TTS-safe replacements (spaced letters or full words).
# ---------------------------------------------------------------------------
ABBREVIATION_MAP: dict[str, str] = {
    # Car variant abbreviations — space-separate letters so TTS spells them
    r"\bBR-V\b": "B R V",
    r"\bBRV\b": "B R V",
    r"\bVXR\b": "V X R",
    r"\bVXL\b": "V X L",
    r"\bGLi\b": "G L i",
    r"\bGLI\b": "G L I",
    r"\bXLi\b": "X L i",
    r"\bXLI\b": "X L I",
    r"\bAGS\b": "A G S",
    r"\bCVT\b": "C V T",
    r"\bEFI\b": "E F I",
    r"\bABS\b": "A B S",
    r"\bAC\b": "A C",
    # Body types — spoken as words, not acronyms
    r"\bSUV\b": "es yu vi",
    r"\bMPV\b": "em pi vi",
    r"\bCUV\b": "C U V",
    # Fuel / tech
    r"\bCNG\b": "C N G",
    r"\bLPG\b": "L P G",
    r"\bHEV\b": "H E V",
    r"\bBEV\b": "B E V",
    # Currency / units
    r"\bPKR\b": "rupay",
    r"\bRs\.\b": "rupay",
    r"\bRs\b": "rupay",
    r"\bkm\b": "kilometre",
    r"\bKM\b": "kilometre",
    r"\bkms\b": "kilometre",
    r"\bcc\b": "c c",
    r"\bCC\b": "c c",
}

# ---------------------------------------------------------------------------
# Price / number → spoken form
# ---------------------------------------------------------------------------

def _number_to_urdu_price(value: int) -> str:
    """
    Convert an integer rupee amount to Roman Urdu spoken form.
    Examples:
      3500000  → "35 lakh"
      10200000 → "1 crore 2 lakh"
      150000   → "1 lakh 50 hazaar"
      50000    → "50 hazaar"
    """
    crore = value // 10_000_000
    remainder = value % 10_000_000
    lakh = remainder // 100_000
    remainder2 = remainder % 100_000
    hazaar = remainder2 // 1_000

    parts = []
    if crore:
        parts.append(f"{crore} crore")
    if lakh:
        parts.append(f"{lakh} lakh")
    if hazaar and not crore:  # only include hazaar if no crore (avoids verbosity)
        parts.append(f"{hazaar} hazaar")

    return " ".join(parts) if parts else str(value)


def _replace_price_patterns(text: str) -> str:
    """
    Replace Rs X,XXX,XXX or raw large numbers that look like prices
    with spoken Urdu form.
    """
    # Match "Rs 3,500,000" or "Rs. 3500000" or "Rs3500000"
    def _rs_replacer(m: re.Match) -> str:
        raw = m.group(2).replace(",", "")
        try:
            val = int(raw)
            return _number_to_urdu_price(val) + " rupay"
        except ValueError:
            return m.group(0)

    text = re.sub(
        r"(Rs\.?\s*)([\d,]{6,})",
        _rs_replacer,
        text,
        flags=re.IGNORECASE,
    )

    # Match standalone large numbers that are clearly prices (>= 100,000 and look like money)
    # Only replace if followed by "rupay/rupees" or preceded by price context
    def _bare_price_replacer(m: re.Match) -> str:
        raw = m.group(0).replace(",", "")
        try:
            val = int(raw)
            if val >= 100_000:
                return _number_to_urdu_price(val)
        except ValueError:
            pass
        return m.group(0)

    # Replace comma-formatted numbers like 3,500,000
    text = re.sub(r"\b\d{1,3}(?:,\d{3}){2,}\b", _bare_price_replacer, text)

    return text


def _replace_year_ranges(text: str) -> str:
    """Convert '2020-2023' to '2020 to 2023' so TTS doesn't read the dash as minus."""
    return re.sub(r"(\b20\d{2})-(\b20\d{2})", r"\1 to \2", text)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def normalize_for_tts(text: str) -> str:
    """
    Normalize an LLM reply string for TTS playback.

    Should be called on `reply` before returning from process_turn()
    and before injecting into the user_message context.

    Applies in order:
      1. Abbreviation expansion
      2. Price/number conversion
      3. Year range dashes
    """
    if not text:
        return text

    # 1. Abbreviations
    for pattern, replacement in ABBREVIATION_MAP.items():
        text = re.sub(pattern, replacement, text)

    # 2. Price patterns
    text = _replace_price_patterns(text)

    # 3. Year ranges
    text = _replace_year_ranges(text)

    return text
