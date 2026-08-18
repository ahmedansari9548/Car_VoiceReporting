"""
app/services/context.py

Builds structured context strings for the LLM prompt.
"""

from app.core.utils import slot_value
from app.services.catalog import get_variants_for_model, resolve_model


def build_state_context(phase, slots, selected_car, session_language="en"):
    lines = [
        "=== CONVERSATION STATE ===",
        f"CURRENT_PHASE: {phase}",
        "",
        "=== LANGUAGE RULE ===",
    ]

    if session_language == "ur":
        lines.append("REPLY_LANGUAGE: Urdu — ENTIRE reply in Urdu script (اردو). No English. No Roman Urdu.")
    else:
        lines.append("REPLY_LANGUAGE: English — ENTIRE reply in English. No Urdu.")
    lines.append("")

    # Active filters
    lines.append("=== ACTIVE FILTERS ===")
    filter_items = []
    for k, v in slots.items():
        if k.startswith("_"):
            continue
        val = v.get("value", v) if isinstance(v, dict) else v
        src = v.get("source", "said") if isinstance(v, dict) else "said"
        filter_items.append(f"  {k}: {val} (source={src})")
    lines.extend(filter_items if filter_items else ["  (none set)"])
    lines.append("")

    # Selected car
    lines.append("=== SELECTED CAR ===")
    if selected_car:
        lines.append(
            f"  {selected_car.get('year')} {selected_car.get('make')} "
            f"{selected_car.get('model')} {selected_car.get('variant', '')} — "
            f"Rs {selected_car.get('price', 0):,} | {selected_car.get('city')} | "
            f"{selected_car.get('transmission', '')} | {selected_car.get('mileage', 0)} km | "
            f"{selected_car.get('color', '')}"
        )
        lines.append("  >>> ONLY discuss THIS car. No alternatives unless user asks.")
        lines.append("  >>> Do NOT ask 'do you need more info?' — offer inspection directly.")
    else:
        lines.append("  (none)")
    lines.append("")

    # Inspection — the key fix: extremely explicit about collected vs missing
    lines.append("=== INSPECTION BOOKING ===")
    if phase == "inspection":
        insp = slots.get("_inspection", {})
        lines.append("  STATUS: Collecting inspection details.")
        lines.append("  ALREADY COLLECTED (do NOT ask for these again):")
        for field in ["name", "phone", "date", "time"]:
            val = insp.get(field)
            if val:
                lines.append(f"    ✓ {field}: {val} — DONE, do NOT re-ask")
            else:
                lines.append(f"    ✗ {field}: MISSING")
        needed = [f for f in ["name", "phone", "date", "time"] if not insp.get(f)]
        if not needed:
            lines.append("  >>> ALL COLLECTED — call determine_action with action=confirm_inspection")
        else:
            lines.append(f"  >>> Ask ONLY for: {needed[0]}")
            lines.append(f"  >>> Do NOT ask for anything else. Do NOT ask about the car.")
            lines.append(f"  >>> Do NOT re-ask for fields marked ✓ above.")
    elif phase == "selected":
        lines.append("  STATUS: Car selected. Offer inspection or answer car questions.")
        lines.append("  When user agrees to inspection, use action=schedule_inspection.")
    else:
        lines.append("  (not applicable)")
    lines.append("")

    # Phase instructions
    lines.append("=== PHASE INSTRUCTIONS ===")
    if phase == "searching":
        from app.services.helpers import missing_filters
        missing = missing_filters(slots)
        if missing:
            lines.append(f"  Missing: {', '.join(missing)}. Ask ONE question.")
        else:
            lines.append("  All filters set. Present cars from INVENTORY RESULTS.")
    elif phase == "selected":
        lines.append("  Discuss ONLY the selected car. Offer PakWheels inspection.")
        lines.append("  Do NOT ask for budget/city/car type.")
    elif phase == "inspection":
        lines.append("  ONLY collect the next missing inspection field.")
        lines.append("  Do NOT discuss the car. Do NOT ask budget/city.")
        lines.append("  Do NOT repeat any field already collected.")
    elif phase == "confirmed":
        lines.append("  Inspection booked. Confirm and wish luck.")
    lines.append("")

    return "\n".join(lines)


def build_catalog_context(slots):
    model_name = slot_value(slots, "model")
    if not model_name:
        return ""
    model = resolve_model(model_name)
    if not model:
        return ""
    year = slot_value(slots, "model_year")
    variants = get_variants_for_model(model_name, int(year) if year else None)

    lines = [
        "=== CATALOG INFO ===",
        f"MODEL: {model['make']} {model['model']}",
        f"BODY TYPE: {model['body_type']}",
        f"ASSEMBLY: {model['assembly']}",
        "", "VARIANTS:",
    ]
    for v in variants:
        trans = v["transmission"] if v["transmission"] != "any" else "Manual/Automatic"
        lines.append(f"  • {v['name']} | {v['years'][0]}-{v['years'][1]} | {v['cc']}cc {v['fuel']} | {trans}")
        if v.get("features"):
            lines.append(f"    Features: {', '.join(v['features'])}")
    lines.append("")
    return "\n".join(lines)


def build_inventory_context_from_cars(cars):
    if not cars:
        return "=== INVENTORY RESULTS ===\nNo cars match the current filters.\n"

    lines = [
        f"=== INVENTORY RESULTS ({len(cars)} shown) ===",
        "Present these to the user using the numbering below:",
    ]

    # Use 1-based numbering (no brackets — prevents LLM from copy-pasting [0] into reply)
    for i, c in enumerate(cars):
        lines.append(
            f"  {i+1}. {c.get('year')} {c.get('make')} {c.get('model')} "
            f"{c.get('variant') or ''} {c.get('transmission', '')} | "
            f"{c.get('mileage', 0)}km | Rs {c.get('price', 0):,} | "
            f"{c.get('city', '')} | {c.get('color', '')}"
        )

    lines.append("")
    lines.append("RULES:")
    lines.append("  - NEVER say a car is not available if it appears above.")
    lines.append("  - NEVER invent cars not in this list.")
    lines.append("  - When user selects by number, subtract 1 for the select_car index (user says '1' → index 0).")
    lines.append("")

    return "\n".join(lines)