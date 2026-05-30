from pipeline.equipment_filter import filter_by_equipment

EXERCISES = [
    {"name": "Bicep Curl", "equipment": "Dumbbell"},
    {"name": "Barbell Row", "equipment": "Barbell"},
    {"name": "Pull-up", "equipment": "Pull-up bar"},
    {"name": "Push-up", "equipment": "None"},
    {"name": "Cable Fly", "equipment": "Cable"},
]

def test_filter_keeps_matching_equipment():
    result = filter_by_equipment(EXERCISES, ["dumbbell"])
    names = [e["name"] for e in result]
    assert "Bicep Curl" in names
    assert "Barbell Row" not in names

def test_filter_always_includes_bodyweight():
    result = filter_by_equipment(EXERCISES, ["dumbbell"])
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

def test_filter_empty_user_equipment_returns_bodyweight_only():
    result = filter_by_equipment(EXERCISES, [])
    names = [e["name"] for e in result]
    assert names == ["Push-up"]
