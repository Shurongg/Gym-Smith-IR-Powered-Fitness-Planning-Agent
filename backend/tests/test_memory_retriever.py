from pipeline.memory_retriever import retrieve_memory

def test_retrieve_memory_returns_data(temp_db):
    token = temp_db.create_user()
    user_id = temp_db.get_user_id(token)
    temp_db.upsert_user_memory(user_id, ["dumbbell"], "medium", "hypertrophy")
    memory = retrieve_memory(user_id)
    assert memory["equipment"] == ["dumbbell"]
    assert memory["intensity_preference"] == "medium"

def test_retrieve_memory_no_user(temp_db):
    assert retrieve_memory(9999) is None
