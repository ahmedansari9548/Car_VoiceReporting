"""
Fetch one specific car image for every inventory listing.

Uses Pexels and stores the image URL directly in inventory.image_url.

Run:
    python -m scripts.fetch_images
"""

import re
import requests

from app.core.config import settings
from app.db.database import get_connection


PEXELS_URL = "https://api.pexels.com/v1/search"

HEADERS = {
    "Authorization": settings.PEXELS_API_KEY
}

RESULTS_PER_SEARCH = 10


def normalize(text: str | None) -> str:
    if not text:
        return ""

    return re.sub(r"[^a-z0-9 ]+", " ", str(text).lower()).strip()


def build_queries(listing: dict) -> list[str]:
    """
    Build increasingly broad search queries.

    Most specific query is tried first.
    """

    make = listing.get("make", "")
    model = listing.get("model", "")
    year = listing.get("year", "")
    variant = (
        listing.get("variant")
        or listing.get("trim")
        or listing.get("version")
        or ""
    )

    queries = []

    # Most specific
    if year and variant:
        queries.append(
            f"{year} {make} {model} {variant} car"
        )

    # Year + model
    if year:
        queries.append(
            f"{year} {make} {model} car"
        )

    # Variant + model
    if variant:
        queries.append(
            f"{make} {model} {variant} car"
        )

    # Model
    queries.append(
        f"{make} {model} car"
    )

    # Remove duplicates while preserving order
    unique = []

    for query in queries:
        query = query.strip()

        if query and query not in unique:
            unique.append(query)

    return unique


def score_photo(photo: dict, listing: dict) -> int:
    """
    Score a Pexels result against the listing.

    Pexels is not a vehicle catalog, so this is a best-match
    ranking rather than a guaranteed exact vehicle match.
    """

    alt = normalize(photo.get("alt", ""))

    make = normalize(listing.get("make"))
    model = normalize(listing.get("model"))
    year = normalize(listing.get("year"))

    variant = normalize(
        listing.get("variant")
        or listing.get("trim")
        or listing.get("version")
        or ""
    )

    score = 0

    if make and make in alt:
        score += 20

    if model and model in alt:
        score += 30

    if year and year in alt:
        score += 30

    if variant and variant in alt:
        score += 20

    return score


def fetch_best_image(listing: dict, used_urls: set[str]) -> str | None:
    """
    Search Pexels and return the best unused image for this listing.
    """

    queries = build_queries(listing)

    all_photos = []

    for query in queries:
        print(f"   Searching: {query}")

        try:
            response = requests.get(
                PEXELS_URL,
                headers=HEADERS,
                params={
                    "query": query,
                    "per_page": RESULTS_PER_SEARCH,
                    "orientation": "landscape",
                },
                timeout=20,
            )

            response.raise_for_status()

            data = response.json()

            photos = data.get("photos", [])

            if photos:
                all_photos.extend(photos)

        except Exception as e:
            print(f"   ❌ Search failed: {e}")

    if not all_photos:
        return None

    # Remove duplicate photos
    unique_photos = {}

    for photo in all_photos:
        photo_id = photo.get("id")

        if photo_id:
            unique_photos[photo_id] = photo

    photos = list(unique_photos.values())

    # Rank photos
    ranked = sorted(
        photos,
        key=lambda photo: score_photo(photo, listing),
        reverse=True,
    )

    # Prefer an unused image
    for photo in ranked:
        image_url = photo.get("src", {}).get("large")

        if image_url and image_url not in used_urls:
            return image_url

    # If every result has already been used, allow reuse
    for photo in ranked:
        image_url = photo.get("src", {}).get("large")

        if image_url:
            return image_url

    return None


def get_inventory_columns(cur) -> list[str]:
    """
    Get the actual inventory columns so the script can adapt
    to the existing database schema.
    """

    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'inventory'
        ORDER BY ordinal_position
        """
    )

    return [row[0] for row in cur.fetchall()]


def get_value(row: dict, *names):
    """
    Return the first available/non-empty column value.
    """

    for name in names:
        if name in row and row[name] not in (None, ""):
            return row[name]

    return None


def update_inventory():
    conn = get_connection()
    cur = conn.cursor()

    columns = get_inventory_columns(cur)

    print("\nInventory columns:")
    print(", ".join(columns))

    if "image_url" not in columns:
        raise RuntimeError(
            "inventory.image_url column does not exist."
        )

    # Prefer an ID column for updating individual listings
    id_column = None

    for candidate in ["id", "listing_id", "inventory_id"]:
        if candidate in columns:
            id_column = candidate
            break

    if not id_column:
        raise RuntimeError(
            "Could not find a listing ID column in inventory."
        )

    # Fetch all listings
    cur.execute("SELECT * FROM inventory ORDER BY " + id_column)

    raw_rows = cur.fetchall()

    column_names = [desc[0] for desc in cur.description]

    listings = [
        dict(zip(column_names, row))
        for row in raw_rows
    ]

    print(f"\nFound {len(listings)} inventory listings.\n")

    # Keep track of URLs already assigned
    used_urls = set()

    updated = 0

    for index, listing in enumerate(listings, start=1):

        listing_id = listing[id_column]

        make = get_value(
            listing,
            "make"
        )

        model = get_value(
            listing,
            "model"
        )

        year = get_value(
            listing,
            "year",
            "model_year"
        )

        variant = get_value(
            listing,
            "variant",
            "trim",
            "version"
        )

        print(
            f"[{index}/{len(listings)}] "
            f"{year or ''} {make or ''} "
            f"{model or ''} {variant or ''}"
        )

        image_url = fetch_best_image(
            {
                "make": make,
                "model": model,
                "year": year,
                "variant": variant,
                "trim": variant,
            },
            used_urls,
        )

        if not image_url:
            print("   ❌ No suitable image found")
            continue

        cur.execute(
            """
            UPDATE inventory
            SET image_url = %s
            WHERE """
            + id_column
            + " = %s",
            (image_url, listing_id),
        )

        conn.commit()

        used_urls.add(image_url)

        updated += 1

        print(
            f"   ✓ Image assigned: {image_url}"
        )

    cur.close()
    conn.close()

    print(
        f"\nFinished. Updated {updated}/{len(listings)} listings."
    )


if __name__ == "__main__":

    if not settings.PEXELS_API_KEY:
        raise RuntimeError(
            "PEXELS_API_KEY is missing from your .env file."
        )

    update_inventory()