def filter_by_equipment(exercises: list[dict], user_equipment: list[str]) -> list[dict]:
    """Keep exercises whose equipment is in user_equipment or is bodyweight (None)."""
    allowed = {e.lower() for e in user_equipment} | {"none"}
    return [
        ex for ex in exercises
        if ex.get("equipment", "").lower() in allowed
    ]
