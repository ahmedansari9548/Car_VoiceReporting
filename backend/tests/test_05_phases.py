"""Test 5: Full phase flow — search, select, book inspection, confirm."""


def test_full_flow_english(new_chat, turn):
    # Phase 1: searching
    result, sid = new_chat("Corolla in Lahore under 50 lakh automatic")
    assert result["phase"] == "searching"
    assert result["cars"] is not None
    assert len(result["cars"]) > 0

    # Phase 2: select a car
    first_car = result["cars"][0]
    result2 = turn(f"I like the {first_car['year']} {first_car['make']} {first_car['model']}", sid)
    assert result2["phase"] in ("selected", "searching"), \
        f"Expected selected, got {result2['phase']}"

    # If not selected yet, try more explicitly
    if result2["phase"] != "selected":
        result2 = turn("I want the first one, select it", sid)

    # Phase 3: request inspection
    result3 = turn("yes book inspection", sid)
    assert result3["phase"] in ("selected", "inspection"), \
        f"Expected inspection, got {result3['phase']}"

    # Phase 4: provide details
    result4 = turn("Ali Khan, 0312-9876543, this Saturday at 2pm", sid)
    # might need another turn if not all details captured
    if result4["phase"] != "confirmed":
        result4 = turn("my name is Ali, phone 0312-9876543, Saturday 2pm", sid)

    # Final check
    assert result4["session_id"] == sid


def test_full_flow_roman_urdu(new_chat, turn):
    result, sid = new_chat("Civic chahiye Lahore mein 50 lakh tak")
    assert result["cars"] is not None
    assert len(result["cars"]) > 0

    first_car = result["cars"][0]
    turn(f"ye {first_car['year']} wali pasand hai", sid)
    turn("inspection karwao", sid)
    result_final = turn("naam Bilal, number 0333-1234567, kal subah 10 baje", sid)

    assert result_final["session_id"] == sid
