import asyncio
import re
from pathlib import Path
from data.wger_client import fetch_all_exercises
from db.chroma_store import collection_exists_with_data, upsert_documents

RULES_DIR = Path(__file__).parent / "data" / "rules"

# Files whose sections are tagged as nutrition_rule; all others → training_principle
_NUTRITION_FILES = {"nutrition_basics"}
# Files whose sections are tagged as safety_rule
_SAFETY_FILES = {"safety_boundaries"}


def _parse_markdown_rules(file_path: Path) -> list[dict]:
    """Split one markdown file into per-section rule dicts."""
    stem = file_path.stem
    if stem in _NUTRITION_FILES:
        rule_type = "nutrition_rule"
    elif stem in _SAFETY_FILES:
        rule_type = "safety_rule"
    else:
        rule_type = "training_principle"

    text = file_path.read_text(encoding="utf-8")
    # Split on lines that start with "## " to get individual sections
    parts = re.split(r"^## ", text, flags=re.MULTILINE)

    rules = []
    for i, part in enumerate(parts):
        if i == 0:
            continue  # file title block before first ##
        lines = part.strip().split("\n", 1)
        title = lines[0].strip()
        content = lines[1].strip() if len(lines) > 1 else ""
        if not content:
            continue
        rules.append({
            "id": f"{stem}_{i}",
            "type": rule_type,
            "title": title,
            "content": content[:1200],
        })
    return rules


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

    if not RULES_DIR.exists():
        print("[KB] data/rules/ directory not found — skipping rules indexing.")
        return

    md_files = sorted(RULES_DIR.glob("*.md"))
    if not md_files:
        print("[KB] No markdown files found in data/rules/ — skipping rules indexing.")
        return

    all_rules: list[dict] = []
    for md_file in md_files:
        try:
            all_rules.extend(_parse_markdown_rules(md_file))
        except OSError as e:
            print(f"[KB] Failed to read {md_file.name}: {e}")

    if not all_rules:
        print("[KB] No rules parsed — skipping rules indexing.")
        return

    ids = [r["id"] for r in all_rules]
    documents = [f"{r['title']}: {r['content']}" for r in all_rules]
    metadatas = [{"type": r["type"], "title": r["title"], "content": r["content"]} for r in all_rules]

    upsert_documents("rules", ids, documents, metadatas)
    print(f"[KB] Indexed {len(all_rules)} rules from {len(md_files)} files.")


async def init_knowledge_base():
    """Idempotent KB init. Awaitable for use in FastAPI lifespan."""
    _init_rules()
    await _init_exercises()


if __name__ == "__main__":
    asyncio.run(init_knowledge_base())
