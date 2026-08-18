"""Test 4: Slot extraction accuracy and sources."""


def test_slots_have_sources(new_chat):
    result, sid = new_chat("Corolla in Lahore under 40 lakh automatic")

    slots = result["slots"]
    assert len(slots) >= 3, f"Too few slots: {list(slots.keys())}"

    # every slot should have value and source
    for key, val in slots.items():
        assert "value" in val, f"Slot {key} missing value"
        assert "source" in val, f"Slot {key} missing source"
        assert val["source"] in ("said", "derived"), f"Slot {key} bad source: {val['source']}"


def test_said_vs_derived(new_chat):
    result, sid = new_chat("family car chahiye 35 lakh Lahore")

    slots = result["slots"]

    # price and city should be "said"
    if "price_max" in slots:
        assert slots["price_max"]["source"] == "said"
    if "city" in slots:
        assert slots["city"]["source"] == "said"

    # body_type from "family" should be "derived"
    if "body_type" in slots:
        assert slots["body_type"]["source"] == "derived", \
            f"body_type should be derived from 'family', got {slots['body_type']['source']}"


def test_number_parsing(new_chat):
    result, sid = new_chat("50 lakh ki gaari chahiye Lahore mein")

    slots = result["slots"]
    if "price_max" in slots:
        assert int(slots["price_max"]["value"]) == 5000000, \
            f"Expected 5000000, got {slots['price_max']['value']}"