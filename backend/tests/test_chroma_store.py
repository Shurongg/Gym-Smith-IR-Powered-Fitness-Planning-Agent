import pytest

def test_upsert_and_query(tmp_path, monkeypatch):
    import db.chroma_store as cs
    monkeypatch.setattr(cs, "CHROMA_PATH", str(tmp_path / "chroma"))
    cs._client = None  # reset singleton

    cs.upsert_documents(
        collection_name="test_col",
        ids=["1", "2"],
        documents=["bicep curl for arm strength", "squat for leg power"],
        metadatas=[{"name": "Bicep Curl"}, {"name": "Squat"}],
    )
    results = cs.query_collection("test_col", "arm muscle exercise", n_results=1)
    assert results["ids"][0][0] == "1"

def test_collection_exists_with_data(tmp_path, monkeypatch):
    import db.chroma_store as cs
    monkeypatch.setattr(cs, "CHROMA_PATH", str(tmp_path / "chroma2"))
    cs._client = None

    assert cs.collection_exists_with_data("empty_col") is False
    cs.upsert_documents("empty_col", ["x"], ["hello world"], [{"k": "v"}])
    assert cs.collection_exists_with_data("empty_col") is True
