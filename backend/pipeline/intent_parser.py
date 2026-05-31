"""Slim safety check: detect medical concerns only.

All training-related intent (target muscles, frequency, intensity, goal, equipment)
is now reasoned by the agent itself in Stage 1.  This module exists solely to
gate medical-concern requests with a deterministic safety net.
"""
import json
from openai import OpenAI

MEDICAL_FLAGS = [
    "injury", "injured", "pain", "hurt", "surgery", "recovering",
    "pregnant", "pregnancy", "illness", "sick", "disease", "disorder",
    "eating disorder", "chronic", "diabetes", "arthritis", "fracture",
    "doctor", "rehabilitation", "physical therapy",
]

_MEDICAL_CHECK_PROMPT = """Decide whether the user message implies a medical
concern (injury, pain, illness, pregnancy, chronic condition, rehabilitation,
or anything requiring a doctor / physical therapist).

Return ONLY valid JSON:
{"medical_concern": true|false}"""


def check_medical(client: OpenAI, user_input: str) -> dict:
    """Return {"flags": ["medical_concern"]} if concern detected, else {"flags": []}.

    Combines a hardcoded keyword scan (cheap, never misses obvious cases) with
    an LLM check (catches paraphrased descriptions).  Either trigger sets the flag.
    """
    flags: list[str] = []

    lower = user_input.lower()
    if any(kw in lower for kw in MEDICAL_FLAGS):
        flags.append("medical_concern")

    if "medical_concern" not in flags:
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": _MEDICAL_CHECK_PROMPT},
                    {"role": "user", "content": user_input},
                ],
                temperature=0,
                response_format={"type": "json_object"},
            )
            parsed = json.loads(response.choices[0].message.content)
            if parsed.get("medical_concern"):
                flags.append("medical_concern")
        except Exception:
            # If the LLM call fails, fall back to the keyword scan result.
            pass

    return {"flags": flags}
