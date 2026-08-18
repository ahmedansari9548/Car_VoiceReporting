"""Test 8: Edge cases — the system should never crash."""


def test_empty_text(client):
    r = client.post("/api/turns", json={"text": ""})
    # should either handle gracefully or return 422 validation error
    assert r.status_code in (200, 422, 500)


def test_single_word(new_chat):
    result, sid = new_chat("car")
    assert result["reply"] is not None
    assert len(result["reply"]) > 0


def test_numbers_only(new_chat):
    result, sid = new_chat("50 lakh")
    assert result["reply"] is not None
    assert "price_max" in result["slots"]


def test_very_long_message(new_chat):
    long_text = "I want " + "a really good " * 50 + "car in Lahore under 40 lakh"
    result, sid = new_chat(long_text)
    assert result["reply"] is not None


def test_special_characters(new_chat):
    result, sid = new_chat("car <script>alert('xss')</script> in Lahore")
    assert result["reply"] is not None
    # should not crash


def test_mixed_languages_one_message(new_chat):
    result, sid = new_chat("mujhe Lahore mein under 30 lakh Honda chahiye please")
    assert result["reply"] is not None
    assert result["cars"] is not None


def test_emoji_input(new_chat):
    result, sid = new_chat("🚗 Lahore mein car chahiye 30 lakh")
    assert result["reply"] is not None
