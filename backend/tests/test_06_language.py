"""Test 6: Language matching — reply should match user's language."""

import re


def _is_mostly_english(text):
    """Check if text is mostly ASCII (English)."""
    ascii_chars = sum(1 for c in text if ord(c) < 128)
    return ascii_chars / max(len(text), 1) > 0.85


def _has_urdu_script(text):
    """Check if text contains Urdu/Arabic script characters."""
    return any('\u0600' <= c <= '\u06FF' for c in text)


def test_english_in_english_out(new_chat):
    result, sid = new_chat("Show me automatic cars in Karachi under 30 lakh")
    reply = result["reply"]

    assert _is_mostly_english(reply), \
        f"English input got non-English reply: {reply[:80]}"


def test_roman_urdu_in_roman_urdu_out(new_chat):
    result, sid = new_chat("Karachi mein automatic gaari chahiye 30 lakh tak")
    reply = result["reply"]

    # should NOT be pure English formal, should have some Urdu flavor
    # but should NOT be Urdu script
    assert not _has_urdu_script(reply), \
        f"Roman Urdu input got Urdu script reply: {reply[:80]}"


def test_urdu_script_gets_roman_urdu(new_chat):
    result, sid = new_chat("مجھے لاہور میں گاڑی چاہیے")
    reply = result["reply"]

    # should reply in Roman Urdu, NOT Urdu script
    assert not _has_urdu_script(reply), \
        f"Urdu script input should get Roman Urdu reply, got: {reply[:80]}"
