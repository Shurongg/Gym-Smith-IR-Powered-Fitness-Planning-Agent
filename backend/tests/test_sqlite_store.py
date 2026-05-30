import pytest
import json

def test_init_creates_tables(temp_db):
    store = temp_db
    with store.get_connection() as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    names = {r[0] for r in tables}
    assert "users" in names
    assert "user_memory" in names
    assert "plan_history" in names

def test_create_user_returns_token(temp_db):
    token = temp_db.create_user()
    assert isinstance(token, str)
    assert len(token) == 36  # UUID format

def test_get_user_id_returns_id(temp_db):
    token = temp_db.create_user()
    user_id = temp_db.get_user_id(token)
    assert isinstance(user_id, int)

def test_get_user_id_unknown_token(temp_db):
    assert temp_db.get_user_id("nonexistent") is None

def test_upsert_and_get_user_memory(temp_db):
    token = temp_db.create_user()
    user_id = temp_db.get_user_id(token)
    temp_db.upsert_user_memory(user_id, ["dumbbell", "barbell"], "medium", "hypertrophy")
    mem = temp_db.get_user_memory(user_id)
    assert mem["equipment"] == ["dumbbell", "barbell"]
    assert mem["intensity_preference"] == "medium"
    assert mem["last_goal"] == "hypertrophy"

def test_upsert_user_memory_updates_existing(temp_db):
    token = temp_db.create_user()
    user_id = temp_db.get_user_id(token)
    temp_db.upsert_user_memory(user_id, ["dumbbell"], "low", "endurance")
    temp_db.upsert_user_memory(user_id, ["barbell"], "high", "strength")
    mem = temp_db.get_user_memory(user_id)
    assert mem["equipment"] == ["barbell"]
    assert mem["intensity_preference"] == "high"

def test_get_user_memory_no_memory(temp_db):
    token = temp_db.create_user()
    user_id = temp_db.get_user_id(token)
    assert temp_db.get_user_memory(user_id) is None

def test_save_and_get_plan_history(temp_db):
    token = temp_db.create_user()
    user_id = temp_db.get_user_id(token)
    plan = {"weekly_schedule": [{"day": "Day 1", "exercises": []}]}
    temp_db.save_plan(user_id, "I want to build arms", plan)
    history = temp_db.get_plan_history(user_id)
    assert len(history) == 1
    assert history[0]["user_input"] == "I want to build arms"
