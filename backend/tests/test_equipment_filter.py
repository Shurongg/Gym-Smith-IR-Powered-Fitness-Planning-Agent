from pipeline.equipment_filter import filter_by_equipment

def _ex(name: str, **eq_booleans) -> dict:
    """Build a fixture exercise with all 9 equipment_* booleans defaulting False."""
    base = {
        "equipment_barbell": False, "equipment_bench": False,
        "equipment_dumbbell": False, "equipment_pull_up_bar": False,
        "equipment_bodyweight": False, "equipment_cable": False,
        "equipment_kettlebell": False, "equipment_machine": False,
        "equipment_resistance_band": False,
    }
    base.update(eq_booleans)
    return {"name": name, **base}


EXERCISES = [
    _ex("Bicep Curl", equipment_dumbbell=True),
    _ex("Barbell Row", equipment_barbell=True),
    _ex("Pull-up", equipment_pull_up_bar=True),
    _ex("Push-up", equipment_bodyweight=True),
    _ex("Cable Fly", equipment_cable=True),
    _ex("Combo", equipment_barbell=True, equipment_dumbbell=True),
]

def test_filter_keeps_matching_equipment():
    result = filter_by_equipment(EXERCISES, ["dumbbell"])
    names = [e["name"] for e in result]
    assert "Bicep Curl" in names
    assert "Barbell Row" not in names
    assert "Cable Fly" not in names

def test_filter_excludes_bodyweight_when_not_selected():
    result = filter_by_equipment(EXERCISES, ["dumbbell"])
    names = [e["name"] for e in result]
    assert "Push-up" not in names

def test_filter_includes_bodyweight_when_selected():
    result = filter_by_equipment(EXERCISES, ["dumbbell", "bodyweight"])
    names = [e["name"] for e in result]
    assert "Push-up" in names

def test_filter_case_insensitive():
    result = filter_by_equipment(EXERCISES, ["DUMBBELL"])
    names = [e["name"] for e in result]
    assert "Bicep Curl" in names

def test_filter_multiple_equipment():
    result = filter_by_equipment(EXERCISES, ["dumbbell", "barbell"])
    names = [e["name"] for e in result]
    assert "Bicep Curl" in names
    assert "Barbell Row" in names
    assert "Cable Fly" not in names

def test_filter_empty_returns_all():
    result = filter_by_equipment(EXERCISES, [])
    assert len(result) == len(EXERCISES)

def test_filter_multi_value_exercise_matches_any():
    result = filter_by_equipment(EXERCISES, ["dumbbell"])
    names = [e["name"] for e in result]
    assert "Combo" in names  # has "barbell, dumbbell" — dumbbell matches

def test_filter_multi_value_exercise_excluded_when_no_match():
    result = filter_by_equipment(EXERCISES, ["cable"])
    names = [e["name"] for e in result]
    assert "Combo" not in names  # barbell,dumbbell — neither is cable
