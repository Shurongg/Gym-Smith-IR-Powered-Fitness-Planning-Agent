import pytest
from unittest.mock import MagicMock

@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    import db.sqlite_store as store
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "test.db")
    store.init_db()
    return store

@pytest.fixture
def mock_openai():
    client = MagicMock()
    return client
