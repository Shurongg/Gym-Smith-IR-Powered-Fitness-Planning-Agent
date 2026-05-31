from data.freeexdb_client import normalize_equipment, _parse_exercise

def test_normalize_known_values():
    assert normalize_equipment("Dumbbell") == "dumbbell"
    assert normalize_equipment("body only") == "bodyweight"
    assert normalize_equipment("cable") == "cable"
    assert normalize_equipment("machine") == "machine"
    assert normalize_equipment("bands") == "resistance band"
    assert normalize_equipment("SZ-Bar") == "barbell"
    assert normalize_equipment("None") == "bodyweight"
    assert normalize_equipment("none (bodyweight exercise)") == "bodyweight"
    assert normalize_equipment("Gym mat") == "bodyweight"
    assert normalize_equipment("e-z curl bar") == "barbell"

def test_normalize_unknown_returns_none():
    assert normalize_equipment("swiss ball") is None
    assert normalize_equipment("foam roll") is None
    assert normalize_equipment("medicine ball") is None
    assert normalize_equipment("other") is None

def test_normalize_case_insensitive():
    assert normalize_equipment("DUMBBELL") == "dumbbell"
    assert normalize_equipment("Cable") == "cable"
    assert normalize_equipment("MACHINE") == "machine"

def test_parse_exercise_valid():
    raw = {
        "id": "0001",
        "name": "Cable Curl",
        "equipment": "cable",
        "primaryMuscles": ["biceps"],
        "secondaryMuscles": ["forearms"],
        "instructions": ["Step 1", "Step 2", "Step 3", "Step 4"],
        "category": "strength",
    }
    result = _parse_exercise(raw)
    assert result is not None
    assert result["exercise_id"] == "fex_0001"
    assert result["equipment"] == ["cable"]
    assert result["muscles"] == ["biceps"]
    assert result["muscles_secondary"] == ["forearms"]
    assert "Step 4" not in result["description"]  # only first 3 steps

def test_parse_exercise_unknown_equipment_returns_none():
    raw = {
        "id": "0002", "name": "Foam Roll Exercise", "equipment": "foam roll",
        "primaryMuscles": [], "secondaryMuscles": [], "instructions": [], "category": "other",
    }
    assert _parse_exercise(raw) is None
