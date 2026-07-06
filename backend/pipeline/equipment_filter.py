# backend/pipeline/equipment_filter.py
"""
Filters retrieved exercises against the user's selected equipment.

Primary check: the canonical equipment_<slug> boolean fields written by
pipeline/normalize.py at ingest time. Legacy name-inference fallback for
cable/machine kept as a defensive net for freeexdb rows where ingest
didn't tag equipment correctly (out of the normalization spec's scope).
"""

_NAME_INFERRED_EQUIPMENT = {"cable", "machine"}


def _slug(equipment_name: str) -> str:
    return equipment_name.lower().replace("-", "_").replace(" ", "_")


def filter_by_equipment(exercises: list[dict], user_equipment: list[str]) -> list[dict]:
    if not user_equipment:
        return exercises

    selected_slugs = {_slug(e) for e in user_equipment}
    selected_lower = {e.lower() for e in user_equipment}
    name_check = selected_lower & _NAME_INFERRED_EQUIPMENT

    result = []
    for ex in exercises:
        # Primary check: canonical boolean fields.
        if any(ex.get(f"equipment_{s}") for s in selected_slugs):
            result.append(ex)
            continue
        # Defensive fallback: cable/machine untagged in some freeexdb rows.
        if name_check:
            name_lower = ex.get("name", "").lower()
            if any(equip in name_lower for equip in name_check):
                result.append(ex)
    return result
