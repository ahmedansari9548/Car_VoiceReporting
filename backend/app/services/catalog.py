"""
app/services/catalog.py

Three jobs:
  1. load()      — read catalog.json into memory once at startup
  2. resolve()   — match a messy spoken fragment to a real catalog entry
  3. autofill()  — the cascade: variant resolved → 6 more fields filled

This file is the product. Everything else — the LLM, the routes, the UI —
exists to feed data into resolve() and display the output of autofill().
"""

from __future__ import annotations

import json
import difflib
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.core.constants import COLOR_SYNONYMS, SOURCE_DERIVED
from app.core.utils import slot_value

# -------------------------------------------------------------------------
# In-memory catalog — loaded once, read many
# -------------------------------------------------------------------------

_catalog: dict = {}
_model_index: dict[str, dict] = {}      # "civic" → model dict
_variant_index: dict[str, list] = {}     # "civic" → [variant, variant, ...]
_all_aliases: list[str] = []             # flat list for fuzzy matching


def load() -> None:
    """Read catalog.json into memory. Called once at startup."""
    global _catalog
    _catalog = json.loads(Path(settings.CATALOG_PATH).read_text())

    for model in _catalog["models"]:
        key = model["model"].lower()
        _model_index[key] = model
        _variant_index[key] = model["variants"]
        for alias in model.get("aliases", []):
            _model_index[alias.lower()] = model
            _variant_index[alias.lower()] = model["variants"]
            _all_aliases.append(alias.lower())
        _all_aliases.append(key)


def get_cities() -> list[str]:
    return _catalog.get("cities", [])


def get_registration_options() -> list[str]:
    return _catalog.get("registration_options", [])


# -------------------------------------------------------------------------
# Resolve — match spoken text to catalog entries
# -------------------------------------------------------------------------

def resolve_model(text: str) -> Optional[dict]:
    """
    Match a spoken model name to a catalog entry.

    Tries exact match first, then fuzzy. Returns the full model dict
    or None if nothing is close enough.
    """
    key = text.strip().lower()

    # exact match on model name or alias
    if key in _model_index:
        return _model_index[key]

    # fuzzy match — catches "orial", "korola", "alswin"
    matches = difflib.get_close_matches(key, _all_aliases, n=1, cutoff=0.7)
    if matches:
        return _model_index[matches[0]]

    return None


def resolve_make(text: str) -> Optional[str]:
    """Match a spoken make name. Returns the canonical make or None."""
    key = text.strip().lower()
    makes = {m["make"].lower(): m["make"] for m in _catalog["models"]}
    if key in makes:
        return makes[key]
    matches = difflib.get_close_matches(key, list(makes.keys()), n=1, cutoff=0.7)
    return makes[matches[0]] if matches else None


def resolve_variant(
    model_name: str,
    variant_text: str,
    year: Optional[int] = None,
) -> list[dict]:
    """
    Match a spoken variant to catalog variants for a given model.

    Returns a list because there may be ambiguity:
      "Oriel" on a 2020 Civic → [VTi Oriel, VTi Oriel UG]

    If year is provided, filters to variants produced in that year.
    The caller decides whether to disambiguate (2 results) or pick (1 result).
    """
    key = model_name.strip().lower()
    variants = _variant_index.get(key, [])
    if not variants:
        return []

    search = variant_text.strip().lower()
    results = []

    for v in variants:
        name_lower = v["name"].lower()

        # exact or substring match
        if search == name_lower or search in name_lower:
            if year and not (v["years"][0] <= year <= v["years"][1]):
                continue
            results.append(v)

    # if exact produced nothing, try fuzzy on variant names
    if not results:
        names = [v["name"].lower() for v in variants]
        fuzzy = difflib.get_close_matches(search, names, n=3, cutoff=0.5)
        for fname in fuzzy:
            for v in variants:
                if v["name"].lower() == fname:
                    if year and not (v["years"][0] <= year <= v["years"][1]):
                        continue
                    results.append(v)

    return results


def get_variants_for_model(model_name: str, year: Optional[int] = None) -> list[dict]:
    """All variants for a model, optionally filtered by year."""
    key = model_name.strip().lower()
    variants = _variant_index.get(key, [])
    if year:
        return [v for v in variants if v["years"][0] <= year <= v["years"][1]]
    return list(variants)


def resolve_color(text: str) -> Optional[str]:
    """Match a spoken color (Urdu or English) to the PakWheels enum."""
    key = text.strip().lower()
    return COLOR_SYNONYMS.get(key)


# -------------------------------------------------------------------------
# Autofill — the cascade. THIS IS THE PRODUCT.
# -------------------------------------------------------------------------

def autofill(slots: dict, model_dict: Optional[dict] = None) -> dict:
    """
    Fill every field the catalog knows, given what's already in slots.

    This is why "one sentence → 9 fields" works. When the variant is
    resolved, 6 more fields come from the catalog for free.

    Every field this function writes gets source="derived" so the UI
    can show it with a DERIVED badge instead of a SAID badge.

    Args:
        slots: current slot dict, e.g. {"make": {"value": "Honda", ...}}
        model_dict: the resolved model from the catalog (optional,
                    looked up from slots if not provided)

    Returns:
        Updated slots dict with derived fields added.
    """
    slots = dict(slots)  # don't mutate the original

    # try to resolve the model if we have a model name but no model_dict
    if model_dict is None:
        model_val = slot_value(slots, "model")
        if model_val:
            model_dict = resolve_model(model_val)

    if model_dict is None:
        return slots

    # derive make from model if not already set
    if not slot_value(slots, "make"):
        slots["make"] = _derived(model_dict["make"])

    # derive body_type and assembly from model
    if not slot_value(slots, "body_type"):
        slots["body_type"] = _derived(model_dict["body_type"])

    if not slot_value(slots, "assembly"):
        slots["assembly"] = _derived(model_dict["assembly"])

    # variant cascade — the big one
    variant_val = slot_value(slots, "variant")
    year_val = slot_value(slots, "model_year")
    year = int(year_val) if year_val else None

    if variant_val:
        matches = resolve_variant(model_dict["model"], variant_val, year)

        if len(matches) == 1:
            v = matches[0]
            _fill_from_variant(slots, v)
        elif len(matches) > 1:
            # ambiguity — fill what's common across all matches,
            # leave the rest for the assistant to disambiguate
            _fill_common(slots, matches)

    elif year:
        # no variant spoken, but we have the year — check if only one
        # variant exists for this model+year (e.g. BR-V has only one)
        year_variants = get_variants_for_model(model_dict["model"], year)
        if len(year_variants) == 1:
            v = year_variants[0]
            slots["variant"] = _derived(v["name"])
            _fill_from_variant(slots, v)

    return slots


def _fill_from_variant(slots: dict, v: dict) -> None:
    """Fill all derivable fields from a single resolved variant."""
    if not slot_value(slots, "engine_capacity_cc"):
        slots["engine_capacity_cc"] = _derived(v["cc"])

    if not slot_value(slots, "engine_type"):
        slots["engine_type"] = _derived(v["fuel"])

    # only derive transmission if the variant is single-transmission
    if not slot_value(slots, "transmission") and v["transmission"] != "any":
        slots["transmission"] = _derived(v["transmission"])

    if not slot_value(slots, "features"):
        slots["features"] = _derived(v.get("features", []))

    if v.get("seating") and not slot_value(slots, "seating_capacity"):
        slots["seating_capacity"] = _derived(v["seating"])


def _fill_common(slots: dict, variants: list[dict]) -> None:
    """Fill fields that are the same across all ambiguous matches."""
    def all_same(key):
        vals = [v.get(key) for v in variants]
        return vals[0] if len(set(str(v) for v in vals)) == 1 else None

    cc = all_same("cc")
    if cc and not slot_value(slots, "engine_capacity_cc"):
        slots["engine_capacity_cc"] = _derived(cc)

    fuel = all_same("fuel")
    if fuel and not slot_value(slots, "engine_type"):
        slots["engine_type"] = _derived(fuel)

    trans = all_same("transmission")
    if trans and trans != "any" and not slot_value(slots, "transmission"):
        slots["transmission"] = _derived(trans)


# -------------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------------

def slot_value(slots: dict, key: str):
    """Get the raw value from a slot, or None if missing."""
    slot = slots.get(key)
    if slot is None:
        return None
    if isinstance(slot, dict):
        return slot.get("value")
    return slot


def _derived(value) -> dict:
    """Wrap a value as a derived slot."""
    return {"value": value, "source": SOURCE_DERIVED, "confidence": 0.95}