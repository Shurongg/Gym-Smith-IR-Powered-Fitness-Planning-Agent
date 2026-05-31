import asyncio
import re
from pathlib import Path
from data.wger_client import fetch_all_exercises
from data.freeexdb_client import fetch_free_exercise_db, normalize_equipment
from db.chroma_store import collection_exists_with_data, upsert_documents

RULES_DIR = Path(__file__).parent / "data" / "rules"

_NUTRITION_FILES = {"nutrition_basics"}
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


def _init_rules():
    if collection_exists_with_data("rules"):
        print("[KB] Rules already indexed.")
        return

    if not RULES_DIR.exists():
        print("[KB] data/rules/ directory not found — skipping rules indexing.")
        return

    md_files = sorted(RULES_DIR.glob("*.md"))
    if not md_files:
        print("[KB] No markdown files found in data/rules/ — skipping.")
        return

    all_rules: list[dict] = []
    for md_file in md_files:
        try:
            all_rules.extend(_parse_markdown_rules(md_file))
        except OSError as e:
            print(f"[KB] Failed to read {md_file.name}: {e}")

    if not all_rules:
        return

    upsert_documents(
        "rules",
        [r["id"] for r in all_rules],
        [f"{r['title']}: {r['content']}" for r in all_rules],
        [{"type": r["type"], "title": r["title"], "content": r["content"]} for r in all_rules],
    )
    print(f"[KB] Indexed {len(all_rules)} rules from {len(md_files)} files.")


def _normalize_wger_equipment(equipment_list: list[str]) -> str | None:
    """Normalize wger equipment list to comma-separated canonical string. Returns None if all unmapped."""
    canonical = []
    for eq in equipment_list:
        norm = normalize_equipment(eq)
        if norm and norm not in canonical:
            canonical.append(norm)
    return ", ".join(canonical) if canonical else None


async def _init_exercises():
    if collection_exists_with_data("exercises"):
        print("[KB] Exercises already indexed.")
        return

    print("[KB] Fetching exercises from wger API...")
    wger_exercises = await fetch_all_exercises()
    print(f"[KB] Fetched {len(wger_exercises)} wger exercises.")

    print("[KB] Fetching Free Exercise DB...")
    fex_exercises = await fetch_free_exercise_db()
    print(f"[KB] Fetched {len(fex_exercises)} Free Exercise DB exercises.")

    ids, documents, metadatas = [], [], []
    seen_ids: set[str] = set()

    for ex in wger_exercises:
        eq = _normalize_wger_equipment(ex["equipment"])
        if eq is None:
            continue
        # wger leaves cable/machine exercises untagged → they normalize to "bodyweight".
        # Override using name/description keywords so the equipment filter works correctly.
        if eq == "bodyweight":
            name_lower = ex["name"].lower()
            desc_lower = ex["description"].lower()
            if "cable" in name_lower or "cable" in desc_lower:
                eq = "cable"
            elif "machine" in name_lower:
                eq = "machine"
        ex_id = ex["exercise_id"]
        if ex_id in seen_ids:
            continue
        seen_ids.add(ex_id)
        muscles_str = ", ".join(ex["muscles"]) or "general"
        doc = f"{ex['name']} - {ex['category']} - muscles: {muscles_str} - {ex['description']}"
        ids.append(ex_id)
        documents.append(doc[:1500])
        metadatas.append({
            "name": ex["name"],
            "category": ex["category"],
            "muscles": muscles_str,
            "muscles_secondary": ", ".join(ex["muscles_secondary"]),
            "equipment": eq,
            "description": ex["description"][:400],
        })

    for ex in fex_exercises:
        eq = ", ".join(ex["equipment"])
        ex_id = ex["exercise_id"]
        if ex_id in seen_ids:
            continue
        seen_ids.add(ex_id)
        muscles_str = ", ".join(ex["muscles"]) or "general"
        doc = f"{ex['name']} - {ex['category']} - muscles: {muscles_str} - {ex['description']}"
        ids.append(ex_id)
        documents.append(doc[:1500])
        metadatas.append({
            "name": ex["name"],
            "category": ex["category"],
            "muscles": muscles_str,
            "muscles_secondary": ", ".join(ex["muscles_secondary"]),
            "equipment": eq,
            "description": ex["description"][:400],
        })

    upsert_documents("exercises", ids, documents, metadatas)
    print(f"[KB] Indexed {len(ids)} exercises ({len(wger_exercises)} wger + {len(fex_exercises)} freeexdb).")


async def init_knowledge_base():
    """Idempotent KB init. Awaitable for use in FastAPI lifespan."""
    _init_rules()
    await _init_exercises()


if __name__ == "__main__":
    asyncio.run(init_knowledge_base())
