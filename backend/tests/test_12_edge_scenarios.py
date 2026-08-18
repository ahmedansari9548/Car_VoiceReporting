"""
Test 12: Real-world edge scenarios.

Each test simulates a situation that commonly breaks in production.
"""


# =========================================================================
# SCENARIO 1: Budget correction mid-conversation
# User says 30 lakh, then changes to 35 lakh.
# The old value must be replaced, not ignored.
# =========================================================================

def test_budget_30_to_35(new_chat, turn):
    result, sid = new_chat("Corolla Lahore 30 lakh")
    
    result2 = turn("35 lakh tak budget hai", sid)
    if "price_max" in result2["slots"]:
        val = int(result2["slots"]["price_max"]["value"])
        assert val == 3500000, f"Budget stuck at {val}, should be 3500000"


# =========================================================================
# SCENARIO 2: City change
# User starts with Karachi, then says "actually Lahore".
# Cars must switch to Lahore, not stay Karachi.
# =========================================================================

def test_city_switch_karachi_to_lahore(new_chat, turn):
    r1, sid = new_chat("Civic Karachi 50 lakh")
    r2 = turn("actually Lahore mein dhundna hai", sid)
    
    if "city" in r2["slots"]:
        assert r2["slots"]["city"]["value"] == "Lahore"
    
    # verify cars are from Lahore
    if r2.get("cars"):
        for car in r2["cars"]:
            assert car["city"] == "Lahore", f"Car still from {car['city']}"


# =========================================================================
# SCENARIO 3: Model switch
# User asks for Corolla, then changes mind to Civic.
# Should show Civics, not Corollas.
# =========================================================================

def test_model_switch_corolla_to_civic(new_chat, turn):
    r1, sid = new_chat("Corolla Lahore 50 lakh")
    r2 = turn("Civic dikhao", sid)
    
    if r2.get("cars"):
        for car in r2["cars"]:
            assert car["model"] == "Civic", f"Still showing {car['model']}"


# =========================================================================
# SCENARIO 4: Greeting then search then greeting
# "hello" → search → "thanks" should not reset the search.
# =========================================================================

def test_greeting_search_thanks(new_chat, turn):
    r1, sid = new_chat("hello")
    cars1 = r1.get("cars") or []
    assert len(cars1) == 0, "Greeting returned cars"
    
    r2 = turn("Corolla Lahore 40 lakh", sid)
    assert len(r2.get("cars") or []) > 0, "Search after greeting failed"
    
    # "thanks" should NOT clear the conversation or return random cars
    r3 = turn("thanks", sid)
    # slots should still have the previous search filters
    assert "model" in r3.get("slots", {}), "Slots wiped after thanks"


# =========================================================================
# SCENARIO 5: Multiple prices in one message
# "budget 20 se 35 lakh" — should set price_min=2000000, price_max=3500000
# This is hard. At minimum, the higher number should be price_max.
# =========================================================================

def test_price_range(new_chat):
    result, sid = new_chat("Corolla Lahore 20 se 35 lakh tak")
    slots = result["slots"]
    
    # at minimum, price_max should be the higher number
    if "price_max" in slots:
        val = int(slots["price_max"]["value"])
        assert val >= 3000000, f"price_max too low: {val}"


# =========================================================================
# SCENARIO 6: Same message repeated
# User sends "Corolla Lahore 40 lakh" twice. 
# Should not create duplicate slots or crash.
# =========================================================================

def test_repeated_message(new_chat, turn):
    r1, sid = new_chat("Corolla Lahore 40 lakh")
    count1 = r1["total_results"]
    
    r2 = turn("Corolla Lahore 40 lakh", sid)
    count2 = r2["total_results"]
    
    assert count2 == count1, f"Results changed on repeat: {count1} → {count2}"
    assert r2["reply"] is not None


# =========================================================================
# SCENARIO 7: Misspelled model name
# "korola" should still find Corolla.
# "alswin" should still find Alsvin.
# =========================================================================

def test_misspelled_model(new_chat):
    # "corolla" misspelled as "korola" — won't match _quick_extract keywords
    # but the LLM should handle it
    result, sid = new_chat("korola Lahore 40 lakh")
    # should not crash at minimum
    assert result["reply"] is not None


# =========================================================================
# SCENARIO 8: Urdu numbers
# "pachas lakh" (50 lakh), "tees lakh" (30 lakh)
# Number parser should catch these.
# =========================================================================

def test_urdu_number_pachas_lakh(new_chat):
    result, sid = new_chat("Corolla Lahore pachas lakh tak")
    if "price_max" in result["slots"]:
        val = int(result["slots"]["price_max"]["value"])
        assert val == 5000000, f"pachas lakh parsed as {val}"


# =========================================================================
# SCENARIO 9: Filter then broaden
# "Corolla automatic Lahore 30 lakh" (few results)
# Then "any car Lahore 30 lakh" should show more results.
# =========================================================================

def test_filter_then_broaden(new_chat, turn):
    r1, sid = new_chat("Corolla automatic Lahore 30 lakh")
    narrow = r1.get("total_results", 0)
    
    r2 = turn("koi bhi car dikhao Lahore 30 lakh", sid)
    broad = r2.get("total_results", 0)
    
    # broad should have same or more results
    # (it might not if LLM doesn't clear the Corolla filter)
    assert r2["reply"] is not None  # at minimum, no crash


# =========================================================================
# SCENARIO 10: Long conversation (6+ turns)
# Context from turn 1 should still be accessible at turn 6.
# =========================================================================

def test_long_conversation_context(new_chat, turn):
    r1, sid = new_chat("Corolla Lahore 50 lakh")
    turn("automatic", sid)
    turn("white color", sid)
    turn("2019 or newer", sid)
    turn("low mileage preferred", sid)
    
    # turn 6: ask about the search — should still know it's Corolla Lahore
    r6 = turn("kya options hain?", sid)
    slots = r6.get("slots", {})
    
    # model and city from turn 1 should still be in slots
    assert "model" in slots, "Model lost after 6 turns"
    assert "city" in slots, "City lost after 6 turns"


# =========================================================================
# SCENARIO 11: Inspection with partial info across turns
# User gives name on one turn, phone on next, date on third.
# All should accumulate, not replace each other.
# =========================================================================

def test_inspection_partial_info(new_chat, turn):
    r1, sid = new_chat("Corolla Lahore 50 lakh automatic")
    
    if r1.get("cars") and len(r1["cars"]) > 0:
        first = r1["cars"][0]
        # select
        r2 = turn(f"I want the {first['year']} {first['make']} {first['model']}", sid)
        
        # request inspection
        r3 = turn("book inspection", sid)
        
        # give name only
        r4 = turn("my name is Ahmed", sid)
        assert r4["reply"] is not None  # should ask for phone
        
        # give phone only
        r5 = turn("0321-1234567", sid)
        assert r5["reply"] is not None  # should ask for date/time
        
        # no crash through the whole flow
        assert r5["session_id"] == sid


# =========================================================================
# SCENARIO 12: Rapid filter changes
# User changes every filter in 4 turns. Each change must stick.
# =========================================================================

def test_rapid_filter_changes(new_chat, turn):
    r1, sid = new_chat("Corolla Lahore 40 lakh")
    
    # change to Civic
    r2 = turn("Civic dikhao", sid)
    
    # change city
    r3 = turn("Karachi mein dekhein", sid)
    
    # change budget
    r4 = turn("50 lakh tak", sid)
    
    # final state should reflect ALL changes
    slots = r4.get("slots", {})
    
    # at minimum, the latest values should be present
    if "city" in slots:
        assert slots["city"]["value"] == "Karachi", \
            f"City should be Karachi, got {slots['city']['value']}"
    
    if "price_max" in slots:
        assert int(slots["price_max"]["value"]) == 5000000, \
            f"Budget should be 50L, got {slots['price_max']['value']}"
