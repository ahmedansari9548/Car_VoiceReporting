"""
app/services/search_url.py

Builds real PakWheels search URLs from buyer filters.

The URL format is path-slug based:
    pakwheels.com/used-cars/search/-/mk_toyota/md_corolla/ct_lahore/pr_0_3500000/

Only the 7 verified slugs are used. A guessed slug that 404s in front
of a client is worse than offering fewer filters.

Also handles the needs→filters translation: "family car" → body types,
"7 seater" → SUV/MPV, "first car" → hatchback + small cc.
"""

from __future__ import annotations

from typing import Optional

from app.core.constants import PAKWHEELS_SEARCH_BASE, SEARCH_SLUGS

# -------------------------------------------------------------------------
# Needs → filter translation table
# -------------------------------------------------------------------------

# When a buyer says a need instead of a filter, this maps it to real
# PakWheels facets. The LLM extracts the need; this code translates it.
NEED_MAPPINGS: dict[str, dict] = {
    "family": {
        "body_type": ["Sedan", "Hatchback", "Crossover", "MPV"],
    },
    "7_seater": {
        "body_type": ["SUV", "MPV", "Mini Van"],
    },
    "first_car": {
        "body_type": ["Hatchback"],
    },
    "offroad": {
        "body_type": ["SUV", "Double Cabin", "Off-Road Vehicles"],
    },
    "luxury": {
        "body_type": ["Sedan", "SUV"],
    },
    "commercial": {
        "body_type": ["Pick Up", "Single Cabin", "Double Cabin", "Truck", "High Roof"],
    },
}


def build_url(filters: dict) -> str:
    """
    Build a PakWheels search URL from a filter dict.

    Args:
        filters: {
            "make": "Toyota",
            "model": "Corolla",
            "city": "Lahore",
            "price_min": 0,
            "price_max": 3500000,
            "transmission": "Automatic",
            "body_type": "Sedan",
            "doors": 4,
        }

    Returns:
        "https://www.pakwheels.com/used-cars/search/-/mk_toyota/md_corolla/ct_lahore/pr_0_3500000/tr_automatic/"
    """
    segments: list[str] = []

    # make
    make = filters.get("make")
    if make:
        segments.append(f"{SEARCH_SLUGS['make']}_{_slug(make)}")

    # model (only if make is present — PakWheels requires make for model)
    model = filters.get("model")
    if model and make:
        segments.append(f"{SEARCH_SLUGS['model']}_{_slug(model)}")

    # city
    city = filters.get("city")
    if city:
        segments.append(f"{SEARCH_SLUGS['city']}_{_slug(city)}")

    # price range
    price_min = filters.get("price_min", 0)
    price_max = filters.get("price_max")
    if price_max:
        segments.append(f"{SEARCH_SLUGS['price']}_{price_min}_{price_max}")

    # transmission
    trans = filters.get("transmission")
    if trans:
        segments.append(f"{SEARCH_SLUGS['transmission']}_{_slug(trans)}")

    # body type
    body = filters.get("body_type")
    if body:
        segments.append(f"{SEARCH_SLUGS['body_type']}_{_slug(body)}")

    # doors
    doors = filters.get("doors")
    if doors:
        segments.append(f"{SEARCH_SLUGS['doors']}_{doors}")

    return PAKWHEELS_SEARCH_BASE + "/".join(segments) + "/"


def apply_need(filters: dict, need: str) -> dict:
    """
    Apply a need mapping to the filters.

    If the buyer says "family car", this adds body_type filters.
    Only applies if those filters aren't already set by the user.
    """
    filters = dict(filters)
    mapping = NEED_MAPPINGS.get(need)
    if not mapping:
        return filters

    for key, values in mapping.items():
        if key not in filters:
            # use the first value for the URL (single-select in PakWheels)
            filters[key] = values[0]

    return filters


def summarize_filters(filters: dict) -> str:
    """One-line summary of what the search covers, for the assistant to say."""
    parts: list[str] = []

    city = filters.get("city")
    if city:
        parts.append(f"in {city}")

    price_max = filters.get("price_max")
    if price_max:
        if price_max >= 10_000_000:
            parts.append(f"under {price_max / 10_000_000:.1f} crore")
        elif price_max >= 100_000:
            parts.append(f"under {price_max / 100_000:.0f} lakh")

    make = filters.get("make")
    model = filters.get("model")
    if make and model:
        parts.append(f"{make} {model}")
    elif make:
        parts.append(make)

    trans = filters.get("transmission")
    if trans:
        parts.append(trans.lower())

    body = filters.get("body_type")
    if body:
        parts.append(body.lower())

    return ", ".join(parts) if parts else "all cars"


# -------------------------------------------------------------------------
# Helper
# -------------------------------------------------------------------------

def _slug(text: str) -> str:
    """Convert a display name to a PakWheels URL slug."""
    return text.strip().lower().replace(" ", "_").replace("-", "_")