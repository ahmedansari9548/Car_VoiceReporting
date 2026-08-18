"""
tests/test_services.py

Comprehensive tests for all service-layer pure functions.
Run from backend/: pytest tests/test_services.py -v
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import re


# ═══════════════════════════════════════════════════════════════
# 1. LANGUAGE DETECTION
# ═══════════════════════════════════════════════════════════════

from app.services.handlers import detect_language


class TestLanguageDetection:

    # ── Urdu script → ur ──
    def test_urdu_script_pure(self):
        assert detect_language("مجھے گاڑی چاہیے") == "ur"

    def test_urdu_script_mixed(self):
        assert detect_language("مجھے Honda Civic چاہیے") == "ur"

    def test_urdu_script_greeting(self):
        assert detect_language("السلام علیکم") == "ur"

    # ── Roman Urdu strong markers ──
    def test_roman_salam(self):
        assert detect_language("salam bhai") == "ur"

    def test_roman_gaari(self):
        assert detect_language("gaari dikhao") == "ur"

    def test_roman_chahiye(self):
        assert detect_language("mujhe chahiye") == "ur"

    def test_roman_dikhao(self):
        assert detect_language("dikhao yaar") == "ur"

    def test_roman_pasand(self):
        assert detect_language("ye pasand hai") == "ur"

    def test_roman_mujhe(self):
        assert detect_language("mujhe SUV dikhao") == "ur"

    # ── Roman Urdu weak markers (need 2+) ──
    def test_weak_single_not_enough(self):
        result = detect_language("hai")
        assert result != "ur" or result is None

    def test_weak_two_words_enough(self):
        assert detect_language("kya hai bhai") == "ur"

    def test_weak_aur_mein(self):
        assert detect_language("aur mein kya karun") == "ur"

    # ── English ──
    def test_english_simple(self):
        assert detect_language("I am looking for a car") == "en"

    def test_english_show_me(self):
        assert detect_language("show me SUVs under 50 lakh") == "en"

    # ── Ambiguous ──
    def test_just_number(self):
        assert detect_language("35") is None

    def test_car_name_only(self):
        result = detect_language("Corolla")
        assert result is None or result == "en"

    # ── Real user messages ──
    def test_real_roman_urdu_long(self):
        text = "Achcha Mujhe Koi City bhi dikhayen jo Lahore mein ho aur 80 lakh se niche Ho"
        assert detect_language(text) == "ur"

    def test_real_roman_urdu_selection(self):
        text = "Mujhe yah Civic oriel Pasand I Hai Isko Tum ab inspection ke liye book kar de please"
        assert detect_language(text) == "ur"

    def test_real_roman_urdu_database(self):
        text = "ji main aapki database Mein jitni bhi SUV padi hai mujhe Sara dikha de please"
        assert detect_language(text) == "ur"

    def test_main_aur_kuchh_nahin(self):
        text = "Main Aur Kuchh Nahin Janna Chahta"
        # "main" + "aur" + "nahin" + "janna" = 4 weak markers (need 2+)
        assert detect_language(text) == "ur"

    def test_fortuner_legend(self):
        result = detect_language("Fortuner legend")
        assert result is None or result == "en"


# ═══════════════════════════════════════════════════════════════
# 2. GREETING DETECTION
# ═══════════════════════════════════════════════════════════════

from app.services.handlers import is_greeting, has_car_keywords


class TestGreetingDetection:

    def test_hello(self):
        assert is_greeting("hello") is True

    def test_salam(self):
        assert is_greeting("salam") is True

    def test_salam_exclamation(self):
        assert is_greeting("salam!") is True

    def test_urdu_greeting(self):
        assert is_greeting("السلام علیکم") is True

    def test_short_text(self):
        assert is_greeting("ok") is True

    def test_car_query_not_greeting(self):
        assert is_greeting("show me Corolla in Lahore") is False

    def test_greeting_with_car_word(self):
        assert has_car_keywords("hello, looking for corolla") is True

    def test_greeting_without_car_word(self):
        assert has_car_keywords("hello") is False


# ═══════════════════════════════════════════════════════════════
# 3. ASK AI MESSAGE PARSING
# ═══════════════════════════════════════════════════════════════

from app.services.handlers import is_car_detail_request, parse_ask_ai_message


class TestCarDetailRequest:

    def test_english_detail(self):
        assert is_car_detail_request("tell me about this car") is True

    def test_urdu_detail(self):
        assert is_car_detail_request("اس گاڑی کے بارے میں بتائیں") is True

    def test_not_detail(self):
        assert is_car_detail_request("show me SUVs") is False


class TestParseAskAiMessage:

    def test_standard_format(self):
        text = (
            "Tell me about this car and answer my questions about it: "
            "2017 Toyota Aqua S (id 32), 65000 km, Automatic, White, Lahore, Rs 29.00 lac."
        )
        result = parse_ask_ai_message(text)
        assert result is not None
        assert result["year"] == 2017
        assert result["make"] == "Toyota"
        assert result["model"] == "Aqua"
        assert result["variant"] == "S"
        assert result["id"] == 32
        assert result["mileage"] == 65000
        assert result["city"] == "Lahore"
        assert result["price"] == 2_900_000

    def test_not_ask_ai(self):
        assert parse_ask_ai_message("show me Corolla") is None


# ═══════════════════════════════════════════════════════════════
# 4. SELECTION PARSING
# ═══════════════════════════════════════════════════════════════

from app.services.helpers import parse_selection, is_detail_or_selection


class TestParseSelection:

    SAMPLE_CARS = [
        {"make": "Honda", "model": "Civic", "variant": "VTi", "year": 2018,
         "price": 3900000, "city": "Karachi"},
        {"make": "Honda", "model": "Civic", "variant": "Oriel", "year": 2023,
         "price": 7200000, "city": "Lahore"},
        {"make": "Toyota", "model": "Corolla", "variant": "Altis Grande",
         "year": 2021, "price": 5500000, "city": "Islamabad"},
    ]

    # ── Variant match (highest priority) ──
    def test_oriel_matches_variant_not_first_civic(self):
        idx = parse_selection("Mujhe Civic Oriel pasand hai", self.SAMPLE_CARS)
        assert idx == 1

    def test_vti_matches_its_variant(self):
        assert parse_selection("I want the VTi", self.SAMPLE_CARS) == 0

    def test_altis_grande_matches(self):
        assert parse_selection("Altis Grande dikhao", self.SAMPLE_CARS) == 2

    # ── Model match ──
    def test_corolla_matches_model(self):
        assert parse_selection("I like the Corolla", self.SAMPLE_CARS) == 2

    # ── Positional ──
    def test_first_one(self):
        assert parse_selection("first one", self.SAMPLE_CARS) == 0

    def test_pehli(self):
        assert parse_selection("pehli wali", self.SAMPLE_CARS) == 0

    def test_second(self):
        assert parse_selection("second one", self.SAMPLE_CARS) == 1

    def test_third(self):
        assert parse_selection("third car", self.SAMPLE_CARS) == 2

    def test_second_with_one_car(self):
        assert parse_selection("second one", [self.SAMPLE_CARS[0]]) is None

    # ── Demonstrative ──
    def test_this_one(self):
        assert parse_selection("this one is nice", self.SAMPLE_CARS) == 0

    def test_negated(self):
        assert parse_selection("ye nahi chahiye", self.SAMPLE_CARS) is None

    # ── Edge cases ──
    def test_empty_cars(self):
        assert parse_selection("first one", []) is None

    def test_unrelated(self):
        assert parse_selection("what's the weather", self.SAMPLE_CARS) is None


class TestIsDetailOrSelection:

    def test_pasand(self):
        assert is_detail_or_selection("ye pasand hai") is True

    def test_this_one(self):
        assert is_detail_or_selection("I like this one") is True

    def test_details(self):
        assert is_detail_or_selection("tell me the details") is True

    def test_unrelated(self):
        assert is_detail_or_selection("what is your name") is False


# ═══════════════════════════════════════════════════════════════
# 5. PHASE RESET DETECTION
# ═══════════════════════════════════════════════════════════════

from app.services.conversation import _should_reset_to_searching


class TestPhaseReset:

    SELECTED_SPORTAGE = {
        "make": "KIA", "model": "Sportage", "variant": "AWD",
        "year": 2021, "price": 8200000, "city": "Karachi",
        "body_type": "SUV",
    }

    SELECTED_CIVIC = {
        "make": "Honda", "model": "Civic", "variant": "VTi",
        "year": 2018, "price": 3900000, "city": "Karachi",
        "body_type": "Sedan",
    }

    # ── Should reset (model check fires BEFORE token length check) ──
    def test_different_model_fortuner(self):
        assert _should_reset_to_searching("Fortuner legend", self.SELECTED_SPORTAGE) is True

    def test_different_model_corolla(self):
        assert _should_reset_to_searching("Corolla 2020 dikhao", self.SELECTED_SPORTAGE) is True

    def test_show_me_intent(self):
        assert _should_reset_to_searching(
            "Achcha Mujhe Koi City bhi dikhayen jo Lahore mein ho",
            self.SELECTED_SPORTAGE,
        ) is True

    def test_search_intent(self):
        assert _should_reset_to_searching("find me an Alto in Multan", self.SELECTED_SPORTAGE) is True

    def test_dikhao_intent(self):
        assert _should_reset_to_searching(
            "ji main aapki database Mein jitni bhi SUV padi hai mujhe Sara dikha de",
            self.SELECTED_CIVIC,
        ) is True

    def test_different_body_type(self):
        assert _should_reset_to_searching("SUV dikhao please", self.SELECTED_CIVIC) is True

    def test_chahiye_intent(self):
        assert _should_reset_to_searching("mujhe Honda City chahiye", self.SELECTED_SPORTAGE) is True

    # ── Should NOT reset ──
    def test_short_reply_name(self):
        assert _should_reset_to_searching("Ahmad Ansari", self.SELECTED_SPORTAGE) is False

    def test_short_reply_phone(self):
        assert _should_reset_to_searching("03001234567", self.SELECTED_SPORTAGE) is False

    def test_short_reply_time(self):
        assert _should_reset_to_searching("6:00 PM", self.SELECTED_SPORTAGE) is False

    def test_short_reply_yes(self):
        assert _should_reset_to_searching("haan", self.SELECTED_SPORTAGE) is False

    def test_inspection_yes(self):
        assert _should_reset_to_searching("yes book", self.SELECTED_SPORTAGE) is False

    def test_same_body_type(self):
        assert _should_reset_to_searching("SUV pasand hai", self.SELECTED_SPORTAGE) is False

    def test_no_selected_car(self):
        # 5+ tokens, no model, no car → should reset since selected_car is None
        assert _should_reset_to_searching("show me some good cars please", None) is True

    def test_no_selected_car_short(self):
        # Short message, no model → should NOT reset (likely inspection answer)
        assert _should_reset_to_searching("ok thanks", None) is False


# ═══════════════════════════════════════════════════════════════
# 6. BODY TYPE OVERRIDE
# ═══════════════════════════════════════════════════════════════

from app.services.overrides import apply_overrides
from app.core.utils import slot_value as util_slot_value


class TestBodyTypeOverride:

    def test_suv_sets_body_type(self):
        slots = {}
        apply_overrides("show me all SUV cars", slots, 1)
        assert util_slot_value(slots, "body_type") == "SUV"

    def test_sedan_sets_body_type(self):
        slots = {}
        apply_overrides("sedan chahiye", slots, 1)
        assert util_slot_value(slots, "body_type") == "Sedan"

    def test_hatchback_sets_body_type(self):
        slots = {}
        apply_overrides("hatchback dikhao", slots, 1)
        assert util_slot_value(slots, "body_type") == "Hatchback"

    def test_user_said_body_not_overwritten_by_model(self):
        slots = {}
        apply_overrides("Civic SUV dikhao", slots, 1)
        assert util_slot_value(slots, "body_type") == "SUV"


# ═══════════════════════════════════════════════════════════════
# 7. MAKE OVERRIDE
# ═══════════════════════════════════════════════════════════════

class TestMakeOverride:

    def test_kia_sets_make(self):
        slots = {}
        apply_overrides("show me all Kia cars", slots, 1)
        assert util_slot_value(slots, "make") == "KIA"

    def test_toyota_sets_make(self):
        slots = {}
        apply_overrides("Toyota ki gaariyan dikhao", slots, 1)
        assert util_slot_value(slots, "make") == "Toyota"


# ═══════════════════════════════════════════════════════════════
# 8. MODEL OVERRIDE
# ═══════════════════════════════════════════════════════════════

class TestModelOverride:

    def test_corolla_sets_model_and_make(self):
        slots = {}
        apply_overrides("Corolla Lahore 40 lakh", slots, 1)
        assert util_slot_value(slots, "model") == "Corolla"
        assert util_slot_value(slots, "make") == "Toyota"

    def test_civic_sets_model(self):
        slots = {}
        apply_overrides("civic chahiye automatic", slots, 1)
        assert util_slot_value(slots, "model") == "Civic"
        assert util_slot_value(slots, "make") == "Honda"

    def test_model_switch_with_negation(self):
        slots = {
            "make": {"value": "Toyota", "source": "said"},
            "model": {"value": "Corolla", "source": "said"},
        }
        apply_overrides("Corolla nahi, Civic dikhao", slots, 2)
        assert util_slot_value(slots, "model") == "Civic"
        assert util_slot_value(slots, "make") == "Honda"

    def test_fortuner(self):
        slots = {}
        apply_overrides("Fortuner legend Karachi", slots, 1)
        assert util_slot_value(slots, "model") == "Fortuner"
        assert util_slot_value(slots, "make") == "Toyota"


# ═══════════════════════════════════════════════════════════════
# 9. CITY OVERRIDE (with negation)
# ═══════════════════════════════════════════════════════════════

class TestCityOverride:

    def test_lahore(self):
        slots = {}
        apply_overrides("Corolla Lahore 40 lakh", slots, 1)
        assert util_slot_value(slots, "city") == "Lahore"

    def test_karachi(self):
        slots = {}
        apply_overrides("Karachi mein SUV dikhao", slots, 1)
        assert util_slot_value(slots, "city") == "Karachi"

    def test_city_correction_karachi_nahi_lahore(self):
        """'Karachi nahi, Lahore mein chahiye' → Lahore (Karachi is negated)."""
        slots = {"city": {"value": "Karachi", "source": "said"}}
        apply_overrides("sorry Karachi nahi, Lahore mein chahiye", slots, 2)
        assert util_slot_value(slots, "city") == "Lahore"

    def test_city_correction_lahore_not_karachi(self):
        """'Lahore mein dhundna hai, Karachi nahi' → Lahore (Karachi negated)."""
        slots = {"city": {"value": "Karachi", "source": "said"}}
        apply_overrides("Lahore mein dhundna hai, Karachi nahi", slots, 2)
        assert util_slot_value(slots, "city") == "Lahore"

    def test_city_correction_actually_lahore(self):
        """'actually Lahore mein dhundna hai' → Lahore."""
        slots = {"city": {"value": "Karachi", "source": "said"}}
        apply_overrides("actually Lahore mein dhundna hai", slots, 2)
        assert util_slot_value(slots, "city") == "Lahore"


# ═══════════════════════════════════════════════════════════════
# 10. TRANSMISSION OVERRIDE
# ═══════════════════════════════════════════════════════════════

class TestTransmissionOverride:

    def test_automatic(self):
        slots = {}
        apply_overrides("automatic Civic dikhao", slots, 1)
        assert util_slot_value(slots, "transmission") == "Automatic"

    def test_manual(self):
        slots = {}
        apply_overrides("manual Alto chahiye", slots, 1)
        assert util_slot_value(slots, "transmission") == "Manual"

    def test_manually_doesnt_trigger(self):
        slots = {}
        apply_overrides("I manually checked the car", slots, 1)
        assert util_slot_value(slots, "transmission") is None


# ═══════════════════════════════════════════════════════════════
# 11. COMBINED OVERRIDES
# ═══════════════════════════════════════════════════════════════

class TestCombinedOverrides:

    def test_corolla_lahore_40_lakh(self):
        slots = {}
        apply_overrides("Corolla Lahore 40 lakh", slots, 1)
        assert util_slot_value(slots, "model") == "Corolla"
        assert util_slot_value(slots, "make") == "Toyota"
        assert util_slot_value(slots, "city") == "Lahore"
        price = util_slot_value(slots, "price_max")
        assert price is not None
        assert int(price) == 4_000_000

    def test_suv_karachi(self):
        slots = {}
        apply_overrides("SUV Karachi mein dikhao", slots, 1)
        assert util_slot_value(slots, "body_type") == "SUV"
        assert util_slot_value(slots, "city") == "Karachi"


# ═══════════════════════════════════════════════════════════════
# 12. MISSING FILTERS
# ═══════════════════════════════════════════════════════════════

from app.services.helpers import missing_filters


class TestMissingFilters:

    def test_all_missing(self):
        missing = missing_filters({})
        assert "price_max" in missing
        assert "city" in missing
        assert "car_type" in missing

    def test_price_filled(self):
        slots = {"price_max": {"value": 4000000, "source": "said"}}
        assert "price_max" not in missing_filters(slots)

    def test_model_fills_car_type(self):
        slots = {
            "price_max": {"value": 4000000, "source": "said"},
            "city": {"value": "Lahore", "source": "said"},
            "model": {"value": "Corolla", "source": "said"},
        }
        assert len(missing_filters(slots)) == 0


# ═══════════════════════════════════════════════════════════════
# 13. CLAIMS NO CARS
# ═══════════════════════════════════════════════════════════════

from app.services.helpers import claims_no_cars


class TestClaimsNoCars:

    def test_english(self):
        assert claims_no_cars("Sorry, no car found") is True

    def test_not_available(self):
        assert claims_no_cars("This model is not available") is True

    def test_urdu_nahi_hai(self):
        assert claims_no_cars("یہ گاڑی دستیاب نہیں ہے") is True

    def test_normal_reply(self):
        assert claims_no_cars("Here are 3 great options!") is False


# ═══════════════════════════════════════════════════════════════
# 14. SLOTS TO FILTERS
# ═══════════════════════════════════════════════════════════════

from app.services.helpers import slots_to_filters


class TestSlotsToFilters:

    def test_basic(self):
        slots = {
            "make": {"value": "Toyota", "source": "said"},
            "city": {"value": "Lahore", "source": "said"},
        }
        f = slots_to_filters(slots)
        assert f["make"] == "Toyota"
        assert f["city"] == "Lahore"

    def test_skips_internal(self):
        slots = {"make": {"value": "Toyota", "source": "said"}, "_last_shown": []}
        assert "_last_shown" not in slots_to_filters(slots)


# ═══════════════════════════════════════════════════════════════
# 15. WANTS INSPECTION
# ═══════════════════════════════════════════════════════════════

from app.services.helpers import wants_inspection


class TestWantsInspection:

    def test_book_inspection(self):
        assert wants_inspection("book an inspection") is True

    def test_karwao(self):
        assert wants_inspection("inspection karwao") is True

    def test_not_inspection(self):
        assert wants_inspection("tell me the price") is False


# ═══════════════════════════════════════════════════════════════
# 16. GREETING REPLY LANGUAGE
# ═══════════════════════════════════════════════════════════════

from app.services.handlers import greeting_reply


class TestGreetingReply:

    def test_english_hello(self):
        reply = greeting_reply("hello", "en")
        assert "Hello" in reply

    def test_urdu_salam(self):
        reply = greeting_reply("salam", "ur")
        assert "وعلیکم" in reply

    def test_english_thanks(self):
        reply = greeting_reply("thanks", "en")
        assert "welcome" in reply.lower()


# ═══════════════════════════════════════════════════════════════
# 17. QUICK EXTRACT
# ═══════════════════════════════════════════════════════════════

from app.services.overrides import quick_extract


class TestQuickExtract:

    def test_extracts_city(self):
        assert quick_extract("Civic in Lahore", {}, {}).get("city") == "Lahore"

    def test_extracts_model(self):
        f = quick_extract("show me Corolla", {}, {})
        assert f.get("make") == "Toyota"
        assert f.get("model") == "Corolla"

    def test_extracts_body_type(self):
        assert quick_extract("SUV chahiye", {}, {}).get("body_type") == "SUV"

    def test_negated_city_skipped(self):
        """'Karachi nahi, Lahore' → Lahore."""
        f = quick_extract("Karachi nahi, Lahore mein dikhao", {"city": "Karachi"}, {})
        assert f.get("city") == "Lahore"


# ═══════════════════════════════════════════════════════════════
# 18. EDGE CASES
# ═══════════════════════════════════════════════════════════════

class TestEdgeCases:

    def test_empty_text(self):
        assert detect_language("") is None
        assert is_greeting("") is True
        assert is_car_detail_request("") is False

    def test_unicode_numbers(self):
        assert detect_language("۳۵ لاکھ") == "ur"

    def test_multiple_models_negation(self):
        slots = {}
        apply_overrides("Corolla nahi, Civic chahiye", slots, 1)
        assert util_slot_value(slots, "model") == "Civic"

    def test_mixed_case(self):
        slots = {}
        apply_overrides("COROLLA LAHORE AUTOMATIC", slots, 1)
        assert util_slot_value(slots, "model") == "Corolla"
        assert util_slot_value(slots, "city") == "Lahore"
        assert util_slot_value(slots, "transmission") == "Automatic"

    def test_special_characters(self):
        assert detect_language("salam!!!") == "ur"
        assert is_greeting("hello???") is True