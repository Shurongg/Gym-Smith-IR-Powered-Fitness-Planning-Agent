# Equipment Picker & Data Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Free Exercise DB second data source (cable/machine exercises), fix equipment filtering bugs, and add a UI equipment picker with Machine sub-panel, search, and memory persistence.

**Architecture:** Free Exercise DB JSON (no API key) is fetched at startup alongside wger and embedded into the same ChromaDB `exercises` collection using a shared equipment normalization map. The frontend Equipment Picker sends `equipment_override` + `specific_machines` to the backend, which uses them to override the Intent Parser's guess and enrich GPT-4o's context. Selections are saved to SQLite `user_memory` and pre-populated on next visit.

**Tech Stack:** Python/FastAPI backend, React/Vite frontend, ChromaDB, SQLite, aiohttp, pytest. All tests run from `backend/` with `python -m pytest tests/ -q`.

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `backend/data/freeexdb_client.py` | Create | Download & parse Free Exercise DB; shared `normalize_equipment` util |
| `backend/tests/test_freeexdb_client.py` | Create | Tests for normalize_equipment and _parse_exercise |
| `backend/init_knowledge_base.py` | Modify | Add Free Exercise DB indexing; normalize wger equipment at index time |
| `backend/pipeline/equipment_filter.py` | Modify | Fix empty/multi-value/bodyweight bugs |
| `backend/tests/test_equipment_filter.py` | Modify | Update tests to canonical equipment values + new empty behavior |
| `backend/pipeline/intent_parser.py` | Modify | Prompt: don't guess equipment, return [] |
| `backend/db/sqlite_store.py` | Modify | Add `specific_machines` column; update upsert/get |
| `backend/tests/test_sqlite_store.py` | Modify | Add specific_machines tests |
| `backend/pipeline/context_assembler.py` | Modify | Accept + render `specific_machines` parameter |
| `backend/tests/test_context_assembler.py` | Modify | Add specific_machines test |
| `backend/main.py` | Modify | Add `equipment_override` + `specific_machines` to PlanRequest; wire pipeline |
| `backend/tests/test_routes.py` | Modify | Add test for equipment_override passthrough |
| `frontend/src/api.js` | Modify | Update generatePlan signature |
| `frontend/src/components/EquipmentPicker.jsx` | Create | Equipment picker UI with Machine sub-panel + search + clear |
| `frontend/src/pages/MainPage.jsx` | Modify | Add picker state, pre-populate from memory, pass to API |

---

## Task 1: Free Exercise DB client + normalize_equipment

**Files:**
- Create: `backend/data/freeexdb_client.py`
- Create: `backend/tests/test_freeexdb_client.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_freeexdb_client.py
from data.freeexdb_client import normalize_equipment, _parse_exercise

def test_normalize_known_values():
    assert normalize_equipment("Dumbbell") == "dumbbell"
    assert normalize_equipment("body only") == "bodyweight"
    assert normalize_equipment("cable") == "cable"
    assert normalize_equipment("machine") == "machine"
    assert normalize_equipment("bands") == "resistance band"
    assert normalize_equipment("SZ-Bar") == "barbell"
    assert normalize_equipment("None") == "bodyweight"
    assert normalize_equipment("none (bodyweight exercise)") == "bodyweight"
    assert normalize_equipment("Gym mat") == "bodyweight"
    assert normalize_equipment("e-z curl bar") == "barbell"

def test_normalize_unknown_returns_none():
    assert normalize_equipment("swiss ball") is None
    assert normalize_equipment("foam roll") is None
    assert normalize_equipment("medicine ball") is None
    assert normalize_equipment("other") is None

def test_normalize_case_insensitive():
    assert normalize_equipment("DUMBBELL") == "dumbbell"
    assert normalize_equipment("Cable") == "cable"
    assert normalize_equipment("MACHINE") == "machine"

def test_parse_exercise_valid():
    raw = {
        "id": "0001",
        "name": "Cable Curl",
        "equipment": "cable",
        "primaryMuscles": ["biceps"],
        "secondaryMuscles": ["forearms"],
        "instructions": ["Step 1", "Step 2", "Step 3", "Step 4"],
        "category": "strength",
    }
    result = _parse_exercise(raw)
    assert result is not None
    assert result["exercise_id"] == "fex_0001"
    assert result["equipment"] == ["cable"]
    assert result["muscles"] == ["biceps"]
    assert result["muscles_secondary"] == ["forearms"]
    assert "Step 4" not in result["description"]  # only first 3 steps

def test_parse_exercise_unknown_equipment_returns_none():
    raw = {
        "id": "0002", "name": "Foam Roll Exercise", "equipment": "foam roll",
        "primaryMuscles": [], "secondaryMuscles": [], "instructions": [], "category": "other",
    }
    assert _parse_exercise(raw) is None
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd backend && python -m pytest tests/test_freeexdb_client.py -v
```
Expected: `ModuleNotFoundError: No module named 'data.freeexdb_client'`

- [ ] **Step 3: Create `backend/data/freeexdb_client.py`**

```python
import aiohttp

FREEEXDB_URL = (
    "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/dist/exercises.json"
)

EQUIPMENT_NORM_MAP = {
    # wger values
    "none": "bodyweight",
    "none (bodyweight exercise)": "bodyweight",
    "gym mat": "bodyweight",
    "dumbbell": "dumbbell",
    "barbell": "barbell",
    "sz-bar": "barbell",
    "bench": "bench",
    "incline bench": "bench",
    "pull-up bar": "pull-up bar",
    "kettlebell": "kettlebell",
    "resistance band": "resistance band",
    # Free Exercise DB values
    "body only": "bodyweight",
    "cable": "cable",
    "machine": "machine",
    "bands": "resistance band",
    "e-z curl bar": "barbell",
}


def normalize_equipment(raw: str) -> str | None:
    """Return canonical equipment name, or None if the value is unmapped (exercise should be skipped)."""
    return EQUIPMENT_NORM_MAP.get(raw.lower().strip())


def _parse_exercise(raw: dict) -> dict | None:
    canonical_eq = normalize_equipment(raw.get("equipment", ""))
    if canonical_eq is None:
        return None
    instructions = raw.get("instructions", [])
    description = " ".join(instructions[:3])
    return {
        "exercise_id": f"fex_{raw['id']}",
        "name": raw["name"],
        "category": raw.get("category", "general"),
        "muscles": raw.get("primaryMuscles", []),
        "muscles_secondary": raw.get("secondaryMuscles", []),
        "equipment": [canonical_eq],
        "description": description,
    }


async def fetch_free_exercise_db() -> list[dict]:
    async with aiohttp.ClientSession() as session:
        async with session.get(FREEEXDB_URL, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            resp.raise_for_status()
            data = await resp.json(content_type=None)
    return [ex for raw in data if (ex := _parse_exercise(raw)) is not None]
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd backend && python -m pytest tests/test_freeexdb_client.py -v
```
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
cd backend && git add data/freeexdb_client.py tests/test_freeexdb_client.py
git commit -m "feat: Free Exercise DB client + normalize_equipment utility"
```

---

## Task 2: Update init_knowledge_base.py — dual source + normalization

**Files:**
- Modify: `backend/init_knowledge_base.py`

Context: The ChromaDB `exercises` collection already exists with OLD unnormalized equipment strings (e.g. `"Dumbbell"`, `"None"`). This task re-indexes with normalized strings and adds Free Exercise DB exercises. **Before running `init_knowledge_base.py` you must delete the old ChromaDB data:**
```bash
rm -rf backend/data/chroma
```

- [ ] **Step 1: Replace `backend/init_knowledge_base.py` entirely**

```python
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
    stem = file_path.stem
    if stem in _NUTRITION_FILES:
        rule_type = "nutrition_rule"
    elif stem in _SAFETY_FILES:
        rule_type = "safety_rule"
    else:
        rule_type = "training_principle"

    text = file_path.read_text(encoding="utf-8")
    parts = re.split(r"^## ", text, flags=re.MULTILINE)

    rules = []
    for i, part in enumerate(parts):
        if i == 0:
            continue
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
```

- [ ] **Step 2: Delete old ChromaDB data and re-index**

```bash
rm -rf /Users/chenshurong/Desktop/glada\ studier/language\ technology/Information\ Retrieval/assignment_2/backend/data/chroma
cd backend && python init_knowledge_base.py
```

Expected output (takes ~2 minutes):
```
[KB] Indexed 40 rules from 7 files.
[KB] Fetched ~847 wger exercises.
[KB] Fetched ~600 Free Exercise DB exercises.
[KB] Indexed ~1400 exercises (847 wger + ~600 freeexdb).
```

- [ ] **Step 3: Verify cable exercises are now in ChromaDB**

```bash
cd backend && python -c "
from db.chroma_store import query_collection
results = query_collection('exercises', 'cable bicep tricep arm', n_results=10)
for meta in results['metadatas'][0]:
    print(meta['name'], '|', meta['equipment'])
" 2>/dev/null
```

Expected: several exercises with `equipment: cable` appear.

- [ ] **Step 4: Commit**

```bash
git add backend/init_knowledge_base.py
git commit -m "feat: dual-source KB init — wger + Free Exercise DB with normalized equipment"
```

---

## Task 3: Fix Equipment Filter

**Files:**
- Modify: `backend/pipeline/equipment_filter.py`
- Modify: `backend/tests/test_equipment_filter.py`

The current filter has three bugs:
1. Empty equipment → returns bodyweight only (should return all)
2. Multi-value equipment strings (e.g. `"barbell, dumbbell"`) compared as a whole string (should any-match)
3. Old `"none"` check doesn't match canonical `"bodyweight"`

- [ ] **Step 1: Rewrite tests (new canonical values + new empty behavior)**

```python
# backend/tests/test_equipment_filter.py
from pipeline.equipment_filter import filter_by_equipment

EXERCISES = [
    {"name": "Bicep Curl", "equipment": "dumbbell"},
    {"name": "Barbell Row", "equipment": "barbell"},
    {"name": "Pull-up", "equipment": "pull-up bar"},
    {"name": "Push-up", "equipment": "bodyweight"},
    {"name": "Cable Fly", "equipment": "cable"},
    {"name": "Combo", "equipment": "barbell, dumbbell"},
]

def test_filter_keeps_matching_equipment():
    result = filter_by_equipment(EXERCISES, ["dumbbell"])
    names = [e["name"] for e in result]
    assert "Bicep Curl" in names
    assert "Barbell Row" not in names
    assert "Cable Fly" not in names

def test_filter_always_includes_bodyweight():
    result = filter_by_equipment(EXERCISES, ["dumbbell"])
    names = [e["name"] for e in result]
    assert "Push-up" in names

def test_filter_case_insensitive():
    result = filter_by_equipment(EXERCISES, ["DUMBBELL"])
    names = [e["name"] for e in result]
    assert "Bicep Curl" in names

def test_filter_multiple_equipment():
    result = filter_by_equipment(EXERCISES, ["dumbbell", "barbell"])
    names = [e["name"] for e in result]
    assert "Bicep Curl" in names
    assert "Barbell Row" in names
    assert "Cable Fly" not in names

def test_filter_empty_returns_all():
    result = filter_by_equipment(EXERCISES, [])
    assert len(result) == len(EXERCISES)

def test_filter_multi_value_exercise_matches_any():
    result = filter_by_equipment(EXERCISES, ["dumbbell"])
    names = [e["name"] for e in result]
    assert "Combo" in names  # has "barbell, dumbbell" — dumbbell matches

def test_filter_multi_value_exercise_excluded_when_no_match():
    result = filter_by_equipment(EXERCISES, ["cable"])
    names = [e["name"] for e in result]
    assert "Combo" not in names  # barbell,dumbbell — neither is cable
```

- [ ] **Step 2: Run tests to confirm failures**

```bash
cd backend && python -m pytest tests/test_equipment_filter.py -v
```
Expected: `test_filter_empty_returns_all` FAIL, `test_filter_multi_value_exercise_matches_any` FAIL, `test_filter_always_includes_bodyweight` FAIL (old data used "None" not "bodyweight").

- [ ] **Step 3: Rewrite `backend/pipeline/equipment_filter.py`**

```python
def filter_by_equipment(exercises: list[dict], user_equipment: list[str]) -> list[dict]:
    """Filter exercises by user's available equipment.

    Returns all exercises when user_equipment is empty (no restriction).
    Bodyweight exercises are always included when any filter is active.
    Exercises with multiple comma-separated equipment values pass if any one matches.
    """
    if not user_equipment:
        return exercises

    allowed = {e.lower() for e in user_equipment} | {"bodyweight"}
    result = []
    for ex in exercises:
        eq_str = ex.get("equipment", "bodyweight")
        ex_equip = {e.strip().lower() for e in eq_str.split(",")}
        if ex_equip & allowed:
            result.append(ex)
    return result
```

- [ ] **Step 4: Run tests to confirm all pass**

```bash
cd backend && python -m pytest tests/test_equipment_filter.py -v
```
Expected: 7 passed

- [ ] **Step 5: Run full suite**

```bash
cd backend && python -m pytest tests/ -q
```
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add backend/pipeline/equipment_filter.py backend/tests/test_equipment_filter.py
git commit -m "fix: equipment filter — empty returns all, any-match multi-value, bodyweight canonical"
```

---

## Task 4: Update Intent Parser — don't guess equipment

**Files:**
- Modify: `backend/pipeline/intent_parser.py`

- [ ] **Step 1: Update the system prompt in `_PARSE_SYSTEM`**

Find this line in `_PARSE_SYSTEM`:
```
- equipment: normalize to: dumbbell, barbell, cable, pull-up bar, resistance band, kettlebell, bench, bodyweight, none
```

Replace the entire `_PARSE_SYSTEM` string with:

```python
_PARSE_SYSTEM = """Extract training intent from the user message. Return ONLY valid JSON:
{
  "target_muscles": ["string"],
  "equipment": ["string"],
  "frequency": integer,
  "intensity": "low"|"medium"|"high",
  "goal": "hypertrophy"|"strength"|"endurance"|"general"|"fat_loss",
  "flags": []
}

Rules:
- target_muscles: use English anatomy names (biceps, triceps, pectoralis, latissimus dorsi, quadriceps, etc.)
- equipment: ONLY extract equipment the user explicitly mentions. If the user does not mention any equipment, return []. Do NOT guess. Normalize to: bodyweight, dumbbell, barbell, cable, machine, bench, pull-up bar, kettlebell, resistance band
- frequency: default 3 if not specified
- intensity: default "medium" if not specified
- flags: add "medical_concern" if user mentions injury, pain, illness, pregnancy, or medical condition"""
```

- [ ] **Step 2: Run existing intent parser tests to confirm nothing broke**

```bash
cd backend && python -m pytest tests/test_intent_parser.py -v
```
Expected: 3 passed (tests mock the LLM so they're unaffected by the prompt change)

- [ ] **Step 3: Commit**

```bash
git add backend/pipeline/intent_parser.py
git commit -m "fix: intent parser — don't guess equipment when not mentioned"
```

---

## Task 5: SQLite store — add specific_machines

**Files:**
- Modify: `backend/db/sqlite_store.py`
- Modify: `backend/tests/test_sqlite_store.py`

- [ ] **Step 1: Write failing tests**

Add these tests to `backend/tests/test_sqlite_store.py`:

```python
def test_upsert_and_get_specific_machines(temp_db):
    token = temp_db.create_user()
    user_id = temp_db.get_user_id(token)
    temp_db.upsert_user_memory(
        user_id, ["machine"], "medium", "strength",
        specific_machines=["Leg Press Machine", "Lat Pulldown Machine"]
    )
    mem = temp_db.get_user_memory(user_id)
    assert mem["specific_machines"] == ["Leg Press Machine", "Lat Pulldown Machine"]

def test_specific_machines_defaults_to_empty_list(temp_db):
    token = temp_db.create_user()
    user_id = temp_db.get_user_id(token)
    temp_db.upsert_user_memory(user_id, ["dumbbell"], "medium", "hypertrophy")
    mem = temp_db.get_user_memory(user_id)
    assert mem["specific_machines"] == []
```

- [ ] **Step 2: Run new tests to confirm they fail**

```bash
cd backend && python -m pytest tests/test_sqlite_store.py::test_upsert_and_get_specific_machines tests/test_sqlite_store.py::test_specific_machines_defaults_to_empty_list -v
```
Expected: FAIL (`upsert_user_memory()` doesn't accept `specific_machines` kwarg)

- [ ] **Step 3: Update `backend/db/sqlite_store.py`**

In `init_db()`, add a migration after `executescript`:

```python
def init_db():
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY,
                session_token TEXT UNIQUE NOT NULL,
                created_at    TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS user_memory (
                id                   INTEGER PRIMARY KEY,
                user_id              INTEGER REFERENCES users(id),
                equipment            TEXT,
                intensity_preference TEXT,
                last_goal            TEXT,
                updated_at           TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS plan_history (
                id          INTEGER PRIMARY KEY,
                user_id     INTEGER REFERENCES users(id),
                user_input  TEXT NOT NULL,
                plan_json   TEXT NOT NULL,
                created_at  TEXT NOT NULL
            );
        """)
        cols = {row[1] for row in conn.execute("PRAGMA table_info(user_memory)")}
        if "specific_machines" not in cols:
            conn.execute("ALTER TABLE user_memory ADD COLUMN specific_machines TEXT")
```

Update `get_user_memory`:

```python
def get_user_memory(user_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM user_memory WHERE user_id = ?", (user_id,)
        ).fetchone()
    if not row:
        return None
    return {
        "equipment": json.loads(row["equipment"]) if row["equipment"] else [],
        "intensity_preference": row["intensity_preference"],
        "last_goal": row["last_goal"],
        "specific_machines": json.loads(row["specific_machines"]) if row["specific_machines"] else [],
    }
```

Update `upsert_user_memory`:

```python
def upsert_user_memory(
    user_id: int,
    equipment: list,
    intensity: str,
    goal: str,
    specific_machines: list | None = None,
):
    now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    machines_json = json.dumps(specific_machines or [])
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM user_memory WHERE user_id = ?", (user_id,)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE user_memory SET equipment=?, intensity_preference=?, last_goal=?, "
                "specific_machines=?, updated_at=? WHERE user_id=?",
                (json.dumps(equipment), intensity, goal, machines_json, now, user_id),
            )
        else:
            conn.execute(
                "INSERT INTO user_memory (user_id, equipment, intensity_preference, last_goal, "
                "specific_machines, updated_at) VALUES (?,?,?,?,?,?)",
                (user_id, json.dumps(equipment), intensity, goal, machines_json, now),
            )
```

- [ ] **Step 4: Run all sqlite tests**

```bash
cd backend && python -m pytest tests/test_sqlite_store.py -v
```
Expected: all pass (including 2 new ones)

- [ ] **Step 5: Run full suite**

```bash
cd backend && python -m pytest tests/ -q
```
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add backend/db/sqlite_store.py backend/tests/test_sqlite_store.py
git commit -m "feat: add specific_machines to user_memory — SQLite migration + upsert/get"
```

---

## Task 6: Context Assembler — render specific_machines

**Files:**
- Modify: `backend/pipeline/context_assembler.py`
- Modify: `backend/tests/test_context_assembler.py`

- [ ] **Step 1: Write failing test**

Add to `backend/tests/test_context_assembler.py`:

```python
def test_assemble_includes_specific_machines():
    prompt = assemble_prompt(
        "I want to build legs",
        SAMPLE_INTENT,
        SAMPLE_EXERCISES,
        SAMPLE_RULES,
        SAMPLE_MEMORY,
        specific_machines=["Leg Press Machine", "Leg Extension Machine"],
    )
    assert "Leg Press Machine" in prompt
    assert "Leg Extension Machine" in prompt

def test_assemble_no_specific_machines_no_section():
    prompt = assemble_prompt(
        "I want arm gains", SAMPLE_INTENT, SAMPLE_EXERCISES, SAMPLE_RULES, SAMPLE_MEMORY,
        specific_machines=[],
    )
    assert "SPECIFIC MACHINES" not in prompt
```

- [ ] **Step 2: Run new tests to confirm they fail**

```bash
cd backend && python -m pytest tests/test_context_assembler.py::test_assemble_includes_specific_machines tests/test_context_assembler.py::test_assemble_no_specific_machines_no_section -v
```
Expected: FAIL (`assemble_prompt()` doesn't accept `specific_machines`)

- [ ] **Step 3: Update `backend/pipeline/context_assembler.py`**

```python
import json

SYSTEM_PROMPT = """You are Gym Smith, a fitness planning assistant. You generate structured weekly training plans based on retrieved exercises and rules.

RESTRICTIONS — never do these:
- No medical advice or diagnosis
- No injury rehabilitation plans
- No precise calorie counting or macro calculations
- No supplement recommendations
- No body fat percentage predictions
- No guarantees of specific results

If the user mentions injury, pain, illness, pregnancy, or a medical condition, respond only with:
"This is outside Gym Smith's scope. Please consult a qualified professional."

OUTPUT FORMAT: Respond ONLY with valid JSON matching this exact schema:
{
  "goal_summary": "string",
  "equipment_needed": ["string"],
  "weekly_schedule": [
    {
      "day": "Day 1",
      "focus": "string",
      "exercises": [
        {
          "name": "string",
          "sets": 3,
          "reps": "10-12",
          "rest": "60s",
          "equipment": "string",
          "muscles": ["string"],
          "alternative": "string or null"
        }
      ]
    }
  ],
  "nutrition_notes": ["string"],
  "safety_reminder": "string"
}"""


def assemble_prompt(
    user_input: str,
    intent: dict,
    exercises: list[dict],
    rules: list[dict],
    memory: dict | None,
    specific_machines: list[str] | None = None,
) -> str:
    parts = [f"USER REQUEST:\n{user_input}\n"]

    parts.append(f"PARSED INTENT:\n{json.dumps(intent, indent=2)}\n")

    parts.append("RETRIEVED EXERCISES:")
    for ex in exercises:
        parts.append(
            f"- {ex['name']} | Category: {ex['category']} | "
            f"Muscles: {ex['muscles']} | Equipment: {ex['equipment']} | "
            f"Description: {ex['description'][:200]}"
        )

    training_rules = [r for r in rules if r.get("type") != "nutrition_rule"]
    nutrition_rules = [r for r in rules if r.get("type") == "nutrition_rule"]

    parts.append("\nTRAINING RULES:")
    for r in training_rules:
        parts.append(f"- {r['title']}: {r['content']}")

    parts.append("\nNUTRITION RULES:")
    for r in nutrition_rules:
        parts.append(f"- {r['title']}: {r['content']}")

    if specific_machines:
        parts.append(
            f"\nUSER'S SPECIFIC MACHINES: {', '.join(specific_machines)}\n"
            "Prioritize exercises using these machines when building the plan."
        )

    if memory:
        parts.append(
            f"\nUSER MEMORY:\n"
            f"- Previous equipment: {memory.get('equipment', [])}\n"
            f"- Previous intensity: {memory.get('intensity_preference', 'unknown')}\n"
            f"- Previous goal: {memory.get('last_goal', 'unknown')}"
        )
    else:
        parts.append("\nUSER MEMORY: No previous session found.")

    return "\n".join(parts)
```

- [ ] **Step 4: Run all context assembler tests**

```bash
cd backend && python -m pytest tests/test_context_assembler.py -v
```
Expected: 7 passed

- [ ] **Step 5: Run full suite**

```bash
cd backend && python -m pytest tests/ -q
```
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add backend/pipeline/context_assembler.py backend/tests/test_context_assembler.py
git commit -m "feat: context assembler — render specific_machines in GPT prompt"
```

---

## Task 7: Backend API wiring — PlanRequest + main.py

**Files:**
- Modify: `backend/main.py`
- Modify: `backend/tests/test_routes.py`

- [ ] **Step 1: Write failing test**

Add to `backend/tests/test_routes.py`:

```python
def test_equipment_override_used_in_plan(client):
    token = client.post("/api/session").json()["session_token"]
    with patch("main.parse_intent") as mock_parse, \
         patch("main.retrieve_exercises") as mock_ex, \
         patch("main.filter_by_equipment") as mock_filter, \
         patch("main.retrieve_rules") as mock_rules, \
         patch("main.retrieve_memory") as mock_mem, \
         patch("main.OpenAI") as mock_cls:
        mock_parse.return_value = {
            "target_muscles": ["biceps"], "equipment": ["cable"],
            "frequency": 3, "intensity": "medium", "goal": "hypertrophy", "flags": [],
        }
        mock_ex.return_value = []
        mock_filter.return_value = []
        mock_rules.return_value = []
        mock_mem.return_value = None
        mock_instance = MagicMock()
        mock_instance.chat.completions.create.return_value.choices[0].message.content = json.dumps({
            "goal_summary": "Arm gains",
            "equipment_needed": ["dumbbell"],
            "weekly_schedule": [],
            "nutrition_notes": [],
            "safety_reminder": "Warm up first.",
        })
        mock_cls.return_value = mock_instance

        response = client.post("/api/plan", json={
            "session_token": token,
            "api_key": "sk-test",
            "user_input": "I want arm gains",
            "equipment_override": ["dumbbell"],
            "specific_machines": [],
        })

    assert response.status_code == 200
    call_args = mock_filter.call_args
    used_equipment = call_args[0][1]
    assert used_equipment == ["dumbbell"]
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
cd backend && python -m pytest tests/test_routes.py::test_equipment_override_used_in_plan -v
```
Expected: FAIL (PlanRequest doesn't have `equipment_override`)

- [ ] **Step 3: Update `backend/main.py`**

Update imports:

```python
from db.sqlite_store import (
    init_db, create_user, get_user_id, get_user_memory,
    get_plan_history, upsert_user_memory, save_plan, delete_plan
)
```

Update `PlanRequest`:

```python
class PlanRequest(BaseModel):
    session_token: str
    api_key: str
    user_input: str
    equipment_override: list[str] = []
    specific_machines: list[str] = []
```

Update `generate_plan` endpoint body (replace the pipeline section):

```python
@app.post("/api/plan")
def generate_plan(body: PlanRequest):
    user_id = get_user_id(body.session_token)
    if user_id is None:
        raise HTTPException(status_code=404, detail="Session not found")

    client = OpenAI(api_key=body.api_key)

    intent = parse_intent(client, body.user_input)

    if "medical_concern" in intent.get("flags", []):
        return {
            "is_medical_concern": True,
            "message": "This is outside Gym Smith's scope. Please consult a qualified professional such as a doctor or certified personal trainer.",
            "ir_process": {"parsed_intent": intent},
        }

    if body.equipment_override:
        intent["equipment"] = body.equipment_override

    exercises_raw = retrieve_exercises(intent["target_muscles"], intent["goal"])
    exercises_filtered = filter_by_equipment(exercises_raw, intent["equipment"])
    rules = retrieve_rules(intent["goal"])
    memory = retrieve_memory(user_id)

    prompt = assemble_prompt(
        body.user_input, intent, exercises_filtered, rules, memory,
        specific_machines=body.specific_machines,
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    plan = json.loads(response.choices[0].message.content)

    upsert_user_memory(
        user_id, intent["equipment"], intent["intensity"], intent["goal"],
        specific_machines=body.specific_machines,
    )
    save_plan(user_id, body.user_input, plan)

    ir_process = {
        "parsed_intent": intent,
        "exercises_retrieved": [e["name"] for e in exercises_raw[:10]],
        "exercises_after_filter": [e["name"] for e in exercises_filtered],
        "training_rules_used": [r["title"] for r in rules if r["type"] != "nutrition_rule"],
        "nutrition_rules_used": [r["title"] for r in rules if r["type"] == "nutrition_rule"],
        "memory_loaded": memory,
    }

    return {"is_medical_concern": False, "plan": plan, "ir_process": ir_process}
```

- [ ] **Step 4: Run all route tests**

```bash
cd backend && python -m pytest tests/test_routes.py -v
```
Expected: all pass

- [ ] **Step 5: Run full suite**

```bash
cd backend && python -m pytest tests/ -q
```
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add backend/main.py backend/tests/test_routes.py
git commit -m "feat: API — equipment_override and specific_machines in PlanRequest"
```

---

## Task 8: Update api.js

**Files:**
- Modify: `frontend/src/api.js`

- [ ] **Step 1: Update `generatePlan` to accept and send equipment fields**

```javascript
// frontend/src/api.js
import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export async function validateKey(apiKey) {
  const { data } = await api.post('/validate-key', { api_key: apiKey })
  return data
}

export async function createSession() {
  const { data } = await api.post('/session')
  return data
}

export async function getSession(token) {
  const { data } = await api.get(`/session/${token}`)
  return data
}

export async function generatePlan(sessionToken, apiKey, userInput, equipmentOverride = [], specificMachines = []) {
  const { data } = await api.post('/plan', {
    session_token: sessionToken,
    api_key: apiKey,
    user_input: userInput,
    equipment_override: equipmentOverride,
    specific_machines: specificMachines,
  })
  return data
}

export async function deletePlan(planId, sessionToken) {
  const { data } = await api.delete(`/plan/${planId}`, { params: { session_token: sessionToken } })
  return data
}
```

- [ ] **Step 2: Verify frontend still builds**

```bash
cd frontend && npm run build 2>&1 | tail -5
```
Expected: build succeeds, no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api.js
git commit -m "feat: api.js — generatePlan accepts equipmentOverride + specificMachines"
```

---

## Task 9: EquipmentPicker component

**Files:**
- Create: `frontend/src/components/EquipmentPicker.jsx`

- [ ] **Step 1: Create `frontend/src/components/EquipmentPicker.jsx`**

```jsx
import { useState } from 'react'
import '../styles/pixel.css'

const TOP_CHIPS = [
  { label: 'Bodyweight', value: 'bodyweight' },
  { label: 'Dumbbell', value: 'dumbbell' },
  { label: 'Barbell', value: 'barbell' },
  { label: 'Cable', value: 'cable' },
  { label: 'Machine', value: 'machine' },
  { label: 'Bench', value: 'bench' },
  { label: 'Pull-up bar', value: 'pull-up bar' },
  { label: 'Kettlebell', value: 'kettlebell' },
  { label: 'Resistance band', value: 'resistance band' },
]

const MACHINE_GROUPS = [
  { group: 'CHEST', machines: ['Chest Press Machine', 'Incline Chest Press Machine', 'Decline Chest Press Machine', 'Pec Deck (Chest Fly)'] },
  { group: 'BACK', machines: ['Lat Pulldown Machine', 'Seated Row Machine', 'Chest-Supported Row Machine', 'Assisted Pull-up Machine', 'Back Extension Machine'] },
  { group: 'SHOULDERS', machines: ['Shoulder Press Machine', 'Lateral Raise Machine', 'Rear Delt Machine', 'Shrug Machine'] },
  { group: 'LEGS — QUADS', machines: ['Leg Press Machine', 'Leg Extension Machine', 'Hack Squat Machine'] },
  { group: 'LEGS — HAMSTRINGS', machines: ['Seated Leg Curl Machine', 'Lying Leg Curl Machine'] },
  { group: 'LEGS — GLUTES', machines: ['Hip Thrust Machine', 'Glute Kickback Machine'] },
  { group: 'LEGS — ADDUCTORS', machines: ['Hip Abductor Machine', 'Hip Adductor Machine'] },
  { group: 'CALVES', machines: ['Seated Calf Raise Machine', 'Standing Calf Raise Machine'] },
  { group: 'ARMS', machines: ['Preacher Curl Machine', 'Triceps Press Machine', 'Triceps Extension Machine', 'Assisted Dip Machine'] },
  { group: 'CORE', machines: ['Ab Crunch Machine', 'Torso Rotation Machine'] },
  { group: 'COMPOUND', machines: ['Smith Machine', 'Multi-Station Machine'] },
]

export default function EquipmentPicker({ selected, specificMachines, onChange }) {
  const [machineOpen, setMachineOpen] = useState(false)
  const [search, setSearch] = useState('')

  const isMachineSelected = selected.includes('machine')
  const hasAny = selected.length > 0 || specificMachines.length > 0

  function toggleChip(value) {
    if (value === 'machine') {
      if (isMachineSelected) {
        onChange(selected.filter(v => v !== 'machine'), [])
        setMachineOpen(false)
        setSearch('')
      } else {
        onChange([...selected, 'machine'], specificMachines)
        setMachineOpen(true)
      }
    } else {
      const next = selected.includes(value)
        ? selected.filter(v => v !== value)
        : [...selected, value]
      onChange(next, specificMachines)
    }
  }

  function toggleMachine(name) {
    const next = specificMachines.includes(name)
      ? specificMachines.filter(m => m !== name)
      : [...specificMachines, name]
    onChange(selected, next)
  }

  function handleClear() {
    onChange([], [])
    setMachineOpen(false)
    setSearch('')
  }

  const filteredGroups = search
    ? MACHINE_GROUPS
        .map(g => ({ ...g, machines: g.machines.filter(m => m.toLowerCase().includes(search.toLowerCase())) }))
        .filter(g => g.machines.length > 0)
    : MACHINE_GROUPS

  return (
    <div style={{ marginBottom: '12px' }}>
      {/* Label + clear row */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <label style={{ fontFamily: 'var(--font-title)', fontSize: '0.5rem', color: 'var(--text-muted)' }}>
          EQUIPMENT (optional)
        </label>
        {hasAny && (
          <button
            onClick={handleClear}
            style={{
              fontFamily: 'var(--font-title)', fontSize: '0.4rem',
              background: 'none', border: '1px dashed var(--text-muted)',
              cursor: 'pointer', padding: '2px 6px', color: 'var(--text-muted)',
            }}
          >
            CLEAR
          </button>
        )}
      </div>

      {/* Top-level chips */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
        {TOP_CHIPS.map(({ label, value }) => {
          const isSelected = selected.includes(value)
          const machineCount = value === 'machine' && specificMachines.length > 0
            ? ` ×${specificMachines.length}` : ''
          const arrow = value === 'machine' ? (machineOpen ? ' ▴' : ' ▾') : ''
          return (
            <button
              key={value}
              onClick={() => toggleChip(value)}
              style={{
                fontFamily: 'var(--font-body)', fontSize: '15px',
                padding: '3px 10px', cursor: 'pointer',
                background: isSelected ? 'var(--primary)' : 'var(--card-bg)',
                border: isSelected ? 'var(--border)' : '1px dashed #aaa',
                boxShadow: isSelected ? '2px 2px 0px #2D2D2D' : 'none',
                color: isSelected ? 'var(--text)' : 'var(--text-muted)',
              }}
            >
              {label}{machineCount}{arrow}
            </button>
          )
        })}
      </div>

      {/* Machine sub-panel */}
      {machineOpen && (
        <div style={{
          marginTop: '8px', border: 'var(--border)', padding: '12px',
          boxShadow: '3px 3px 0px #2D2D2D', background: 'var(--card-bg)',
        }}>
          <input
            type="text"
            placeholder="search machines..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="pixel-input"
            style={{
              width: '100%', marginBottom: '10px', fontSize: '14px',
              padding: '4px 8px', boxSizing: 'border-box',
            }}
          />
          {filteredGroups.length === 0 && (
            <p style={{ fontFamily: 'var(--font-body)', fontSize: '15px', color: 'var(--text-muted)' }}>
              No machines match.
            </p>
          )}
          {filteredGroups.map(({ group, machines }) => (
            <div key={group} style={{ marginBottom: '10px' }}>
              <div style={{
                fontFamily: 'var(--font-title)', fontSize: '0.38rem',
                color: 'var(--text-muted)', marginBottom: '5px',
              }}>
                {group}
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                {machines.map(name => {
                  const isSelected = specificMachines.includes(name)
                  return (
                    <button
                      key={name}
                      onClick={() => toggleMachine(name)}
                      style={{
                        fontFamily: 'var(--font-body)', fontSize: '14px',
                        padding: '2px 8px', cursor: 'pointer',
                        background: isSelected ? 'var(--primary)' : 'var(--bg)',
                        border: isSelected ? 'var(--border)' : '1px dashed #bbb',
                        boxShadow: isSelected ? '1px 1px 0px #2D2D2D' : 'none',
                        color: isSelected ? 'var(--text)' : 'var(--text-muted)',
                      }}
                    >
                      {name}
                    </button>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Verify frontend builds**

```bash
cd frontend && npm run build 2>&1 | tail -5
```
Expected: build succeeds

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/EquipmentPicker.jsx
git commit -m "feat: EquipmentPicker component — chips, Machine sub-panel, search, clear"
```

---

## Task 10: MainPage.jsx — wire picker state + memory pre-population

**Files:**
- Modify: `frontend/src/pages/MainPage.jsx`

- [ ] **Step 1: Read current MainPage.jsx to know exact content before editing**

Run: `cat frontend/src/pages/MainPage.jsx`

- [ ] **Step 2: Add imports and state**

At the top of `MainPage.jsx`, add `EquipmentPicker` import after existing component imports:

```jsx
import EquipmentPicker from '../components/EquipmentPicker'
```

Inside `MainPage` function, add two new state variables after existing state declarations:

```jsx
const [selectedEquipment, setSelectedEquipment] = useState([])
const [specificMachines, setSpecificMachines] = useState([])
```

- [ ] **Step 3: Add useEffect to pre-populate equipment from memory**

Add this `useEffect` after the existing `useEffect` that loads session data:

```jsx
useEffect(() => {
  if (!sessionData?.memory) return
  if (sessionData.memory.equipment?.length > 0) {
    setSelectedEquipment(sessionData.memory.equipment)
  }
  if (sessionData.memory.specific_machines?.length > 0) {
    setSpecificMachines(sessionData.memory.specific_machines)
  }
}, [sessionData])
```

- [ ] **Step 4: Update `handleGenerate` to pass equipment to API**

Find this line in `handleGenerate`:
```jsx
const data = await generatePlan(sessionToken, apiKey, input.trim())
```

Replace with:
```jsx
const data = await generatePlan(sessionToken, apiKey, input.trim(), selectedEquipment, specificMachines)
```

- [ ] **Step 5: Render EquipmentPicker between textarea and button**

Find this block in the JSX:
```jsx
          <textarea
            className="pixel-input"
            rows={4}
            placeholder="e.g. I want to build arm muscle, 3x/week, I have dumbbells and resistance bands, medium intensity"
            value={input}
            onChange={e => setInput(e.target.value)}
            style={{ resize: 'vertical', marginBottom: '12px' }}
          />
          <PixelButton onClick={handleGenerate} disabled={loading || !input.trim()}>
```

Replace with:
```jsx
          <textarea
            className="pixel-input"
            rows={4}
            placeholder="e.g. I want to build arm muscle, 3x/week, medium intensity"
            value={input}
            onChange={e => setInput(e.target.value)}
            style={{ resize: 'vertical', marginBottom: '12px' }}
          />
          <EquipmentPicker
            selected={selectedEquipment}
            specificMachines={specificMachines}
            onChange={(eq, machines) => { setSelectedEquipment(eq); setSpecificMachines(machines) }}
          />
          <PixelButton onClick={handleGenerate} disabled={loading || !input.trim()}>
```

- [ ] **Step 6: Verify frontend builds cleanly**

```bash
cd frontend && npm run build 2>&1 | tail -8
```
Expected: build succeeds, no TypeScript/prop errors

- [ ] **Step 7: Run full backend suite to confirm nothing regressed**

```bash
cd backend && python -m pytest tests/ -q
```
Expected: all pass

- [ ] **Step 8: Commit**

```bash
git add frontend/src/pages/MainPage.jsx
git commit -m "feat: MainPage — EquipmentPicker wired with memory pre-population"
```

---

## Self-Review

**Spec coverage check:**
- ✅ Part 1 (Free Exercise DB + normalization) — Task 1 + Task 2
- ✅ Part 2a (Intent Parser prompt) — Task 4
- ✅ Part 2b (Equipment Filter fixes) — Task 3
- ✅ Part 2c (equipment_override in API) — Task 7
- ✅ Part 2d (specific_machines in context assembler) — Task 6
- ✅ Part 2e (specific_machines in SQLite) — Task 5
- ✅ Part 3 (EquipmentPicker UI — chips, sub-panel, search, clear) — Task 9
- ✅ Part 4 (memory load/save, keep on NEW PLAN) — Task 5 + Task 10
- ✅ CLEAR button — Task 9

**Placeholder scan:** No TBDs, all code blocks complete.

**Type consistency:**
- `normalize_equipment(raw: str) -> str | None` — used consistently in Task 1 and imported in Task 2
- `upsert_user_memory(user_id, equipment, intensity, goal, specific_machines=None)` — matches usage in Task 7
- `assemble_prompt(..., specific_machines: list[str] | None = None)` — matches call in Task 7
- `onChange={(eq, machines) => ...}` — matches `EquipmentPicker` signature `onChange(selected, specificMachines)`
- `generatePlan(sessionToken, apiKey, userInput, equipmentOverride=[], specificMachines=[])` — matches call in Task 10
