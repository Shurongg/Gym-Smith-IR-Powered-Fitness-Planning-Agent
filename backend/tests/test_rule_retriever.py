from unittest.mock import patch

def make_rule_result(rules: list[dict]):
    return {
        "ids": [[r["id"] for r in rules]],
        "metadatas": [rules],
        "distances": [[0.1] * len(rules)],
    }

def test_retrieve_rules_returns_training_and_nutrition():
    from pipeline.rule_retriever import retrieve_rules
    training = [{"id": "tp1", "type": "training_principle", "title": "Progressive Overload",
                 "content": "Increase weight.", "tags": "hypertrophy"}]
    nutrition = [{"id": "nr1", "type": "nutrition_rule", "title": "Protein Intake",
                  "content": "1.6g/kg.", "tags": "protein"}]
    with patch("pipeline.rule_retriever.query_collection") as mock_q:
        mock_q.side_effect = [make_rule_result(training), make_rule_result(nutrition)]
        result = retrieve_rules("hypertrophy")
    assert len(result) == 2
    types = {r["type"] for r in result}
    assert "training_principle" in types
    assert "nutrition_rule" in types
