import pytest
import json
from unittest.mock import MagicMock
from pipeline.intent_parser import parse_intent, MEDICAL_FLAGS

def make_mock_client(response_json: dict):
    mock_msg = MagicMock()
    mock_msg.content = json.dumps(response_json)
    mock_choice = MagicMock()
    mock_choice.message = mock_msg
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    client = MagicMock()
    client.chat.completions.create.return_value = mock_response
    return client

def test_parse_returns_structured_intent():
    intent_data = {
        "target_muscles": ["biceps"],
        "equipment": ["dumbbell"],
        "frequency": 3,
        "intensity": "medium",
        "goal": "hypertrophy",
        "flags": [],
    }
    client = make_mock_client(intent_data)
    result = parse_intent(client, "I want to build arm muscles with dumbbells 3x/week")
    assert result["goal"] == "hypertrophy"
    assert "biceps" in result["target_muscles"]
    assert result["flags"] == []

def test_medical_flag_detected():
    intent_data = {
        "target_muscles": [],
        "equipment": [],
        "frequency": 3,
        "intensity": "medium",
        "goal": "general",
        "flags": ["medical_concern"],
    }
    client = make_mock_client(intent_data)
    result = parse_intent(client, "I have a knee injury")
    assert "medical_concern" in result["flags"]

def test_medical_keywords_list_not_empty():
    assert len(MEDICAL_FLAGS) > 5
