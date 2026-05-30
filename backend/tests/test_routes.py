import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import json

@pytest.fixture
def client(temp_db, tmp_path, monkeypatch):
    import db.chroma_store as cs
    monkeypatch.setattr(cs, "CHROMA_PATH", str(tmp_path / "chroma"))
    cs._client = None
    with patch("main.init_knowledge_base", new_callable=AsyncMock):
        from main import app
        with TestClient(app) as c:
            yield c

def test_create_session(client):
    response = client.post("/api/session")
    assert response.status_code == 200
    data = response.json()
    assert "session_token" in data
    assert len(data["session_token"]) == 36

def test_validate_key_invalid(client):
    with patch("main.OpenAI") as mock_cls:
        instance = MagicMock()
        instance.models.list.side_effect = Exception("Invalid API key")
        mock_cls.return_value = instance
        response = client.post("/api/validate-key", json={"api_key": "bad-key"})
    assert response.status_code == 200
    assert response.json()["valid"] is False

def test_validate_key_valid(client):
    with patch("main.OpenAI") as mock_cls:
        instance = MagicMock()
        instance.models.list.return_value = MagicMock()
        mock_cls.return_value = instance
        response = client.post("/api/validate-key", json={"api_key": "sk-valid"})
    assert response.status_code == 200
    assert response.json()["valid"] is True

def test_get_session_memory(client):
    token_resp = client.post("/api/session")
    token = token_resp.json()["session_token"]
    response = client.get(f"/api/session/{token}")
    assert response.status_code == 200
    data = response.json()
    assert "memory" in data
    assert "history" in data

def test_generate_plan_medical_concern(client):
    token = client.post("/api/session").json()["session_token"]
    with patch("main.parse_intent") as mock_parse:
        mock_parse.return_value = {
            "target_muscles": [], "equipment": [], "frequency": 3,
            "intensity": "medium", "goal": "general", "flags": ["medical_concern"]
        }
        response = client.post("/api/plan", json={
            "session_token": token,
            "api_key": "sk-test",
            "user_input": "I have a knee injury"
        })
    assert response.status_code == 200
    data = response.json()
    assert data["is_medical_concern"] is True
    assert "professional" in data["message"].lower()
