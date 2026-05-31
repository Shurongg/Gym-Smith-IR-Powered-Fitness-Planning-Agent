from pipeline.equipment_filter import filter_by_equipment

EXERCISES = [
    {"name": "Bicep Curl", "equipment": "dumbbell"},
    {"name": "Barbell Row", "equipment": "barbell"},
    {"name": "Pull-up", "equipment": "pull-up bar"},
    {"name": "Push-up", "equipment": "bodyweight"},
    {"name": "Cable Fly", "equipment": "cable"},
    {"name": "Combo", "equipment": "barbell, dumbbell"},
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
