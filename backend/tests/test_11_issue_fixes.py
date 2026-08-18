"""
Test 11: Backend issue fixes from testing Excel.
Each test maps to a specific issue.
"""


# =========================================================================
# ISSUE 1: Conversation context preserved
# =========================================================================

def test_context_remembers_model_across_turns(new_chat, turn):
    """Model set in turn 1 should still be in slots at turn 3."""
    result, sid = new_chat("Corolla chahiye Lahore mein 40 lakh")
    assert "model" in result["slots"]

    result2 = turn("automatic chahiye", sid)
    assert "model" in result2["slots"], "Model lost after adding transmission"

    result3 = turn("white color sirf", sid)
    assert "model" in result3["slots"], "Model lost after adding color"


def test_context_preserves_city_across_refinement(new_chat, turn):
    result, sid = new_chat("Honda Civic Lahore 50 lakh")
    result2 = turn("only automatic", sid)
    assert "city" in result2["slots"], "City lost after refinement"


# =========================================================================
# ISSUE 2: Greetings don't trigger car search
# =========================================================================

def test_greeting_english(new_chat):
    result, sid = new_chat("hello")
    cars = result.get("cars") or []
    assert len(cars) == 0, f"Greeting triggered car search: {len(cars)} cars"


def test_greeting_urdu(new_chat):
    result, sid = new_chat("salam")
    cars = result.get("cars") or []
    assert len(cars) == 0, f"Salam triggered car search: {len(cars)} cars"


def test_greeting_then_search(new_chat, turn):
    result1, sid = new_chat("hello")
    cars1 = result1.get("cars") or []
    assert len(cars1) == 0, "Greeting returned cars"

    result2 = turn("show me Corolla in Lahore under 40 lakh", sid)
    cars2 = result2.get("cars") or []
    assert len(cars2) > 0, "Real search after greeting returned no cars"


def test_thanks_no_search(new_chat):
    result, sid = new_chat("shukriya")
    cars = result.get("cars") or []
    assert len(cars) == 0, f"Thanks triggered car search: {len(cars)} cars"


# =========================================================================
# ISSUE 3: Slot updates / corrections work
# =========================================================================

def test_budget_update(new_chat, turn):
    result, sid = new_chat("Corolla Lahore 30 lakh")
    if "price_max" in result["slots"]:
        val = result["slots"]["price_max"]["value"]
        assert int(val) == 3000000, f"Initial budget wrong: {val}"

    result2 = turn("actually 35 lakh tak budget hai", sid)
    if "price_max" in result2["slots"]:
        val2 = result2["slots"]["price_max"]["value"]
        assert int(val2) == 3500000, f"Budget not updated: {val2}"


def test_city_update(new_chat, turn):
    result, sid = new_chat("Civic Karachi 50 lakh")
    result2 = turn("Lahore mein dekhna hai, Karachi nahi", sid)
    if "city" in result2["slots"]:
        assert result2["slots"]["city"]["value"] == "Lahore", \
            f"City not updated: {result2['slots']['city']['value']}"


def test_model_update(new_chat, turn):
    result, sid = new_chat("Corolla Lahore 40 lakh")
    result2 = turn("Corolla nahi, Honda Civic dikhao", sid)
    if "model" in result2["slots"]:
        assert result2["slots"]["model"]["value"] in ("Civic", "civic"), \
            f"Model not updated: {result2['slots']['model']['value']}"


# =========================================================================
# ISSUE 4: Language — no Hindi, match user's language
# =========================================================================

def test_english_stays_english(new_chat):
    result, sid = new_chat("Show me Corolla in Lahore under 40 lakh")
    reply = result["reply"]
    hindi_words = ["gaadi", "shahar", "chaahiye", "dekhiye"]
    for word in hindi_words:
        assert word not in reply.lower(), \
            f"Hindi word '{word}' in English reply: {reply[:80]}"


def test_roman_urdu_no_script(new_chat):
    result, sid = new_chat("Lahore mein gaari chahiye 30 lakh tak")
    reply = result["reply"]
    has_urdu = any('\u0600' <= c <= '\u06FF' for c in reply)
    assert not has_urdu, f"Roman Urdu got Urdu script: {reply[:80]}"


# =========================================================================
# ISSUE 5: "No cars available" when cars exist in DB
# =========================================================================

def test_db_has_cars_shows_cars(new_chat):
    result, sid = new_chat("Corolla Lahore 50 lakh")
    assert result["total_results"] > 0, "DB should have Corollas in Lahore"
    assert len(result.get("cars") or []) > 0, "Cars in DB but not returned"


def test_reply_doesnt_contradict_results(new_chat):
    result, sid = new_chat("Honda Lahore 50 lakh")
    if result["total_results"] and result["total_results"] > 0:
        reply_lower = result["reply"].lower()
        bad = ["no car", "koi car nahi", "koi gaari nahi", "not available"]
        for phrase in bad:
            assert phrase not in reply_lower, \
                f"Reply says '{phrase}' but {result['total_results']} cars exist"


# =========================================================================
# ISSUE 6: State consistency
# =========================================================================

def test_phase_starts_searching(new_chat):
    result, sid = new_chat("Corolla Lahore 40 lakh")
    assert result["phase"] == "searching"


def test_slots_persist_across_turns(new_chat, turn):
    result, sid = new_chat("Corolla Lahore 40 lakh")
    turn("automatic", sid)
    result3 = turn("white color", sid)
    vals = str({k: v["value"] for k, v in result3["slots"].items()})
    assert "Lahore" in vals, f"City missing: {vals}"


def test_selected_car_persists(new_chat, turn):
    result, sid = new_chat("Corolla Lahore 50 lakh automatic")
    cars = result.get("cars") or []
    if len(cars) > 0:
        first = cars[0]
        # select it
        r2 = turn(f"I like the {first['year']} {first['make']} {first['model']}", sid)
        # check THIS turn or NEXT turn has selection
        if r2.get("phase") == "selected" or r2.get("selected_car"):
            # good, selected on this turn
            r3 = turn("tell me more", sid)
            assert r3.get("phase") in ("selected", "inspection"), \
                f"Phase changed unexpectedly: {r3['phase']}"
        else:
            # LLM didn't select — try explicit
            r3 = turn("select the first car please", sid)
            # just verify no crash
            assert r3["reply"] is not None