import json
from openai import OpenAI

MEDICAL_FLAGS = [
    "injury", "injured", "pain", "hurt", "surgery", "recovering",
    "pregnant", "pregnancy", "illness", "sick", "disease", "disorder",
    "eating disorder", "chronic", "diabetes", "arthritis", "fracture",
    "doctor", "rehabilitation", "physical therapy",
]

_PARSE_SYSTEM = """Extract training intent from the user message. Return ONLY valid JSON:
{
  "target_muscles": ["string"],
  "equipment": ["string"],
  "frequency": integer,
  "intensity": "low"|"medium"|"high",
  "goal": "hypertrophy"|"strength"|"endurance"|"general"|"fat_loss",
  "flags": []
}

Rules:
- target_muscles: use English anatomy names (biceps, triceps, pectoralis, latissimus dorsi, quadriceps, etc.)
- equipment: normalize to: dumbbell, barbell, cable, pull-up bar, resistance band, kettlebell, bench, bodyweight, none
- frequency: default 3 if not specified
- intensity: default "medium" if not specified
- flags: add "medical_concern" if user mentions injury, pain, illness, pregnancy, or medical condition"""


def parse_intent(client: OpenAI, user_input: str) -> dict:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": _PARSE_SYSTEM},
            {"role": "user", "content": user_input},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )
    intent = json.loads(response.choices[0].message.content)

    lower_input = user_input.lower()
    if any(kw in lower_input for kw in MEDICAL_FLAGS):
        if "medical_concern" not in intent.get("flags", []):
            intent.setdefault("flags", []).append("medical_concern")

    return intent
