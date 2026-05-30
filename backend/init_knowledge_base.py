import asyncio
import json
from pathlib import Path
from data.wger_client import fetch_all_exercises
from db.chroma_store import collection_exists_with_data, upsert_documents

RULES_PATH = Path(__file__).parent / "data" / "rules.json"


async def _init_exercises():
    if collection_exists_with_data("exercises"):
        print("[KB] Exercises already indexed.")
        return
    print("[KB] Fetching exercises from wger API...")
    exercises = await fetch_all_exercises()
    print(f"[KB] Fetched {len(exercises)} exercises. Indexing...")

    ids, documents, metadatas = [], [], []
    for ex in exercises:
        muscles_str = ", ".join(ex["muscles"]) or "general"
        doc = f"{ex['name']} - {ex['category']} - muscles: {muscles_str} - {ex['description']}"
        ids.append(ex["exercise_id"])
        documents.append(doc[:1500])
        metadatas.append({
            "name": ex["name"],
            "category": ex["category"],
            "muscles": ", ".join(ex["muscles"]),
            "muscles_secondary": ", ".join(ex["muscles_secondary"]),
            "equipment": ", ".join(ex["equipment"]),
            "description": ex["description"][:400],
        })

    upsert_documents("exercises", ids, documents, metadatas)
    print(f"[KB] Indexed {len(ids)} exercises.")


def _init_rules():
    if collection_exists_with_data("rules"):
        print("[KB] Rules already indexed.")
        return

    if not RULES_PATH.exists():
        print("[KB] rules.json not found — skipping rules indexing.")
        return

    try:
        rules_data = json.loads(RULES_PATH.read_text())
    except (json.JSONDecodeError, OSError) as e:
        print(f"[KB] Failed to load rules.json: {e}")
        return

    all_rules = (
        rules_data.get("training_principles", [])
        + rules_data.get("recovery_rules", [])
        + rules_data.get("nutrition_rules", [])
    )

    ids, documents, metadatas = [], [], []
    for rule in all_rules:
        ids.append(rule["id"])
        documents.append(f"{rule['title']}: {rule['content']}")
        metadatas.append({
            "type": rule["type"],
            "title": rule["title"],
            "content": rule["content"],
            "tags": ", ".join(rule["tags"]),
        })

    upsert_documents("rules", ids, documents, metadatas)
    print(f"[KB] Indexed {len(ids)} rules.")


async def init_knowledge_base():
    """Idempotent KB init. Awaitable for use in FastAPI lifespan."""
    _init_rules()
    await _init_exercises()


if __name__ == "__main__":
    asyncio.run(init_knowledge_base())
