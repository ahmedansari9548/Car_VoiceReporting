"""
app/services/helpers.py
"""

import re
from app.api.schemas.common import SlotValue, Source
from app.core.utils import slot_value


# Affirmative words — used by phases.py to detect "yes" to inspection offer
AFFIRMATIVE_WORDS = {
    "haan", "han", "ha", "yes", "yep", "yeah", "sure", "ok", "okay",
    "ji", "jee", "thik", "theek", "bilkul", "zaroor", "karo", "kardo",
    "chalo", "chalain", "lelo", "book",
    "ہاں", "جی", "ٹھیک", "بالکل", "ضرور",
}

def format_car(c: dict) -> dict:
    return {
        "id": c.get("id"), "make": c["make"], "model": c["model"],
        "variant": c["variant"], "year": c["model_year"], "price": c["price"],
        "mileage": c["mileage_km"], "city": c["city"],
        "transmission": c["transmission"], "color": c["color"],
        "seller_type": c["seller_type"], "image_url": c.get("image_url", ""),
    }


def missing_filters(slots: dict) -> list[str]:
    missing = []
    if not slot_value(slots, "price_max"):
        missing.append("price_max")
    if not slot_value(slots, "city"):
        missing.append("city")
    if not any(slot_value(slots, f) for f in ["make", "model", "body_type"]):
        missing.append("car_type")
    return missing


def slots_to_filters(slots: dict) -> dict:
    mapping = {
        "make": "make", "model": "model", "city": "city",
        "price_min": "price_min", "price_max": "price_max",
        "transmission": "transmission", "body_type": "body_type",
        "assembly": "assembly", "mileage_max": "mileage_max",
        "color": "color", "year_min": "year_min", "year_max": "year_max",
    }
    return {fk: slot_value(slots, sk) for sk, fk in mapping.items() if slot_value(slots, sk)}


def to_schema(slots: dict) -> dict[str, SlotValue]:
    return {
        k: SlotValue(
            value=v["value"] if isinstance(v, dict) else v,
            source=Source(v.get("source", "said")) if isinstance(v, dict) else Source.SAID,
            confidence=v.get("confidence", 1.0) if isinstance(v, dict) else 1.0,
            turn=v.get("turn") if isinstance(v, dict) else None,
        )
        for k, v in slots.items() if not k.startswith("_")
    }


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.lower()))


def is_detail_or_selection(text: str) -> bool:
    tokens = _tokens(text)
    lower = text.lower()

    if tokens & {"pehli", "first", "doosri", "second", "teesri", "third",
                 "chauthi", "fourth", "paanchvi", "fifth",
                 "select", "pick", "pasand", "lelo"}:
        return True

    if tokens & {"ye", "yeh"} and tokens & {"wali", "chahiye", "pasand", "dikhao", "batao"}:
        return True

    detail_phrases = [
        "this one", "i like", "this car", "more about",
        "tell me about", "details", "iske baare", "is gaari",
        "ye wali batao", "yeh wali batao",
        "اس گاڑی", "اس کے بارے", "تفصیل",
    ]
    return any(p in lower for p in detail_phrases)


def user_selecting(text: str) -> bool:
    return is_detail_or_selection(text)


def parse_selection(text: str, cars: list) -> int | None:
    if not cars:
        return None

    tokens = _tokens(text)
    lower = text.lower()

    # 1. Variant name FIRST
    for i, car in enumerate(cars):
        variant = (car.get("variant") or "").lower()
        if variant and len(variant) > 2:
            for vw in set(re.findall(r"\w+", variant)):
                if len(vw) > 2 and vw in tokens:
                    return i

    # 2. Model name
    for i, car in enumerate(cars):
        model = (car.get("model") or "").lower()
        if model and model in tokens:
            return i

    # 3. Positional (1st through 5th + Urdu)
    if tokens & {"pehli", "first", "1st"} and len(cars) > 0:
        return 0
    if tokens & {"doosri", "second", "2nd"} and len(cars) > 1:
        return 1
    if tokens & {"teesri", "third", "3rd"} and len(cars) > 2:
        return 2
    if tokens & {"chauthi", "fourth", "4th"} and len(cars) > 3:
        return 3
    if tokens & {"paanchvi", "fifth", "5th"} and len(cars) > 4:
        return 4

    # 4. Numeric: "car number 4", "number 3", "jo chauthi thi"
    num_match = re.search(r"(?:number|#|no\.?)\s*(\d)", text.lower())
    if num_match:
        idx = int(num_match.group(1)) - 1
        if 0 <= idx < len(cars):
            return idx

    # 5. Demonstratives → first car
    if tokens & {"ye", "yeh", "this", "isko"} and not tokens & {"nahi", "not", "nhi", "cancel"}:
        return 0

    return None


def wants_inspection(text: str) -> bool:
    lower = text.lower()
    return any(w in lower for w in [
        "inspection", "inspect", "book", "schedule", "karwao",
        "lagwao", "check karwao", "dekh lo",
    ])


def has_inspection_data(llm_result: dict) -> bool:
    insp_slots = {"buyer_name", "buyer_phone", "preferred_date", "preferred_time"}
    for u in llm_result.get("slot_updates", []):
        if u["slot"] in insp_slots:
            return True
    return bool(llm_result.get("inspection_data"))


def claims_no_cars(reply: str) -> bool:
    """
    Did the LLM claim the inventory is empty?

    These patterns must be SPECIFIC. The old list contained bare "nahi hai"
    and "نہیں ہے" — phrases that appear in almost any ordinary Urdu sentence,
    so healthy replies were being flagged and replaced by the override below.
    """
    lower = reply.lower()
    return any(p in lower for p in [
        "no cars", "no car is", "no cars are", "not available right now",
        "none are available", "no results", "no matches", "nothing available",
        "couldn't find any", "could not find any", "no options found",
        "کوئی گاڑی نہیں", "کوئی گاڑی دستیاب نہیں", "کوئی آپشن نہیں",
        "دستیاب نہیں ہے", "موجود نہیں ہے", "کچھ نہیں ملا", "کوئی نتیجہ نہیں",
    ])


def override_no_cars(total: int, top_cars: list, language: str = "en") -> str:
    """Replacement text when the LLM falsely says inventory is empty."""
    car_list = "، ".join(
        f"{c['year']} {c['make']} {c['model']} Rs {c['price']:,}" for c in top_cars
    ) if language == "ur" else ", ".join(
        f"{c['year']} {c['make']} {c['model']} Rs {c['price']:,}" for c in top_cars
    )

    if language == "ur":
        return f"دراصل {total} گاڑیاں موجود ہیں۔ سرِفہرست: {car_list}۔ کون سی پسند ہے؟"
    return f"There are actually {total} options. Top picks: {car_list}. Which one do you like?"


def fallback_reply(cars, total, slots, phase, language="en"):
    if language == "ur":
        return _fallback_urdu(cars, total, slots, phase)
    return _fallback_english(cars, total, slots, phase)


def _fallback_english(cars, total, slots, phase):
    if phase == "confirmed":
        return "Inspection booked! Best of luck with your car."
    if phase in ("selected", "inspection"):
        return "Would you like to book a PakWheels inspection for this car?"
    if cars and len(cars) > 0:
        top = cars[:3]
        lines = [f"{total} options found:"]
        for i, c in enumerate(top):
            lines.append(f"  {i+1}. {c.get('year')} {c.get('make')} {c.get('model')} "
                         f"{c.get('variant', '')} — Rs {c.get('price', 0):,}, {c.get('city')}")
        lines.append("Which one do you like?")
        return "\n".join(lines)

    p_max = slot_value(slots, "price_max")
    model = slot_value(slots, "model")
    make = slot_value(slots, "make")
    city = slot_value(slots, "city")

    if p_max and int(p_max) < 750_000:
        return f"No cars are available under Rs {int(p_max):,} (minimum price in inventory is Rs 750,000 for Suzuki Mehran VX)."

    if model or make:
        car_name = f"{make or ''} {model or ''}".strip()
        city_str = f" in {city}" if city and city.lower() != "all" else ""
        price_str = f" under Rs {int(p_max):,}" if p_max else ""
        return f"No {car_name}{city_str}{price_str} is available right now. Would you like to check other cities or models?"

    if not city:
        return "Which city are you looking in?"
    if not p_max:
        return "What is your budget?"
    return "What type of car are you looking for?"


def _fallback_urdu(cars, total, slots, phase):
    if phase == "confirmed":
        return "انسپکشن بک ہو گئی! گاڑی کے لیے نیک خواہشات۔"
    if phase in ("selected", "inspection"):
        return "کیا آپ اس گاڑی کی PakWheels انسپکشن بک کرنا چاہیں گے؟"
    if cars and len(cars) > 0:
        top = cars[:3]
        lines = [f"{total} آپشنز ملی ہیں:"]
        for i, c in enumerate(top):
            lines.append(f"  {i+1}. {c.get('year')} {c.get('make')} {c.get('model')} "
                         f"{c.get('variant', '')} — Rs {c.get('price', 0):,}, {c.get('city')}")
        lines.append("کون سی پسند ہے؟")
        return "\n".join(lines)

    p_max = slot_value(slots, "price_max")
    model = slot_value(slots, "model")
    make = slot_value(slots, "make")
    city = slot_value(slots, "city")

    if p_max and int(p_max) < 750_000:
        return f"{int(p_max):,} روپے سے کم کوئی گاڑی موجود نہیں ہے۔ ہمارے پاس سب سے سستی گاڑی 7.5 لاکھ روپے کی 2015 Suzuki Mehran VX ہے۔"

    if model or make:
        car_name = f"{make or ''} {model or ''}".strip()
        city_str = f" {city} میں" if city and city.lower() != "all" else ""
        price_str = f" {int(p_max):,} تک" if p_max else ""
        return f"{city_str}{price_str} کوئی {car_name} نہیں ملی۔ کیا آپ کسی اور شہر میں یا کوئی اور گاڑی دیکھنا چاہیں گے؟"

    if not city:
        return "کس شہر میں ڈھونڈ رہے ہیں؟"
    if not p_max:
        return "بجٹ کتنا ہے؟"
    return "کون سی گاڑی پسند کریں گے؟"


