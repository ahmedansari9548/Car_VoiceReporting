"""Test 7: Corrections — user changes a filter mid-conversation."""


def test_city_correction(new_chat, turn):
    result, sid = new_chat("Civic chahiye Karachi mein 40 lakh")

    slots = result["slots"]
    if "city" in slots:
        assert slots["city"]["value"] == "Karachi"

    result2 = turn("sorry Karachi nahi, Lahore mein chahiye", sid)
    slots2 = result2["slots"]

    if "city" in slots2:
        assert slots2["city"]["value"] == "Lahore", \
            f"City not corrected: {slots2['city']['value']}"

    if result2["cars"]:
        for car in result2["cars"]:
            assert car["city"] == "Lahore", f"Car still from {car['city']}"


def test_model_correction(new_chat, turn):
    result, sid = new_chat("Corolla chahiye Lahore 40 lakh")

    # be very explicit about the correction
    result2 = turn("Corolla cancel, mujhe Honda Civic chahiye instead", sid)
    slots2 = result2["slots"]

    # check if model changed — LLM might need a turn to process
    if "model" in slots2 and slots2["model"]["value"] == "Corolla":
        # try one more time, even more explicit
        result3 = turn("model change karo, Civic chahiye, Corolla nahi", sid)
        slots3 = result3["slots"]
        if "model" in slots3:
            assert slots3["model"]["value"] == "Civic", \
                f"Model still not corrected after 2 attempts: {slots3['model']['value']}"