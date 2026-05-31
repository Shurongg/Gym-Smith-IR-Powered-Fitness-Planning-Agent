# wger often leaves cable/machine exercises untagged, so they land as "bodyweight" in ChromaDB.
# For these two types we also accept exercises whose name mentions the equipment word.
_NAME_INFERRED_EQUIPMENT = {"cable", "machine"}


def filter_by_equipment(exercises: list[dict], user_equipment: list[str]) -> list[dict]:
    if not user_equipment:
        return exercises

    allowed = {e.lower() for e in user_equipment}
    name_check = allowed & _NAME_INFERRED_EQUIPMENT

    result = []
    for ex in exercises:
        eq_str = ex.get("equipment", "bodyweight")
        ex_equip = {e.strip().lower() for e in eq_str.split(",")}
        if ex_equip & allowed:
            result.append(ex)
        elif name_check:
            name_lower = ex.get("name", "").lower()
            if any(equip in name_lower for equip in name_check):
                result.append(ex)
    return result
