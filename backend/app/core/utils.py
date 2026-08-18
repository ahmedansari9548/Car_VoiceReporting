"""
app/core/utils.py

Shared helpers used across multiple services.
If you find yourself writing the same function in two files, it belongs here.
"""


def slot_value(slots: dict, key: str):
    """Get the raw value from a slot dict, handling both formats."""
    slot = slots.get(key)
    if slot is None:
        return None
    if isinstance(slot, dict):
        return slot.get("value")
    return slot