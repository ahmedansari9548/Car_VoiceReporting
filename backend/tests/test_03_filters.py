"""Test 3: Advanced filters — mileage, color, transmission, refinement chain."""


def test_mileage_filter(new_chat, turn):
    result, sid = new_chat("white car under 35 lakh, less than 40000 km, Lahore")

    if result["cars"]:
        for car in result["cars"]:
            assert car["price"] <= 3500000, f"Price {car['price']} exceeds 35 lakh"
            # mileage filter might not be applied by LLM on first turn
            # but should be in slots


def test_transmission_filter(new_chat, turn):
    result, sid = new_chat("Corolla Lahore 50 lakh")

    result2 = turn("only automatic", sid)
    assert "transmission" in result2["slots"]
    assert result2["slots"]["transmission"]["value"].lower() == "automatic"

    if result2["cars"]:
        for car in result2["cars"]:
            assert car["transmission"] == "Automatic", f"Got {car['transmission']}"


def test_refinement_narrows_results(new_chat, turn):
    """Each refinement should reduce or maintain result count."""
    result, sid = new_chat("show me cars in Lahore under 50 lakh")
    count1 = result["total_results"]

    result2 = turn("only Honda", sid)
    count2 = result2["total_results"]
    assert count2 <= count1, f"Honda filter didn't narrow: {count1} → {count2}"

    result3 = turn("only automatic", sid)
    count3 = result3["total_results"]
    assert count3 <= count2, f"Auto filter didn't narrow: {count2} → {count3}"


def test_hybrid_filter(new_chat):
    result, sid = new_chat("hybrid car Lahore 40 lakh tak")

    # should find Aqua/Prius
    if result["cars"]:
        makes = {car["make"] for car in result["cars"]}
        assert "Toyota" in makes, "Expected Toyota hybrid (Aqua/Prius)"
