from unittest.mock import patch

def make_chroma_result(names: list[str]):
    return {
        "ids": [[str(i) for i in range(len(names))]],
        "metadatas": [[{"name": n, "category": "Arms", "muscles": "Biceps brachii",
                        "muscles_secondary": "", "equipment": "Dumbbell",
                        "description": "test"} for n in names]],
        "distances": [[0.1] * len(names)],
    }

def test_retrieve_exercises_returns_list():
    from pipeline.exercise_retriever import retrieve_exercises
    mock_result = make_chroma_result(["Bicep Curl", "Hammer Curl"])
    with patch("pipeline.exercise_retriever.query_collection", return_value=mock_result):
        result = retrieve_exercises(["biceps"], "hypertrophy", n_results=20)
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["name"] == "Bicep Curl"

def test_retrieve_exercises_query_uses_muscles():
    from pipeline.exercise_retriever import retrieve_exercises
    mock_result = make_chroma_result([])
    mock_result["ids"] = [[]]
    mock_result["metadatas"] = [[]]
    mock_result["distances"] = [[]]
    with patch("pipeline.exercise_retriever.query_collection", return_value=mock_result) as mock_q:
        retrieve_exercises(["biceps", "triceps"], "hypertrophy")
    call_args = mock_q.call_args
    assert "biceps" in call_args[0][1].lower() or "biceps" in str(call_args)
