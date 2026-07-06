# backend/tests/test_kb_normalization_integration.py
"""
End-to-end proof that the normalize spec closes the missed-recall bug.

Builds an ephemeral (in-memory) ChromaDB "exercises" collection from
fixture rows defined inline. Rows go through the real ingest normalization
(pipeline.normalize.build_exercise_metadata). Retrieval goes through the
real pipeline.exercise_retriever.retrieve_exercises → the real
pipeline.equipment_filter.filter_by_equipment.

If a filtering consumer of the KB metadata was missed during the boolean
migration, this test surfaces it: filtering for "dumbbell" must return
the "dumbbell, bench" fixture.
"""
import chromadb
import pytest
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from pipeline.equipment_filter import filter_by_equipment
from pipeline.exercise_retriever import retrieve_exercises
from pipeline.normalize import build_exercise_metadata


FIXTURES = [
    {
        "id": "F001",
        "name": "Dumbbell Bench Press",
        "category": "Chest",
        "muscles_str": "Chest, Triceps",
        "muscles_secondary_str": "shoulders",
        "equipment_str": "dumbbell, bench",     # THE recall-bug case
        "description": "Lie on a bench and press dumbbells for chest strength.",
    },
    {
        "id": "F002",
        "name": "Barbell Row",
        "category": "Back",
        "muscles_str": "Lats",
        "muscles_secondary_str": "biceps",
        "equipment_str": "barbell",             # control: no dumbbell
        "description": "Barbell row for back thickness.",
    },
    {
        "id": "F003",
        "name": "Push-up",
        "category": "Chest",
        "muscles_str": "chest",
        "muscles_secondary_str": "triceps",
        "equipment_str": "bodyweight",          # control: no dumbbell
        "description": "Chest push-up on the floor.",
    },
    {
        "id": "F004",
        "name": "Cable Fly",
        "category": "Chest",
        "muscles_str": "chest",
        "muscles_secondary_str": "shoulders",
        "equipment_str": "cable",               # control: no dumbbell
        "description": "Cable chest fly for pec isolation.",
    },
    {
        "id": "F005",
        "name": "Dumbbell Curl",
        "category": "Arms",
        "muscles_str": "Biceps",
        "muscles_secondary_str": "forearms",
        "equipment_str": "dumbbell",            # single-atom dumbbell control
        "description": "Standing dumbbell curl for biceps.",
    },
]


@pytest.fixture
def ephemeral_exercises(monkeypatch):
    """Swap the global chroma client for an in-memory one, seeded with FIXTURES."""
    ephemeral = chromadb.EphemeralClient()
    ef = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

    # Force db.chroma_store.get_client() to return our ephemeral client.
    import db.chroma_store as store
    monkeypatch.setattr(store, "_client", ephemeral)

    col = ephemeral.get_or_create_collection(
        name="exercises",
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )
    ids, docs, metas = [], [], []
    for fx in FIXTURES:
        meta = build_exercise_metadata(
            name=fx["name"],
            category=fx["category"],
            muscles_str=fx["muscles_str"],
            muscles_secondary_str=fx["muscles_secondary_str"],
            equipment_str=fx["equipment_str"],
            description=fx["description"],
        )
        ids.append(fx["id"])
        docs.append(
            f"{fx['name']} - {fx['category']} - muscles: {fx['muscles_str']} - {fx['description']}"
        )
        metas.append(meta)
    col.upsert(ids=ids, documents=docs, metadatas=metas)
    yield col


def test_dumbbell_filter_surfaces_multi_equipment_row(ephemeral_exercises):
    """End-to-end: user filters for 'dumbbell'; the 'dumbbell, bench' fixture
    (F001) MUST be in the result. This is the whole spec in one assertion."""
    retrieved = retrieve_exercises(
        target_muscles=["chest"],
        goal="strength",
        equipment_hint=["dumbbell"],
        n_results_per_query=15,     # collection has 5 rows; retrieval returns all
    )
    retrieved_names = {e["name"] for e in retrieved}
    # Sanity — retrieval brought the fixtures into scope
    assert "Dumbbell Bench Press" in retrieved_names, (
        f"retrieval did not surface the fixture at all (got {retrieved_names!r}); "
        "if this fails, the ephemeral client monkeypatch didn't take effect"
    )

    filtered = filter_by_equipment(retrieved, ["dumbbell"])
    names = {e["name"] for e in filtered}

    # THE recall-bug assertion:
    assert "Dumbbell Bench Press" in names, (
        "Multi-equipment 'dumbbell, bench' fixture was dropped by the filter — "
        "the boolean migration is incomplete or a filtering consumer was missed"
    )
    # Positive control:
    assert "Dumbbell Curl" in names
    # Negative controls: none of these carry dumbbell
    assert "Barbell Row" not in names
    assert "Push-up" not in names
    assert "Cable Fly" not in names
