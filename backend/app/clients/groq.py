"""
app/clients/groq.py

LLM client — tool calling mode + Whisper transcription.
"""

from __future__ import annotations

import json
import traceback
from typing import Optional

from openai import OpenAI

from app.core.config import settings
from app.prompts import BUY_SYSTEM_PROMPT

_client: Optional[OpenAI] = None

# Domain vocabulary only — no Roman Urdu steering. Whisper detects the
# language itself; forcing language="ur" mangled every English utterance.
WHISPER_PROMPT = (
    "PakWheels Pakistan used cars. "
    "Corolla, Civic, City, Cultus, Alto, Wagon R, Vitz, Prius, Alsvin, "
    "Sportage, Fortuner, Tucson, Oriel, Altis Grande, GLi, XLi, VXR, VXL, "
    "AGS, Jewela, Lumiere, BR-V, Yaris, Aqua, Mehran, Swift, "
    "Lahore, Karachi, Islamabad, Rawalpindi, Faisalabad, Multan, Peshawar, "
    "lakh, crore, inspection, لاکھ, کروڑ, گاڑی"
)

# Urdu script or English only. No Roman Urdu anywhere in user-facing output.
FALLBACK_QUESTIONS = {
    "en": {
        "price_max": "What is your budget?",
        "city": "Which city are you looking in?",
        "car_type": "What type of car do you want — sedan, hatchback, or SUV?",
        "_default": "Tell me a little more about what you need.",
    },
    "ur": {
        "price_max": "آپ کا بجٹ کتنا ہے؟",
        "city": "کس شہر میں ڈھونڈ رہے ہیں؟",
        "car_type": "کس قسم کی گاڑی چاہیے — سیڈان، ہیچ بیک یا ایس یو وی؟",
        "_default": "ذرا اور بتائیں کہ آپ کو کیا چاہیے۔",
    },
}


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.GROQ_API_KEY, base_url=settings.GROQ_BASE_URL)
    return _client


def call_with_tools(
    text: str,
    current_slots: dict,
    missing: list[str],
    catalog_context: str,
    number_hints: str,
    history: list[dict],
    tools: list[dict],
    language: str = "en",
) -> dict:
    """Call the LLM with tool definitions. Returns tool_calls or fallback_reply."""

    slot_summary = ", ".join(
        f"{k}={v.get('value', v) if isinstance(v, dict) else v}"
        for k, v in current_slots.items()
        if not k.startswith("_")
    ) or "(none yet)"

    user_message = (
        f"=== SESSION STATE ===\n"
        f"Active filters: {slot_summary}\n"
        f"Still needed: {', '.join(missing) if missing else '(none — present results)'}\n"
        f"\n{catalog_context}\n"
        f"{number_hints}\n\n"
        f'BUYER SAID: "{text}"\n'
        f"\nUse the available tools to process this turn. "
        f"Call update_slots first if needed, then determine_action LAST."
    )

    messages = [{"role": "system", "content": BUY_SYSTEM_PROMPT}]
    for turn in history[-12:]:
        messages.append({
            "role": "user" if turn["role"] == "user" else "assistant",
            "content": turn["text"] or "",
        })
    messages.append({"role": "user", "content": user_message})

    try:
        response = _get_client().chat.completions.create(
            model=settings.LLM_MODEL,
            messages=messages,
            temperature=settings.LLM_TEMPERATURE,
            tools=tools,
            tool_choice="auto",
            max_tokens=800,
        )

        message = response.choices[0].message
        tool_calls = message.tool_calls or []

        parsed_calls = []
        for tc in tool_calls:
            try:
                args = json.loads(tc.function.arguments)
                parsed_calls.append({
                    "name": tc.function.name,
                    "arguments": args,
                    "id": tc.id,
                })
            except json.JSONDecodeError as e:
                print(f"[GROQ ERROR] bad args for {tc.function.name}: {e}")

        if not parsed_calls and message.content:
            return {"tool_calls": [], "fallback_reply": message.content.strip()}

        return {"tool_calls": parsed_calls}

    except Exception as e:
        print(f"[GROQ ERROR] {e}")
        traceback.print_exc()
        field = missing[0] if missing else "car_type"
        bank = FALLBACK_QUESTIONS.get(language, FALLBACK_QUESTIONS["en"])
        return {
            "tool_calls": [],
            "fallback_reply": bank.get(field, bank["_default"]),
        }


def transcribe(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    from io import BytesIO
    audio_file = BytesIO(audio_bytes)
    audio_file.name = filename
    response = _get_client().audio.transcriptions.create(
        model=settings.STT_MODEL,
        file=audio_file,
        prompt=WHISPER_PROMPT,
    )
    return response.text
