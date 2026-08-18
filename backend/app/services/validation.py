"""
app/services/validation.py

Validates buyer filter values against allowed enums and sane ranges.
"""

from __future__ import annotations

from app.core.constants import (
    ASSEMBLIES, BODY_TYPES, COLORS, ENGINE_TYPES, TRANSMISSIONS,
)
from app.core.utils import slot_value
from app.services.catalog import get_cities


def validate_filters(slots: dict) -> list[str]:
    """Validate buyer filters. Returns list of errors, empty if all valid."""
    errors: list[str] = []

    _check_enum(slots, "transmission", TRANSMISSIONS, errors)
    _check_enum(slots, "assembly", ASSEMBLIES, errors)
    _check_enum(slots, "body_type", BODY_TYPES, errors)
    _check_enum(slots, "color", COLORS, errors)
    _check_enum(slots, "city", get_cities(), errors)

    _check_range(slots, "price_min", 50_000, 500_000_000, errors)
    _check_range(slots, "price_max", 50_000, 500_000_000, errors)
    _check_range(slots, "year_min", 1950, 2027, errors)
    _check_range(slots, "year_max", 1950, 2027, errors)
    _check_range(slots, "mileage_max", 0, 1_500_000, errors)

    return errors


def _check_enum(slots: dict, key: str, allowed: list[str], errors: list[str]) -> None:
    val = slot_value(slots, key)
    if val is None:
        return
    if val not in allowed:
        errors.append(f"{key}: '{val}' not valid")


def _check_range(slots: dict, key: str, low: int, high: int, errors: list[str]) -> None:
    val = slot_value(slots, key)
    if val is None:
        return
    try:
        num = int(val)
    except (ValueError, TypeError):
        errors.append(f"{key}: '{val}' not a number")
        return
    if num < low or num > high:
        errors.append(f"{key}: {num} outside {low}-{high}")