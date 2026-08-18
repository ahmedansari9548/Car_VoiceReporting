"""Test 2: Search returns cars with correct filters."""


def test_basic_search_english(new_chat):
    result, sid = new_chat("Show me Corolla in Lahore under 40 lakh")

    assert result["cars"] is not None, "No cars returned"
    assert len(result["cars"]) > 0, "Empty car list"
    assert result["total_results"] > 0

    for car in result["cars"]:
        assert car["make"] == "Toyota", f"Wrong make: {car['make']}"
        assert car["model"] == "Corolla", f"Wrong model: {car['model']}"
        assert car["city"] == "Lahore", f"Wrong city: {car['city']}"
        assert car["price"] <= 4000000, f"Price too high: {car['price']}"


def test_basic_search_roman_urdu(new_chat):
    result, sid = new_chat("Civic chahiye Lahore mein 50 lakh tak")

    assert result["cars"] is not None
    assert len(result["cars"]) > 0

    for car in result["cars"]:
        assert car["make"] == "Honda"
        assert car["model"] == "Civic"


def test_suv_search(new_chat):
    result, sid = new_chat("SUV chahiye Islamabad mein 1 crore tak")

    assert result["cars"] is not None
    assert len(result["cars"]) > 0
    assert result["total_results"] > 0


def test_cheap_car(new_chat):
    result, sid = new_chat("10 lakh mein gaari chahiye Multan mein")

    assert result["cars"] is not None
    for car in result["cars"]:
        assert car["price"] <= 1000000, f"Price too high for cheap search: {car['price']}"


def test_unknown_model_no_crash(new_chat):
    """Ferrari isn't in our DB. System should not crash.
    It won't return 0 results because the LLM can't filter by 'Ferrari' —
    it just returns other cars matching the price/city filters."""
    result, sid = new_chat("Ferrari in Lahore under 10 lakh")

    # must not crash
    assert result["reply"] is not None
    assert result["session_id"] is not None
    # no Ferrari should appear in results
    if result["cars"]:
        for car in result["cars"]:
            assert car["make"] != "Ferrari", "Ferrari shouldn't be in our DB"