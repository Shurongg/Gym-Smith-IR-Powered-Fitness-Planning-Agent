from unittest.mock import patch


def make_chroma_result(names: list[str]):
    return {
        "ids": [[str(i) for i in range(len(names))]],
        "metadatas": [[{"name": n, "category": "Arms", "muscles": "Biceps brachii",
                        "muscles_secondary": "", "equipment": "dumbbell",
                        "description": "test"} for n in names]],
        "distances": [[0.1] * len(names)],
    }


EMPTY_RESULT = make_chroma_result([])


def test_retrieve_exercises_returns_list():
    from pipeline.exercise_retriever import retrieve_exercises
    mock_result = make_chroma_result(["Bicep Curl", "Hammer Curl"])
    with patch("pipeline.exercise_retriever.query_collection", return_value=mock_result):
        result = retrieve_exercises(["biceps"], "hypertrophy")
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["name"] == "Bicep Curl"


def test_retrieve_exercises_queries_each_muscle():
    from pipeline.exercise_retriever import retrieve_exercises
    with patch("pipeline.exercise_retriever.query_collection", return_value=EMPTY_RESULT) as mock_q:
        retrieve_exercises(["biceps", "triceps"], "hypertrophy")
    queries = [call[0][1] for call in mock_q.call_args_list]
    assert any("biceps" in q.lower() for q in queries)
    assert any("triceps" in q.lower() for q in queries)
    assert mock_q.call_count == 2


def test_retrieve_exercises_deduplicates():
    from pipeline.exercise_retriever import retrieve_exercises
    mock_result = make_chroma_result(["Bicep Curl"])
    with patch("pipeline.exercise_retriever.query_collection", return_value=mock_result):
        result = retrieve_exercises(["biceps", "triceps"], "hypertrophy")
    assert len(result) == 1


def test_retrieve_exercises_includes_specific_machines():
    from pipeline.exercise_retriever import retrieve_exercises
    with patch("pipeline.exercise_retriever.query_collection", return_value=EMPTY_RESULT) as mock_q:
        retrieve_exercises(["biceps"], "hypertrophy", specific_machines=["Preacher Curl Machine"])
    queries = [call[0][1] for call in mock_q.call_args_list]
    assert any("Preacher Curl Machine" in q for q in queries)
    assert mock_q.call_count == 2  # 1 muscle + 1 machine


def test_retrieve_exercises_fallback_when_no_muscles():
    from pipeline.exercise_retriever import retrieve_exercises
    with patch("pipeline.exercise_retriever.query_collection", return_value=EMPTY_RESULT) as mock_q:
        retrieve_exercises([], "hypertrophy")
    assert mock_q.call_count == 1
    assert "hypertrophy" in mock_q.call_args[0][1]
