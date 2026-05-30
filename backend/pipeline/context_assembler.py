import json

SYSTEM_PROMPT = """You are Gym Smith, a fitness planning assistant. You generate structured weekly training plans based on retrieved exercises and rules.

RESTRICTIONS — never do these:
- No medical advice or diagnosis
- No injury rehabilitation plans
- No precise calorie counting or macro calculations
- No supplement recommendations
- No body fat percentage predictions
- No guarantees of specific results

If the user mentions injury, pain, illness, pregnancy, or a medical condition, respond only with:
"This is outside Gym Smith's scope. Please consult a qualified professional."

OUTPUT FORMAT: Respond ONLY with valid JSON matching this exact schema:
{
  "goal_summary": "string",
  "equipment_needed": ["string"],
  "weekly_schedule": [
    {
      "day": "Day 1",
      "focus": "string",
      "exercises": [
        {
          "name": "string",
          "sets": 3,
          "reps": "10-12",
          "rest": "60s",
          "equipment": "string",
          "muscles": ["string"],
          "alternative": "string or null"
        }
      ]
    }
  ],
  "nutrition_notes": ["string"],
  "safety_reminder": "string"
}"""


def assemble_prompt(
    user_input: str,
    intent: dict,
    exercises: list[dict],
    rules: list[dict],
    memory: dict | None,
) -> str:
    parts = [f"USER REQUEST:\n{user_input}\n"]

    parts.append(f"PARSED INTENT:\n{json.dumps(intent, indent=2)}\n")

    parts.append("RETRIEVED EXERCISES:")
    for ex in exercises:
        parts.append(
            f"- {ex['name']} | Category: {ex['category']} | "
            f"Muscles: {ex['muscles']} | Equipment: {ex['equipment']} | "
            f"Description: {ex['description'][:200]}"
        )

    training_rules = [r for r in rules if r.get("type") != "nutrition_rule"]
    nutrition_rules = [r for r in rules if r.get("type") == "nutrition_rule"]

    parts.append("\nTRAINING RULES:")
    for r in training_rules:
        parts.append(f"- {r['title']}: {r['content']}")

    parts.append("\nNUTRITION RULES:")
    for r in nutrition_rules:
        parts.append(f"- {r['title']}: {r['content']}")

    if memory:
        parts.append(
            f"\nUSER MEMORY:\n"
            f"- Previous equipment: {memory.get('equipment', [])}\n"
            f"- Previous intensity: {memory.get('intensity_preference', 'unknown')}\n"
            f"- Previous goal: {memory.get('last_goal', 'unknown')}"
        )
    else:
        parts.append("\nUSER MEMORY: No previous session found.")

    return "\n".join(parts)
