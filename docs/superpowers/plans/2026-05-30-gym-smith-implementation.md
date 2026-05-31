# Gym Smith — IR Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a retrieval-augmented fitness planning agent with React frontend, FastAPI backend, ChromaDB vector search, SQLite memory, and wger API exercise knowledge base.

**Architecture:** 6-step IR pipeline (Intent Parser → Exercise Retriever → Equipment Filter → Rule Retriever → Memory Retriever → Context Assembler) feeding into GPT-4o for plan generation. React frontend with pixel art UI communicates with FastAPI via REST. ChromaDB stores exercise and rule embeddings using a local sentence-transformer model (no API key needed for KB init); SQLite stores user memory and plan history. OpenAI API key is used exclusively for LLM calls.

**Tech Stack:** Python 3.11+, FastAPI 0.111, ChromaDB 0.5, sentence-transformers (via chromadb), SQLite (stdlib), aiohttp, OpenAI SDK, pytest, React 18, Vite, React Router v6, axios

**Note on embeddings:** We use ChromaDB's built-in `SentenceTransformerEmbeddingFunction` (`all-MiniLM-L6-v2`) instead of OpenAI embeddings so the knowledge base can be initialized at server startup without requiring the user's API key. The OpenAI key is used only for GPT-4o LLM calls.

---

## File Map

```
gym-smith/
├── backend/
│   ├── main.py                          # FastAPI app, routes, CORS, lifespan
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── intent_parser.py             # Step 1: GPT-4o parses user input → structured dict
│   │   ├── exercise_retriever.py        # Step 2: ChromaDB semantic search for exercises
│   │   ├── equipment_filter.py          # Step 3: filter exercises by user equipment
│   │   ├── rule_retriever.py            # Step 4: ChromaDB semantic search for rules
│   │   ├── memory_retriever.py          # Step 5: SQLite user memory lookup
│   │   └── context_assembler.py         # Step 6: assemble all context into prompt
│   ├── data/
│   │   ├── rules.json                   # hand-authored training + nutrition rules
│   │   └── wger_client.py               # async wger API fetcher with pagination
│   ├── db/
│   │   ├── __init__.py
│   │   ├── chroma_store.py              # ChromaDB client wrapper
│   │   └── sqlite_store.py              # SQLite CRUD operations
│   ├── init_knowledge_base.py           # fetches wger + embeds rules → ChromaDB
│   ├── conftest.py                      # (empty, keeps backend as package root for pytest)
│   ├── requirements.txt
│   └── tests/
│       ├── conftest.py                  # pytest fixtures
│       ├── test_sqlite_store.py
│       ├── test_chroma_store.py
│       ├── test_equipment_filter.py
│       ├── test_context_assembler.py
│       ├── test_intent_parser.py
│       ├── test_exercise_retriever.py
│       ├── test_rule_retriever.py
│       ├── test_memory_retriever.py
│       └── test_routes.py
├── frontend/
│   ├── index.html
│   ├── vite.config.js
│   ├── package.json
│   └── src/
│       ├── main.jsx
│       ├── App.jsx                      # router: ApiKeyPage → MainPage
│       ├── api.js                       # axios wrapper for all backend calls
│       ├── pages/
│       │   ├── ApiKeyPage.jsx           # API key input + connection test
│       │   └── MainPage.jsx             # two-column layout, input, plan output
│       ├── components/
│       │   ├── PixelButton.jsx          # reusable pixel-art button
│       │   ├── SidebarMemory.jsx        # left sidebar: user memory + history
│       │   ├── PlanCard.jsx             # one training day card
│       │   └── IrProcessPanel.jsx       # collapsible IR trace panel
│       └── styles/
│           └── pixel.css               # CSS variables, fonts, pixel art base styles
├── .env.example
└── README.md
```

---

## Task 1: Backend Scaffold

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/pytest.ini`
- Create: `backend/pipeline/__init__.py`
- Create: `backend/db/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/conftest.py`

- [ ] **Step 1: Create `backend/requirements.txt`**

```
fastapi==0.111.0
uvicorn[standard]==0.30.1
openai==1.35.0
chromadb==0.5.3
aiohttp==3.9.5
pydantic==2.7.4
pytest==8.2.2
pytest-asyncio==0.23.7
pytest-mock==3.14.0
httpx==0.27.0
```

- [ ] **Step 2: Create `backend/pytest.ini`**

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

- [ ] **Step 3: Create empty `__init__.py` files**

Create `backend/pipeline/__init__.py`, `backend/db/__init__.py`, `backend/data/__init__.py` — all empty.

Create `backend/conftest.py` — empty (makes backend a pytest root).

- [ ] **Step 4: Create `backend/tests/conftest.py`**

```python
import pytest
from pathlib import Path
from unittest.mock import MagicMock

@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    import backend.db.sqlite_store as store
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "test.db")
    store.init_db()
    return store

@pytest.fixture
def mock_openai():
    client = MagicMock()
    return client
```

- [ ] **Step 5: Install dependencies**

```bash
cd backend && pip install -r requirements.txt
```

- [ ] **Step 6: Commit**

```bash
git init
git add backend/
git commit -m "feat: backend scaffold with requirements and test config"
```

---

## Task 2: rules.json

**Files:**
- Create: `backend/data/rules.json`

- [ ] **Step 1: Create `backend/data/rules.json`**

```json
{
  "training_principles": [
    {
      "id": "tp1",
      "type": "training_principle",
      "title": "Progressive Overload",
      "content": "Gradually increase weight, reps, or sets over time. Each week aim to lift slightly more or do one extra rep to continue forcing muscle adaptation.",
      "tags": ["hypertrophy", "strength", "general"]
    },
    {
      "id": "tp2",
      "type": "training_principle",
      "title": "Compound Movements First",
      "content": "Always perform compound exercises (squat, deadlift, bench press, rows) before isolation exercises. Compound lifts require more energy and coordination and should be done when you are fresh.",
      "tags": ["general", "strength", "hypertrophy"]
    },
    {
      "id": "tp3",
      "type": "training_principle",
      "title": "Sets and Reps for Hypertrophy",
      "content": "For muscle growth, perform 3-4 sets of 8-12 reps per exercise at 65-80% of your one-rep max. The last 2-3 reps of each set should feel challenging.",
      "tags": ["hypertrophy", "muscle_growth"]
    },
    {
      "id": "tp4",
      "type": "training_principle",
      "title": "Sets and Reps for Strength",
      "content": "For strength development, perform 3-5 sets of 3-6 reps at 80-90% of your one-rep max with longer rest periods of 2-3 minutes between sets.",
      "tags": ["strength", "powerlifting"]
    },
    {
      "id": "tp5",
      "type": "training_principle",
      "title": "Sets and Reps for Muscle Endurance",
      "content": "For muscular endurance and definition, perform 2-3 sets of 15-20 reps with lighter weight and shorter rest periods of 30-60 seconds.",
      "tags": ["endurance", "toning", "definition"]
    },
    {
      "id": "tp6",
      "type": "training_principle",
      "title": "Rest Between Sets",
      "content": "For hypertrophy, rest 60-90 seconds between sets. For strength, rest 2-3 minutes. For endurance, rest 30-60 seconds. Longer rest allows fuller recovery for heavier loads.",
      "tags": ["hypertrophy", "strength", "endurance", "general"]
    },
    {
      "id": "tp7",
      "type": "training_principle",
      "title": "Muscle Group Split",
      "content": "Avoid training the same muscle group on consecutive days. Allow at least 48 hours of rest between sessions targeting the same muscles to allow recovery and growth.",
      "tags": ["recovery", "programming", "general"]
    },
    {
      "id": "tp8",
      "type": "training_principle",
      "title": "Warm-Up Before Training",
      "content": "Always warm up for 5-10 minutes before training. Do light cardio to raise heart rate, then dynamic stretches or lighter sets of your first exercise before loading up.",
      "tags": ["safety", "general", "injury_prevention"]
    },
    {
      "id": "tp9",
      "type": "training_principle",
      "title": "Full Range of Motion",
      "content": "Use the full range of motion for each exercise. Partial reps reduce muscle activation and long-term flexibility. If you cannot complete a full ROM, reduce the weight.",
      "tags": ["technique", "general", "hypertrophy"]
    },
    {
      "id": "tp10",
      "type": "training_principle",
      "title": "3-Day Full Body vs Push-Pull-Legs",
      "content": "For 3 sessions per week, full body training (each session hits all major muscles) is effective for beginners and intermediates. For 4-6 sessions, a push-pull-legs split allows higher volume per muscle group.",
      "tags": ["programming", "split", "frequency"]
    }
  ],
  "recovery_rules": [
    {
      "id": "rr1",
      "type": "recovery_rule",
      "title": "48-Hour Muscle Recovery Rule",
      "content": "A trained muscle group needs 48-72 hours to fully recover. Training the same muscle before it recovers leads to overtraining and impairs progress.",
      "tags": ["recovery", "programming", "general"]
    },
    {
      "id": "rr2",
      "type": "recovery_rule",
      "title": "Sleep for Muscle Growth",
      "content": "Aim for 7-9 hours of quality sleep per night. Most muscle repair and growth hormone release happens during deep sleep. Poor sleep significantly reduces training gains.",
      "tags": ["recovery", "sleep", "general"]
    },
    {
      "id": "rr3",
      "type": "recovery_rule",
      "title": "Deload Weeks",
      "content": "Every 4-6 weeks, take a deload week by reducing training volume and intensity by 40-50%. This allows accumulated fatigue to dissipate and often leads to better performance afterward.",
      "tags": ["recovery", "programming", "advanced"]
    },
    {
      "id": "rr4",
      "type": "recovery_rule",
      "title": "Active Recovery on Rest Days",
      "content": "On rest days, light activity like walking, yoga, or gentle stretching (20-30 minutes) promotes blood flow to muscles, reduces soreness, and aids recovery better than complete inactivity.",
      "tags": ["recovery", "rest_day"]
    },
    {
      "id": "rr5",
      "type": "recovery_rule",
      "title": "Hydration for Recovery",
      "content": "Drink at least 2-3 liters of water per day. On training days, drink 500ml before, 250ml every 15-20 minutes during, and 500ml after your session. Dehydration impairs strength and recovery.",
      "tags": ["hydration", "recovery", "general"]
    },
    {
      "id": "rr6",
      "type": "recovery_rule",
      "title": "Signs of Overtraining",
      "content": "Watch for: persistent fatigue lasting more than 2 days, declining performance over 2+ weeks, increased resting heart rate, mood changes, or loss of motivation. These signal the need for extra rest.",
      "tags": ["overtraining", "recovery", "safety"]
    },
    {
      "id": "rr7",
      "type": "recovery_rule",
      "title": "Post-Workout Window",
      "content": "Consume protein within 30-60 minutes after training to support muscle repair. A simple meal or snack with 20-40g of protein is sufficient. The post-workout window is real but not as critical as total daily protein.",
      "tags": ["nutrition", "recovery", "post_workout"]
    },
    {
      "id": "rr8",
      "type": "recovery_rule",
      "title": "Mobility and Stretching",
      "content": "Perform static stretches after training (not before) for tight muscle groups, holding 20-30 seconds per stretch. Regular mobility work reduces injury risk and maintains joint health over time.",
      "tags": ["mobility", "flexibility", "injury_prevention"]
    }
  ],
  "nutrition_rules": [
    {
      "id": "nr1",
      "type": "nutrition_rule",
      "title": "Protein Intake for Muscle Building",
      "content": "Consume 1.6-2.2g of protein per kg of bodyweight daily for muscle growth. For a 70kg person, that is 112-154g of protein per day, spread across meals.",
      "tags": ["protein", "hypertrophy", "muscle_building"]
    },
    {
      "id": "nr2",
      "type": "nutrition_rule",
      "title": "Good Protein Sources",
      "content": "High-quality protein sources: chicken breast, turkey, fish (salmon, tuna), eggs, Greek yogurt, cottage cheese, tofu, tempeh, lentils, and legumes. Mix animal and plant sources for variety.",
      "tags": ["protein", "food_sources", "general"]
    },
    {
      "id": "nr3",
      "type": "nutrition_rule",
      "title": "Carbohydrates for Training Energy",
      "content": "Eat complex carbohydrates 1-2 hours before training for sustained energy: oats, brown rice, sweet potato, whole grain bread, or banana. Avoid heavy meals immediately before training.",
      "tags": ["carbohydrates", "pre_workout", "energy"]
    },
    {
      "id": "nr4",
      "type": "nutrition_rule",
      "title": "Caloric Surplus for Muscle Gain",
      "content": "To build muscle, consume a slight caloric surplus of 200-300 kcal above your maintenance level. A large surplus leads to excess fat gain. Combine with progressive overload training.",
      "tags": ["calories", "muscle_building", "hypertrophy"]
    },
    {
      "id": "nr5",
      "type": "nutrition_rule",
      "title": "Caloric Deficit for Fat Loss While Preserving Muscle",
      "content": "For fat loss while preserving muscle, maintain a moderate deficit of 300-500 kcal below maintenance. Keep protein high (2.2g/kg) and continue training. Avoid aggressive deficits which cause muscle loss.",
      "tags": ["calories", "fat_loss", "cutting", "definition"]
    },
    {
      "id": "nr6",
      "type": "nutrition_rule",
      "title": "Consistent Meal Timing",
      "content": "Eat every 3-5 hours to maintain stable energy and support muscle protein synthesis. Aim for 3-5 meals or snacks per day rather than one or two large meals.",
      "tags": ["meal_timing", "general"]
    },
    {
      "id": "nr7",
      "type": "nutrition_rule",
      "title": "Vegetables and Micronutrients",
      "content": "Include vegetables in at least 2 meals per day. Micronutrients (vitamins and minerals from vegetables and fruits) support recovery, immune function, and overall performance. Aim for variety and color.",
      "tags": ["micronutrients", "vegetables", "general", "health"]
    },
    {
      "id": "nr8",
      "type": "nutrition_rule",
      "title": "Limit Processed Foods",
      "content": "Minimize ultra-processed foods, fast food, and sugary drinks especially on training days. These provide empty calories, spike blood sugar, and impair recovery. Whole foods support better training performance.",
      "tags": ["food_quality", "general", "health"]
    },
    {
      "id": "nr9",
      "type": "nutrition_rule",
      "title": "Post-Workout Nutrition",
      "content": "Within 1 hour after training, eat a meal containing both protein (20-40g) and carbohydrates. Examples: chicken and rice, eggs and toast, Greek yogurt and fruit, or a protein shake with banana.",
      "tags": ["post_workout", "recovery", "nutrition"]
    },
    {
      "id": "nr10",
      "type": "nutrition_rule",
      "title": "Nutrition Disclaimer",
      "content": "These are general evidence-based guidelines for healthy adults. Individual needs vary based on age, body composition, health conditions, and goals. Consult a registered dietitian for a personalized nutrition plan.",
      "tags": ["disclaimer", "general"]
    }
  ]
}
```

- [ ] **Step 2: Verify the file is valid JSON**

```bash
cd backend && python -c "import json; json.load(open('data/rules.json')); print('OK')"
```
Expected output: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/data/rules.json
git commit -m "feat: add training, recovery, and nutrition rules knowledge base"
```

---

## Task 3: SQLite Store

**Files:**
- Create: `backend/db/sqlite_store.py`
- Create: `backend/tests/test_sqlite_store.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_sqlite_store.py`:

```python
import pytest
import json

def test_init_creates_tables(temp_db):
    store = temp_db
    with store.get_connection() as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    names = {r[0] for r in tables}
    assert "users" in names
    assert "user_memory" in names
    assert "plan_history" in names

def test_create_user_returns_token(temp_db):
    token = temp_db.create_user()
    assert isinstance(token, str)
    assert len(token) == 36  # UUID format

def test_get_user_id_returns_id(temp_db):
    token = temp_db.create_user()
    user_id = temp_db.get_user_id(token)
    assert isinstance(user_id, int)

def test_get_user_id_unknown_token(temp_db):
    assert temp_db.get_user_id("nonexistent") is None

def test_upsert_and_get_user_memory(temp_db):
    token = temp_db.create_user()
    user_id = temp_db.get_user_id(token)
    temp_db.upsert_user_memory(user_id, ["dumbbell", "barbell"], "medium", "hypertrophy")
    mem = temp_db.get_user_memory(user_id)
    assert mem["equipment"] == ["dumbbell", "barbell"]
    assert mem["intensity_preference"] == "medium"
    assert mem["last_goal"] == "hypertrophy"

def test_upsert_user_memory_updates_existing(temp_db):
    token = temp_db.create_user()
    user_id = temp_db.get_user_id(token)
    temp_db.upsert_user_memory(user_id, ["dumbbell"], "low", "endurance")
    temp_db.upsert_user_memory(user_id, ["barbell"], "high", "strength")
    mem = temp_db.get_user_memory(user_id)
    assert mem["equipment"] == ["barbell"]
    assert mem["intensity_preference"] == "high"

def test_get_user_memory_no_memory(temp_db):
    token = temp_db.create_user()
    user_id = temp_db.get_user_id(token)
    assert temp_db.get_user_memory(user_id) is None

def test_save_and_get_plan_history(temp_db):
    token = temp_db.create_user()
    user_id = temp_db.get_user_id(token)
    plan = {"weekly_schedule": [{"day": "Day 1", "exercises": []}]}
    temp_db.save_plan(user_id, "I want to build arms", plan)
    history = temp_db.get_plan_history(user_id)
    assert len(history) == 1
    assert history[0]["user_input"] == "I want to build arms"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && pytest tests/test_sqlite_store.py -v
```
Expected: `ModuleNotFoundError` or `ImportError` for `backend.db.sqlite_store`

- [ ] **Step 3: Implement `backend/db/sqlite_store.py`**

```python
import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "gym_smith.db"


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


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


def create_user() -> str:
    token = str(uuid.uuid4())
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO users (session_token, created_at) VALUES (?, ?)",
            (token, datetime.utcnow().isoformat()),
        )
    return token


def get_user_id(session_token: str) -> int | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM users WHERE session_token = ?", (session_token,)
        ).fetchone()
    return row["id"] if row else None


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
    }


def upsert_user_memory(user_id: int, equipment: list, intensity: str, goal: str):
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM user_memory WHERE user_id = ?", (user_id,)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE user_memory SET equipment=?, intensity_preference=?, last_goal=?, updated_at=? WHERE user_id=?",
                (json.dumps(equipment), intensity, goal, now, user_id),
            )
        else:
            conn.execute(
                "INSERT INTO user_memory (user_id, equipment, intensity_preference, last_goal, updated_at) VALUES (?,?,?,?,?)",
                (user_id, json.dumps(equipment), intensity, goal, now),
            )


def save_plan(user_id: int, user_input: str, plan: dict):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO plan_history (user_id, user_input, plan_json, created_at) VALUES (?,?,?,?)",
            (user_id, user_input, json.dumps(plan), datetime.utcnow().isoformat()),
        )


def get_plan_history(user_id: int, limit: int = 5) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT user_input, created_at FROM plan_history WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [{"user_input": r["user_input"], "created_at": r["created_at"]} for r in rows]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && pytest tests/test_sqlite_store.py -v
```
Expected: all 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/db/sqlite_store.py backend/tests/test_sqlite_store.py
git commit -m "feat: SQLite store for user sessions, memory, and plan history"
```

---

## Task 4: ChromaDB Store

**Files:**
- Create: `backend/db/chroma_store.py`
- Create: `backend/tests/test_chroma_store.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_chroma_store.py`:

```python
import pytest

def test_upsert_and_query(tmp_path, monkeypatch):
    import backend.db.chroma_store as cs
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
    import backend.db.chroma_store as cs
    monkeypatch.setattr(cs, "CHROMA_PATH", str(tmp_path / "chroma2"))
    cs._client = None

    assert cs.collection_exists_with_data("empty_col") is False
    cs.upsert_documents("empty_col", ["x"], ["hello world"], [{"k": "v"}])
    assert cs.collection_exists_with_data("empty_col") is True
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && pytest tests/test_chroma_store.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Implement `backend/db/chroma_store.py`**

```python
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from pathlib import Path

CHROMA_PATH = str(Path(__file__).parent.parent / "data" / "chroma")

_client = None
_ef = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")


def get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=CHROMA_PATH)
    return _client


def get_or_create_collection(name: str) -> chromadb.Collection:
    return get_client().get_or_create_collection(
        name=name,
        embedding_function=_ef,
        metadata={"hnsw:space": "cosine"},
    )


def collection_exists_with_data(name: str) -> bool:
    try:
        col = get_client().get_collection(name, embedding_function=_ef)
        return col.count() > 0
    except Exception:
        return False


def upsert_documents(
    collection_name: str,
    ids: list[str],
    documents: list[str],
    metadatas: list[dict],
):
    col = get_or_create_collection(collection_name)
    col.upsert(ids=ids, documents=documents, metadatas=metadatas)


def query_collection(
    collection_name: str,
    query_text: str,
    n_results: int = 20,
    where: dict = None,
) -> dict:
    col = get_or_create_collection(collection_name)
    kwargs = {"query_texts": [query_text], "n_results": n_results}
    if where:
        kwargs["where"] = where
    return col.query(**kwargs)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && pytest tests/test_chroma_store.py -v
```
Expected: both tests PASS (first run downloads the SentenceTransformer model, ~80MB)

- [ ] **Step 5: Commit**

```bash
git add backend/db/chroma_store.py backend/tests/test_chroma_store.py
git commit -m "feat: ChromaDB store with SentenceTransformer embeddings"
```

---

## Task 5: wger Client + Knowledge Base Init

**Files:**
- Create: `backend/data/wger_client.py`
- Create: `backend/init_knowledge_base.py`

No unit tests for these (they hit external APIs or are integration-level); they are verified manually.

- [ ] **Step 1: Create `backend/data/wger_client.py`**

```python
import re
import aiohttp

WGER_BASE = "https://wger.de/api/v2"


async def fetch_all_exercises() -> list[dict]:
    exercises = []
    url = f"{WGER_BASE}/exerciseinfo/?format=json&language=2&limit=100&offset=0"
    async with aiohttp.ClientSession() as session:
        while url:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                data = await resp.json()
            for ex in data.get("results", []):
                name = _english_name(ex)
                if not name:
                    continue
                exercises.append({
                    "exercise_id": str(ex["id"]),
                    "name": name,
                    "category": ex["category"]["name"] if ex.get("category") else "General",
                    "muscles": [m["name_en"] for m in ex.get("muscles", []) if m.get("name_en")],
                    "muscles_secondary": [m["name_en"] for m in ex.get("muscles_secondary", []) if m.get("name_en")],
                    "equipment": [e["name"] for e in ex.get("equipment", [])] or ["None"],
                    "description": _english_description(ex),
                })
            url = data.get("next")
    return exercises


def _english_name(ex: dict) -> str:
    for t in ex.get("translations", []):
        if t.get("language") == 2:
            return (t.get("name") or "").strip()
    return ""


def _english_description(ex: dict) -> str:
    for t in ex.get("translations", []):
        if t.get("language") == 2:
            raw = (t.get("description") or "").strip()
            return re.sub(r"<[^>]+>", "", raw).strip()
    return ""
```

- [ ] **Step 2: Create `backend/init_knowledge_base.py`**

```python
import asyncio
import json
from pathlib import Path
from backend.data.wger_client import fetch_all_exercises
from backend.db.chroma_store import collection_exists_with_data, upsert_documents

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
    rules_data = json.loads(RULES_PATH.read_text())
    all_rules = (
        rules_data["training_principles"]
        + rules_data["recovery_rules"]
        + rules_data["nutrition_rules"]
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


def init_knowledge_base():
    _init_rules()
    asyncio.run(_init_exercises())


if __name__ == "__main__":
    init_knowledge_base()
```

- [ ] **Step 3: Run manually to verify**

```bash
cd backend && python init_knowledge_base.py
```
Expected output:
```
[KB] Fetching exercises from wger API...
[KB] Fetched ~847 exercises. Indexing...
[KB] Indexed ~847 exercises.
[KB] Indexed 28 rules.
```
Run again — both should print "already indexed".

- [ ] **Step 4: Commit**

```bash
git add backend/data/wger_client.py backend/init_knowledge_base.py
git commit -m "feat: wger API client and knowledge base initializer"
```

---

## Task 6: Equipment Filter (Pure Function)

**Files:**
- Create: `backend/pipeline/equipment_filter.py`
- Create: `backend/tests/test_equipment_filter.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_equipment_filter.py
from backend.pipeline.equipment_filter import filter_by_equipment

EXERCISES = [
    {"name": "Bicep Curl", "equipment": "Dumbbell"},
    {"name": "Barbell Row", "equipment": "Barbell"},
    {"name": "Pull-up", "equipment": "Pull-up bar"},
    {"name": "Push-up", "equipment": "None"},
    {"name": "Cable Fly", "equipment": "Cable"},
]

def test_filter_keeps_matching_equipment():
    result = filter_by_equipment(EXERCISES, ["dumbbell"])
    names = [e["name"] for e in result]
    assert "Bicep Curl" in names
    assert "Barbell Row" not in names

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

def test_filter_empty_user_equipment_returns_bodyweight_only():
    result = filter_by_equipment(EXERCISES, [])
    names = [e["name"] for e in result]
    assert names == ["Push-up"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && pytest tests/test_equipment_filter.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Implement `backend/pipeline/equipment_filter.py`**

```python
def filter_by_equipment(exercises: list[dict], user_equipment: list[str]) -> list[dict]:
    """Keep exercises whose equipment is in user_equipment or is bodyweight (None)."""
    allowed = {e.lower() for e in user_equipment} | {"none"}
    return [
        ex for ex in exercises
        if ex.get("equipment", "").lower() in allowed
    ]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && pytest tests/test_equipment_filter.py -v
```
Expected: all 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/pipeline/equipment_filter.py backend/tests/test_equipment_filter.py
git commit -m "feat: equipment filter pipeline step"
```

---

## Task 7: Context Assembler (Pure Function)

**Files:**
- Create: `backend/pipeline/context_assembler.py`
- Create: `backend/tests/test_context_assembler.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_context_assembler.py
from backend.pipeline.context_assembler import assemble_prompt, SYSTEM_PROMPT

SAMPLE_INTENT = {
    "target_muscles": ["biceps"],
    "equipment": ["dumbbell"],
    "frequency": 3,
    "intensity": "medium",
    "goal": "hypertrophy",
    "flags": [],
}
SAMPLE_EXERCISES = [
    {"name": "Bicep Curl", "muscles": "Biceps brachii", "equipment": "Dumbbell",
     "description": "Stand with dumbbells, curl up.", "category": "Arms"},
]
SAMPLE_RULES = [
    {"title": "Progressive Overload", "content": "Increase weight over time.", "type": "training_principle"},
]
SAMPLE_MEMORY = {"equipment": ["dumbbell"], "intensity_preference": "medium", "last_goal": "hypertrophy"}

def test_assemble_includes_exercises():
    prompt = assemble_prompt("I want arm gains", SAMPLE_INTENT, SAMPLE_EXERCISES, SAMPLE_RULES, SAMPLE_MEMORY)
    assert "Bicep Curl" in prompt

def test_assemble_includes_rules():
    prompt = assemble_prompt("I want arm gains", SAMPLE_INTENT, SAMPLE_EXERCISES, SAMPLE_RULES, SAMPLE_MEMORY)
    assert "Progressive Overload" in prompt

def test_assemble_includes_user_memory():
    prompt = assemble_prompt("I want arm gains", SAMPLE_INTENT, SAMPLE_EXERCISES, SAMPLE_RULES, SAMPLE_MEMORY)
    assert "dumbbell" in prompt.lower()

def test_assemble_no_memory():
    prompt = assemble_prompt("I want arm gains", SAMPLE_INTENT, SAMPLE_EXERCISES, SAMPLE_RULES, None)
    assert isinstance(prompt, str)
    assert len(prompt) > 100

def test_system_prompt_contains_restrictions():
    assert "medical" in SYSTEM_PROMPT.lower()
    assert "supplement" in SYSTEM_PROMPT.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && pytest tests/test_context_assembler.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Implement `backend/pipeline/context_assembler.py`**

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

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && pytest tests/test_context_assembler.py -v
```
Expected: all 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/pipeline/context_assembler.py backend/tests/test_context_assembler.py
git commit -m "feat: context assembler and system prompt for plan generation"
```

---

## Task 8: Intent Parser

**Files:**
- Create: `backend/pipeline/intent_parser.py`
- Create: `backend/tests/test_intent_parser.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_intent_parser.py
import pytest
import json
from unittest.mock import MagicMock
from backend.pipeline.intent_parser import parse_intent, MEDICAL_FLAGS

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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && pytest tests/test_intent_parser.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Implement `backend/pipeline/intent_parser.py`**

```python
import json
from openai import OpenAI

MEDICAL_FLAGS = [
    "injury", "injured", "pain", "hurt", "surgery", "recovering",
    "pregnant", "pregnancy", "illness", "sick", "disease", "disorder",
    "eating disorder", "chronic", "diabetes", "arthritis", "fracture",
    "doctor", "rehabilitation", "physical therapy",
]

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
- equipment: normalize to: dumbbell, barbell, cable, pull-up bar, resistance band, kettlebell, bench, bodyweight, none
- frequency: default 3 if not specified
- intensity: default "medium" if not specified
- flags: add "medical_concern" if user mentions injury, pain, illness, pregnancy, or medical condition"""


def parse_intent(client: OpenAI, user_input: str) -> dict:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": _PARSE_SYSTEM},
            {"role": "user", "content": user_input},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )
    intent = json.loads(response.choices[0].message.content)

    lower_input = user_input.lower()
    if any(kw in lower_input for kw in MEDICAL_FLAGS):
        if "medical_concern" not in intent.get("flags", []):
            intent.setdefault("flags", []).append("medical_concern")

    return intent
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && pytest tests/test_intent_parser.py -v
```
Expected: all 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/pipeline/intent_parser.py backend/tests/test_intent_parser.py
git commit -m "feat: intent parser with medical safety gate"
```

---

## Task 9: Exercise Retriever + Rule Retriever

**Files:**
- Create: `backend/pipeline/exercise_retriever.py`
- Create: `backend/pipeline/rule_retriever.py`
- Create: `backend/tests/test_exercise_retriever.py`
- Create: `backend/tests/test_rule_retriever.py`

- [ ] **Step 1: Write failing tests for exercise retriever**

```python
# backend/tests/test_exercise_retriever.py
import pytest
from unittest.mock import patch, MagicMock

def make_chroma_result(names: list[str]):
    return {
        "ids": [[str(i) for i in range(len(names))]],
        "metadatas": [[{"name": n, "category": "Arms", "muscles": "Biceps brachii",
                        "muscles_secondary": "", "equipment": "Dumbbell",
                        "description": "test"} for n in names]],
        "distances": [[0.1] * len(names)],
    }

def test_retrieve_exercises_returns_list():
    from backend.pipeline.exercise_retriever import retrieve_exercises
    mock_result = make_chroma_result(["Bicep Curl", "Hammer Curl"])
    with patch("backend.pipeline.exercise_retriever.query_collection", return_value=mock_result):
        result = retrieve_exercises(["biceps"], "hypertrophy", n_results=20)
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["name"] == "Bicep Curl"

def test_retrieve_exercises_query_uses_muscles():
    from backend.pipeline.exercise_retriever import retrieve_exercises
    mock_result = make_chroma_result([])
    mock_result["ids"] = [[]]
    mock_result["metadatas"] = [[]]
    mock_result["distances"] = [[]]
    with patch("backend.pipeline.exercise_retriever.query_collection", return_value=mock_result) as mock_q:
        retrieve_exercises(["biceps", "triceps"], "hypertrophy")
    call_args = mock_q.call_args
    assert "biceps" in call_args[0][1].lower() or "biceps" in str(call_args)
```

- [ ] **Step 2: Write failing tests for rule retriever**

```python
# backend/tests/test_rule_retriever.py
from unittest.mock import patch

def make_rule_result(rules: list[dict]):
    return {
        "ids": [[r["id"] for r in rules]],
        "metadatas": [rules],
        "distances": [[0.1] * len(rules)],
    }

def test_retrieve_rules_returns_training_and_nutrition():
    from backend.pipeline.rule_retriever import retrieve_rules
    training = [{"id": "tp1", "type": "training_principle", "title": "Progressive Overload",
                 "content": "Increase weight.", "tags": "hypertrophy"}]
    nutrition = [{"id": "nr1", "type": "nutrition_rule", "title": "Protein Intake",
                  "content": "1.6g/kg.", "tags": "protein"}]
    with patch("backend.pipeline.rule_retriever.query_collection") as mock_q:
        mock_q.side_effect = [make_rule_result(training), make_rule_result(nutrition)]
        result = retrieve_rules("hypertrophy")
    assert len(result) == 2
    types = {r["type"] for r in result}
    assert "training_principle" in types
    assert "nutrition_rule" in types
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd backend && pytest tests/test_exercise_retriever.py tests/test_rule_retriever.py -v
```
Expected: `ImportError` for both

- [ ] **Step 4: Implement `backend/pipeline/exercise_retriever.py`**

```python
from backend.db.chroma_store import query_collection


def retrieve_exercises(target_muscles: list[str], goal: str, n_results: int = 20) -> list[dict]:
    muscles_str = " ".join(target_muscles)
    query = f"{muscles_str} {goal} exercises"
    results = query_collection("exercises", query, n_results=n_results)

    exercises = []
    for meta in results["metadatas"][0]:
        exercises.append({
            "name": meta.get("name", ""),
            "category": meta.get("category", ""),
            "muscles": meta.get("muscles", ""),
            "muscles_secondary": meta.get("muscles_secondary", ""),
            "equipment": meta.get("equipment", "None"),
            "description": meta.get("description", ""),
        })
    return exercises
```

- [ ] **Step 5: Implement `backend/pipeline/rule_retriever.py`**

```python
from backend.db.chroma_store import query_collection


def retrieve_rules(goal: str, n_training: int = 5, n_nutrition: int = 3) -> list[dict]:
    training_query = f"{goal} training principles sets reps rest recovery"
    nutrition_query = f"{goal} nutrition protein diet food"

    training_results = query_collection("rules", training_query, n_results=n_training,
                                         where={"type": {"$ne": "nutrition_rule"}})
    nutrition_results = query_collection("rules", nutrition_query, n_results=n_nutrition,
                                          where={"type": {"$eq": "nutrition_rule"}})

    rules = []
    for meta in training_results["metadatas"][0]:
        rules.append(dict(meta))
    for meta in nutrition_results["metadatas"][0]:
        rules.append(dict(meta))
    return rules
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd backend && pytest tests/test_exercise_retriever.py tests/test_rule_retriever.py -v
```
Expected: all tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/pipeline/exercise_retriever.py backend/pipeline/rule_retriever.py \
        backend/tests/test_exercise_retriever.py backend/tests/test_rule_retriever.py
git commit -m "feat: exercise retriever and rule retriever pipeline steps"
```

---

## Task 10: Memory Retriever

**Files:**
- Create: `backend/pipeline/memory_retriever.py`
- Create: `backend/tests/test_memory_retriever.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_memory_retriever.py
from backend.pipeline.memory_retriever import retrieve_memory

def test_retrieve_memory_returns_data(temp_db):
    token = temp_db.create_user()
    user_id = temp_db.get_user_id(token)
    temp_db.upsert_user_memory(user_id, ["dumbbell"], "medium", "hypertrophy")
    memory = retrieve_memory(user_id)
    assert memory["equipment"] == ["dumbbell"]
    assert memory["intensity_preference"] == "medium"

def test_retrieve_memory_no_user(temp_db):
    assert retrieve_memory(9999) is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && pytest tests/test_memory_retriever.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Implement `backend/pipeline/memory_retriever.py`**

```python
from backend.db.sqlite_store import get_user_memory


def retrieve_memory(user_id: int) -> dict | None:
    return get_user_memory(user_id)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && pytest tests/test_memory_retriever.py -v
```
Expected: both tests PASS

- [ ] **Step 5: Run full backend test suite**

```bash
cd backend && pytest -v
```
Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/pipeline/memory_retriever.py backend/tests/test_memory_retriever.py
git commit -m "feat: memory retriever pipeline step — completes IR pipeline"
```

---

## Task 11: FastAPI Routes

**Files:**
- Create: `backend/main.py`
- Create: `backend/tests/test_routes.py`

- [ ] **Step 1: Write the failing route tests**

```python
# backend/tests/test_routes.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json

@pytest.fixture
def client(temp_db, tmp_path, monkeypatch):
    import backend.db.chroma_store as cs
    monkeypatch.setattr(cs, "CHROMA_PATH", str(tmp_path / "chroma"))
    cs._client = None
    from backend.main import app
    return TestClient(app)

def test_create_session(client):
    response = client.post("/api/session")
    assert response.status_code == 200
    data = response.json()
    assert "session_token" in data
    assert len(data["session_token"]) == 36

def test_validate_key_invalid(client):
    with patch("backend.main.OpenAI") as mock_cls:
        instance = MagicMock()
        instance.models.list.side_effect = Exception("Invalid API key")
        mock_cls.return_value = instance
        response = client.post("/api/validate-key", json={"api_key": "bad-key"})
    assert response.status_code == 200
    assert response.json()["valid"] is False

def test_validate_key_valid(client):
    with patch("backend.main.OpenAI") as mock_cls:
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
    with patch("backend.main.parse_intent") as mock_parse:
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && pytest tests/test_routes.py -v
```
Expected: `ImportError` for `backend.main`

- [ ] **Step 3: Implement `backend/main.py`**

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import json

from backend.db.sqlite_store import init_db, create_user, get_user_id, get_user_memory, get_plan_history, upsert_user_memory, save_plan
from backend.init_knowledge_base import init_knowledge_base
from backend.pipeline.intent_parser import parse_intent
from backend.pipeline.exercise_retriever import retrieve_exercises
from backend.pipeline.equipment_filter import filter_by_equipment
from backend.pipeline.rule_retriever import retrieve_rules
from backend.pipeline.memory_retriever import retrieve_memory
from backend.pipeline.context_assembler import assemble_prompt, SYSTEM_PROMPT


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    init_knowledge_base()
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ApiKeyRequest(BaseModel):
    api_key: str


class PlanRequest(BaseModel):
    session_token: str
    api_key: str
    user_input: str


@app.post("/api/session")
def create_session():
    token = create_user()
    return {"session_token": token}


@app.get("/api/session/{token}")
def get_session(token: str):
    user_id = get_user_id(token)
    if user_id is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "user_id": user_id,
        "memory": get_user_memory(user_id),
        "history": get_plan_history(user_id),
    }


@app.post("/api/validate-key")
def validate_key(body: ApiKeyRequest):
    try:
        client = OpenAI(api_key=body.api_key)
        client.models.list()
        return {"valid": True, "message": "Connected successfully"}
    except Exception as e:
        return {"valid": False, "message": str(e)}


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

    exercises_raw = retrieve_exercises(intent["target_muscles"], intent["goal"])
    exercises_filtered = filter_by_equipment(exercises_raw, intent["equipment"])
    rules = retrieve_rules(intent["goal"])
    memory = retrieve_memory(user_id)

    prompt = assemble_prompt(body.user_input, intent, exercises_filtered, rules, memory)

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

    upsert_user_memory(user_id, intent["equipment"], intent["intensity"], intent["goal"])
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

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && pytest tests/test_routes.py -v
```
Expected: all 5 tests PASS

- [ ] **Step 5: Run full test suite**

```bash
cd backend && pytest -v
```
Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/main.py backend/tests/test_routes.py
git commit -m "feat: FastAPI routes — session, key validation, plan generation"
```

---

## Task 12: Frontend Scaffold + Pixel CSS

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.js`
- Create: `frontend/index.html`
- Create: `frontend/src/main.jsx`
- Create: `frontend/src/styles/pixel.css`
- Create: `frontend/src/components/PixelButton.jsx`
- Create: `frontend/src/api.js`

- [ ] **Step 1: Create `frontend/package.json`**

```json
{
  "name": "gym-smith-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.23.1",
    "axios": "^1.7.2"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.1",
    "vite": "^5.3.1"
  }
}
```

- [ ] **Step 2: Create `frontend/vite.config.js`**

```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
```

- [ ] **Step 3: Create `frontend/index.html`**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Gym Smith</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&family=VT323:wght@400&display=swap" rel="stylesheet" />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

- [ ] **Step 4: Create `frontend/src/styles/pixel.css`**

```css
:root {
  --bg: #F5F0E8;
  --card-bg: #FFFDF5;
  --primary: #7BC67E;
  --primary-dark: #5aaa5d;
  --secondary: #A8D8A8;
  --text: #2D2D2D;
  --text-muted: #666;
  --warning: #FF8A65;
  --border: 2px solid #2D2D2D;
  --shadow: 4px 4px 0px #2D2D2D;
  --shadow-sm: 2px 2px 0px #2D2D2D;
  --font-title: 'Press Start 2P', monospace;
  --font-body: 'VT323', monospace;
  --radius: 0px;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  background-color: var(--bg);
  color: var(--text);
  font-family: var(--font-body);
  font-size: 18px;
  min-height: 100vh;
}

.pixel-card {
  background: var(--card-bg);
  border: var(--border);
  box-shadow: var(--shadow);
  padding: 16px;
}

.pixel-input {
  background: var(--card-bg);
  border: var(--border);
  box-shadow: var(--shadow-sm);
  padding: 10px 12px;
  font-family: var(--font-body);
  font-size: 18px;
  color: var(--text);
  outline: none;
  width: 100%;
}

.pixel-input:focus {
  box-shadow: var(--shadow);
}

.tag {
  display: inline-block;
  background: var(--secondary);
  border: 1px solid #2D2D2D;
  padding: 2px 8px;
  font-family: var(--font-body);
  font-size: 16px;
  margin: 2px;
}

.warning-box {
  background: #FFF3EE;
  border: 2px solid var(--warning);
  box-shadow: 4px 4px 0px var(--warning);
  padding: 16px;
  color: var(--text);
}

h1, h2, h3 { font-family: var(--font-title); line-height: 1.6; }
h1 { font-size: 1.4rem; }
h2 { font-size: 1rem; }
h3 { font-size: 0.8rem; }
```

- [ ] **Step 5: Create `frontend/src/api.js`**

```js
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

export async function generatePlan(sessionToken, apiKey, userInput) {
  const { data } = await api.post('/plan', {
    session_token: sessionToken,
    api_key: apiKey,
    user_input: userInput,
  })
  return data
}
```

- [ ] **Step 6: Create `frontend/src/components/PixelButton.jsx`**

```jsx
import '../styles/pixel.css'

export default function PixelButton({ children, onClick, disabled, variant = 'primary', style = {} }) {
  const styles = {
    primary: {
      background: disabled ? '#ccc' : 'var(--primary)',
      border: 'var(--border)',
      boxShadow: disabled ? 'none' : 'var(--shadow)',
      color: 'var(--text)',
    },
    danger: {
      background: disabled ? '#ccc' : 'var(--warning)',
      border: 'var(--border)',
      boxShadow: disabled ? 'none' : '4px 4px 0px #2D2D2D',
      color: 'var(--text)',
    },
    ghost: {
      background: 'transparent',
      border: 'var(--border)',
      boxShadow: 'none',
      color: 'var(--text)',
    },
  }

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        ...styles[variant],
        fontFamily: 'var(--font-title)',
        fontSize: '0.65rem',
        padding: '10px 16px',
        cursor: disabled ? 'not-allowed' : 'pointer',
        letterSpacing: '0.05em',
        transition: 'box-shadow 0.1s, transform 0.1s',
        ...style,
      }}
      onMouseDown={e => !disabled && (e.currentTarget.style.transform = 'translate(2px,2px)')}
      onMouseUp={e => !disabled && (e.currentTarget.style.transform = '')}
      onMouseLeave={e => (e.currentTarget.style.transform = '')}
    >
      {children}
    </button>
  )
}
```

- [ ] **Step 7: Create `frontend/src/main.jsx`**

```jsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './styles/pixel.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
```

- [ ] **Step 8: Install frontend dependencies**

```bash
cd frontend && npm install
```

- [ ] **Step 9: Commit**

```bash
git add frontend/
git commit -m "feat: React frontend scaffold with pixel art CSS and PixelButton"
```

---

## Task 13: ApiKeyPage

**Files:**
- Create: `frontend/src/pages/ApiKeyPage.jsx`

- [ ] **Step 1: Create `frontend/src/pages/ApiKeyPage.jsx`**

```jsx
import { useState } from 'react'
import { validateKey, createSession } from '../api'
import PixelButton from '../components/PixelButton'
import '../styles/pixel.css'

export default function ApiKeyPage({ onConnected }) {
  const [key, setKey] = useState('')
  const [status, setStatus] = useState(null) // null | 'loading' | 'ok' | 'error'
  const [message, setMessage] = useState('')

  async function handleConnect() {
    if (!key.trim()) return
    setStatus('loading')
    setMessage('')
    try {
      const result = await validateKey(key.trim())
      if (result.valid) {
        let token = localStorage.getItem('gym_smith_token')
        if (!token) {
          const session = await createSession()
          token = session.session_token
          localStorage.setItem('gym_smith_token', token)
        }
        setStatus('ok')
        setTimeout(() => onConnected(key.trim(), token), 600)
      } else {
        setStatus('error')
        setMessage(result.message || 'Invalid API key')
      }
    } catch {
      setStatus('error')
      setMessage('Could not reach the server.')
    }
  }

  const dumbbell = '🏋'

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center', padding: '24px',
      background: 'var(--bg)',
    }}>
      {/* Decorative pixel icons */}
      <div style={{ fontSize: '2rem', marginBottom: '8px', letterSpacing: '12px' }}>
        {dumbbell} {dumbbell} {dumbbell}
      </div>

      <div className="pixel-card" style={{ width: '100%', maxWidth: '480px' }}>
        <h1 style={{ textAlign: 'center', marginBottom: '8px', fontSize: '1.2rem' }}>
          GYM SMITH
        </h1>
        <p style={{ fontFamily: 'var(--font-body)', fontSize: '18px', textAlign: 'center',
                    color: 'var(--text-muted)', marginBottom: '24px' }}>
          Your IR-Powered Fitness Planner
        </p>

        <label style={{ fontFamily: 'var(--font-title)', fontSize: '0.6rem',
                        display: 'block', marginBottom: '8px' }}>
          OPENAI API KEY
        </label>
        <input
          className="pixel-input"
          type="password"
          placeholder="sk-..."
          value={key}
          onChange={e => setKey(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleConnect()}
          style={{ marginBottom: '16px' }}
        />

        <PixelButton
          onClick={handleConnect}
          disabled={status === 'loading' || !key.trim()}
          style={{ width: '100%', justifyContent: 'center' }}
        >
          {status === 'loading' ? 'CONNECTING...' : status === 'ok' ? '✓ CONNECTED!' : '[ CONNECT ]'}
        </PixelButton>

        {status === 'error' && (
          <div className="warning-box" style={{ marginTop: '16px', fontSize: '16px' }}>
            ✗ {message}
          </div>
        )}

        {status === 'ok' && (
          <div style={{ marginTop: '16px', padding: '10px', background: '#e8f8e8',
                        border: '2px solid var(--primary)', fontSize: '16px',
                        fontFamily: 'var(--font-body)' }}>
            ✓ Connected! Loading your workspace...
          </div>
        )}
      </div>

      <p style={{ marginTop: '16px', fontFamily: 'var(--font-body)', fontSize: '14px',
                  color: 'var(--text-muted)', textAlign: 'center' }}>
        Your key is never stored on the server.
      </p>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/ApiKeyPage.jsx
git commit -m "feat: ApiKeyPage with pixel art style and key validation"
```

---

## Task 14: SidebarMemory + PlanCard + IrProcessPanel

**Files:**
- Create: `frontend/src/components/SidebarMemory.jsx`
- Create: `frontend/src/components/PlanCard.jsx`
- Create: `frontend/src/components/IrProcessPanel.jsx`

- [ ] **Step 1: Create `frontend/src/components/SidebarMemory.jsx`**

```jsx
import '../styles/pixel.css'
import PixelButton from './PixelButton'

export default function SidebarMemory({ memory, history, onNewPlan }) {
  return (
    <div style={{
      width: '220px', minHeight: '100vh', borderRight: 'var(--border)',
      background: 'var(--card-bg)', padding: '16px', flexShrink: 0,
    }}>
      {/* Logo */}
      <h2 style={{ fontSize: '0.7rem', marginBottom: '20px', borderBottom: 'var(--border)',
                   paddingBottom: '10px' }}>
        ⚙ GYM SMITH
      </h2>

      {/* Stats */}
      <div style={{ marginBottom: '20px' }}>
        <h3 style={{ fontSize: '0.55rem', marginBottom: '10px', color: 'var(--text-muted)' }}>
          YOUR PROFILE
        </h3>
        {memory ? (
          <div style={{ fontFamily: 'var(--font-body)', fontSize: '16px', lineHeight: '1.8' }}>
            <div><span style={{ color: 'var(--text-muted)' }}>Goal:</span> {memory.last_goal || '—'}</div>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Equipment:</span>
              <div style={{ marginTop: '4px' }}>
                {(memory.equipment || []).map(e => (
                  <span key={e} className="tag">{e}</span>
                ))}
              </div>
            </div>
            <div><span style={{ color: 'var(--text-muted)' }}>Intensity:</span> {memory.intensity_preference || '—'}</div>
          </div>
        ) : (
          <p style={{ fontFamily: 'var(--font-body)', fontSize: '16px', color: 'var(--text-muted)' }}>
            No profile yet.
          </p>
        )}
      </div>

      {/* History */}
      <div style={{ marginBottom: '20px' }}>
        <h3 style={{ fontSize: '0.55rem', marginBottom: '10px', color: 'var(--text-muted)' }}>
          HISTORY
        </h3>
        {history && history.length > 0 ? (
          <ul style={{ listStyle: 'none', fontFamily: 'var(--font-body)', fontSize: '15px' }}>
            {history.map((h, i) => (
              <li key={i} style={{ padding: '4px 0', borderBottom: '1px dashed #ccc',
                                   overflow: 'hidden', textOverflow: 'ellipsis',
                                   whiteSpace: 'nowrap', color: 'var(--text-muted)' }}
                  title={h.user_input}>
                · {h.user_input.slice(0, 22)}{h.user_input.length > 22 ? '…' : ''}
              </li>
            ))}
          </ul>
        ) : (
          <p style={{ fontFamily: 'var(--font-body)', fontSize: '16px', color: 'var(--text-muted)' }}>
            No history yet.
          </p>
        )}
      </div>

      <PixelButton onClick={onNewPlan} style={{ width: '100%' }} variant="ghost">
        + NEW PLAN
      </PixelButton>
    </div>
  )
}
```

- [ ] **Step 2: Create `frontend/src/components/PlanCard.jsx`**

```jsx
import { useState } from 'react'
import '../styles/pixel.css'

function ExerciseRow({ ex }) {
  return (
    <div style={{ padding: '8px 0', borderBottom: '1px dashed #ccc', fontFamily: 'var(--font-body)',
                  fontSize: '17px' }}>
      <div style={{ fontWeight: 'bold' }}>▸ {ex.name}</div>
      <div style={{ color: 'var(--text-muted)', marginTop: '2px' }}>
        {ex.sets} sets × {ex.reps} reps · rest {ex.rest} · {ex.equipment}
      </div>
      {ex.muscles?.length > 0 && (
        <div style={{ marginTop: '2px' }}>
          {ex.muscles.map(m => <span key={m} className="tag">{m}</span>)}
        </div>
      )}
      {ex.alternative && (
        <div style={{ color: 'var(--text-muted)', fontSize: '15px', marginTop: '2px' }}>
          Alt: {ex.alternative}
        </div>
      )}
    </div>
  )
}

export default function PlanCard({ day }) {
  const [open, setOpen] = useState(true)

  return (
    <div className="pixel-card" style={{ marginBottom: '16px' }}>
      <div
        style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                 cursor: 'pointer', marginBottom: open ? '12px' : '0' }}
        onClick={() => setOpen(o => !o)}
      >
        <h3 style={{ fontSize: '0.7rem' }}>{day.day} — {day.focus}</h3>
        <span style={{ fontFamily: 'var(--font-body)', fontSize: '20px' }}>{open ? '▲' : '▼'}</span>
      </div>
      {open && (
        <div>
          {day.exercises.map((ex, i) => <ExerciseRow key={i} ex={ex} />)}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 3: Create `frontend/src/components/IrProcessPanel.jsx`**

```jsx
import { useState } from 'react'
import '../styles/pixel.css'

export default function IrProcessPanel({ irProcess }) {
  const [open, setOpen] = useState(false)
  if (!irProcess) return null

  const { parsed_intent, exercises_retrieved, exercises_after_filter,
          training_rules_used, nutrition_rules_used, memory_loaded } = irProcess

  return (
    <div style={{ marginTop: '24px' }}>
      <div
        style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px',
                 fontFamily: 'var(--font-title)', fontSize: '0.6rem', padding: '8px 0',
                 borderTop: 'var(--border)' }}
        onClick={() => setOpen(o => !o)}
      >
        <span>IR PROCESS TRACE</span>
        <span style={{ fontFamily: 'var(--font-body)', fontSize: '18px' }}>{open ? '▲' : '▼'}</span>
      </div>

      {open && (
        <div className="pixel-card" style={{ fontFamily: 'var(--font-body)', fontSize: '16px',
                                              lineHeight: '1.7' }}>
          <Section title="1. PARSED INTENT">
            <pre style={{ background: '#f0f0e8', padding: '8px', border: '1px solid #ccc',
                          fontSize: '14px', overflow: 'auto' }}>
              {JSON.stringify(parsed_intent, null, 2)}
            </pre>
          </Section>

          <Section title="2. EXERCISES RETRIEVED">
            <div>{(exercises_retrieved || []).map(n => <span key={n} className="tag">{n}</span>)}</div>
          </Section>

          <Section title="3. AFTER EQUIPMENT FILTER">
            <div>{(exercises_after_filter || []).map(n => <span key={n} className="tag" style={{ background: 'var(--primary)' }}>{n}</span>)}</div>
            {exercises_retrieved && exercises_after_filter && (
              <div style={{ color: 'var(--text-muted)', marginTop: '4px', fontSize: '15px' }}>
                {exercises_retrieved.length - exercises_after_filter.length} exercises removed by equipment filter
              </div>
            )}
          </Section>

          <Section title="4. TRAINING RULES USED">
            <ul style={{ paddingLeft: '16px' }}>
              {(training_rules_used || []).map(r => <li key={r}>{r}</li>)}
            </ul>
          </Section>

          <Section title="5. NUTRITION RULES USED">
            <ul style={{ paddingLeft: '16px' }}>
              {(nutrition_rules_used || []).map(r => <li key={r}>{r}</li>)}
            </ul>
          </Section>

          <Section title="6. MEMORY LOADED">
            {memory_loaded ? (
              <pre style={{ background: '#f0f0e8', padding: '8px', border: '1px solid #ccc',
                            fontSize: '14px', overflow: 'auto' }}>
                {JSON.stringify(memory_loaded, null, 2)}
              </pre>
            ) : (
              <span style={{ color: 'var(--text-muted)' }}>No previous session found.</span>
            )}
          </Section>
        </div>
      )}
    </div>
  )
}

function Section({ title, children }) {
  return (
    <div style={{ marginBottom: '16px' }}>
      <div style={{ fontFamily: 'var(--font-title)', fontSize: '0.5rem', marginBottom: '6px',
                    color: 'var(--text-muted)' }}>
        {title}
      </div>
      {children}
    </div>
  )
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/
git commit -m "feat: SidebarMemory, PlanCard, and IrProcessPanel components"
```

---

## Task 15: MainPage + App.jsx

**Files:**
- Create: `frontend/src/pages/MainPage.jsx`
- Create: `frontend/src/App.jsx`

- [ ] **Step 1: Create `frontend/src/pages/MainPage.jsx`**

```jsx
import { useState, useEffect, useRef } from 'react'
import { getSession, generatePlan } from '../api'
import SidebarMemory from '../components/SidebarMemory'
import PlanCard from '../components/PlanCard'
import IrProcessPanel from '../components/IrProcessPanel'
import PixelButton from '../components/PixelButton'
import '../styles/pixel.css'

export default function MainPage({ apiKey, sessionToken }) {
  const [sessionData, setSessionData] = useState(null)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const planRef = useRef(null)

  useEffect(() => {
    getSession(sessionToken).then(setSessionData).catch(() => {})
  }, [sessionToken])

  function handleNewPlan() {
    setResult(null)
    setInput('')
    setError(null)
  }

  async function handleGenerate() {
    if (!input.trim() || loading) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await generatePlan(sessionToken, apiKey, input.trim())
      setResult(data)
      if (!data.is_medical_concern) {
        getSession(sessionToken).then(setSessionData).catch(() => {})
        setTimeout(() => planRef.current?.scrollIntoView({ behavior: 'smooth' }), 100)
      }
    } catch (e) {
      setError('Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const plan = result?.plan
  const irProcess = result?.ir_process

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <SidebarMemory
        memory={sessionData?.memory}
        history={sessionData?.history}
        onNewPlan={handleNewPlan}
      />

      <main style={{ flex: 1, padding: '24px', maxWidth: '800px' }}>
        {/* Header */}
        <div style={{ marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '1.5rem' }}>🏋</span>
          <h1 style={{ fontSize: '0.9rem' }}>GYM SMITH</h1>
          <span style={{ fontFamily: 'var(--font-body)', fontSize: '16px',
                         color: 'var(--text-muted)' }}>IR Fitness Planner</span>
        </div>

        {/* Input Area */}
        <div className="pixel-card" style={{ marginBottom: '24px' }}>
          <label style={{ fontFamily: 'var(--font-title)', fontSize: '0.55rem',
                          display: 'block', marginBottom: '8px' }}>
            DESCRIBE YOUR GOAL
          </label>
          <textarea
            className="pixel-input"
            rows={4}
            placeholder="e.g. I want to build arm muscle, 3x/week, I have dumbbells and resistance bands, medium intensity"
            value={input}
            onChange={e => setInput(e.target.value)}
            style={{ resize: 'vertical', marginBottom: '12px' }}
          />
          <PixelButton onClick={handleGenerate} disabled={loading || !input.trim()}>
            {loading ? 'GENERATING...' : '[ GENERATE PLAN ]'}
          </PixelButton>
        </div>

        {/* Error */}
        {error && (
          <div className="warning-box" style={{ marginBottom: '16px' }}>
            {error}
          </div>
        )}

        {/* Medical Concern */}
        {result?.is_medical_concern && (
          <div className="warning-box" style={{ marginBottom: '24px' }}>
            <h3 style={{ marginBottom: '8px', fontSize: '0.6rem' }}>⚠ OUTSIDE SCOPE</h3>
            <p style={{ fontFamily: 'var(--font-body)', fontSize: '17px' }}>
              {result.message}
            </p>
          </div>
        )}

        {/* Plan Output */}
        {plan && (
          <div ref={planRef}>
            {/* Goal Summary */}
            <div className="pixel-card" style={{ marginBottom: '16px', background: '#eef8ee' }}>
              <h2 style={{ fontSize: '0.7rem', marginBottom: '8px' }}>GOAL</h2>
              <p style={{ fontFamily: 'var(--font-body)', fontSize: '18px' }}>
                {plan.goal_summary}
              </p>
              {plan.equipment_needed?.length > 0 && (
                <div style={{ marginTop: '8px' }}>
                  <span style={{ fontFamily: 'var(--font-title)', fontSize: '0.5rem',
                                 color: 'var(--text-muted)' }}>EQUIPMENT: </span>
                  {plan.equipment_needed.map(e => (
                    <span key={e} className="tag">{e}</span>
                  ))}
                </div>
              )}
            </div>

            {/* Weekly Schedule */}
            <h2 style={{ fontSize: '0.7rem', marginBottom: '12px' }}>WEEKLY SCHEDULE</h2>
            {(plan.weekly_schedule || []).map((day, i) => (
              <PlanCard key={i} day={day} />
            ))}

            {/* Nutrition Notes */}
            {plan.nutrition_notes?.length > 0 && (
              <div className="pixel-card" style={{ marginBottom: '16px' }}>
                <h2 style={{ fontSize: '0.7rem', marginBottom: '8px' }}>NUTRITION NOTES</h2>
                <ul style={{ fontFamily: 'var(--font-body)', fontSize: '17px',
                              paddingLeft: '16px', lineHeight: '1.8' }}>
                  {plan.nutrition_notes.map((n, i) => <li key={i}>{n}</li>)}
                </ul>
              </div>
            )}

            {/* Safety Reminder */}
            {plan.safety_reminder && (
              <div style={{ padding: '10px', background: '#fff9f0',
                            border: '1px dashed #ccc', fontFamily: 'var(--font-body)',
                            fontSize: '16px', color: 'var(--text-muted)', marginBottom: '16px' }}>
                ⚠ {plan.safety_reminder}
              </div>
            )}

            {/* IR Process Panel */}
            <IrProcessPanel irProcess={irProcess} />
          </div>
        )}
      </main>
    </div>
  )
}
```

- [ ] **Step 2: Create `frontend/src/App.jsx`**

```jsx
import { useState, useEffect } from 'react'
import ApiKeyPage from './pages/ApiKeyPage'
import MainPage from './pages/MainPage'

export default function App() {
  const [apiKey, setApiKey] = useState(null)
  const [sessionToken, setSessionToken] = useState(null)

  useEffect(() => {
    const token = localStorage.getItem('gym_smith_token')
    const key = sessionStorage.getItem('gym_smith_key')
    if (token && key) {
      setSessionToken(token)
      setApiKey(key)
    }
  }, [])

  function handleConnected(key, token) {
    sessionStorage.setItem('gym_smith_key', key)
    setApiKey(key)
    setSessionToken(token)
  }

  if (!apiKey || !sessionToken) {
    return <ApiKeyPage onConnected={handleConnected} />
  }

  return <MainPage apiKey={apiKey} sessionToken={sessionToken} />
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/MainPage.jsx frontend/src/App.jsx
git commit -m "feat: MainPage and App routing — frontend complete"
```

---

## Task 16: README + .env.example + Final Wiring

**Files:**
- Create: `.env.example`
- Create: `README.md`

- [ ] **Step 1: Create `.env.example`**

```
# Copy this to .env and fill in your key if running init separately
OPENAI_API_KEY=sk-your-key-here
```

- [ ] **Step 2: Create `README.md`**

```markdown
# Gym Smith — IR-Powered Fitness Planning Agent

A retrieval-augmented fitness planning agent. Uses ChromaDB vector search over the wger exercise database and a hand-authored rules knowledge base to generate personalized weekly training plans.

## Requirements

- Python 3.11+
- Node.js 18+
- An OpenAI API key (GPT-4o access)

## Setup & Run

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

On first startup, the server will:
1. Initialize the SQLite database
2. Download the sentence-transformer model (~80MB, one-time)
3. Fetch ~847 exercises from the wger API and index them in ChromaDB
4. Index 28 training/nutrition rules

This takes 2-5 minutes the first time. Subsequent startups are instant.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — enter your OpenAI API key to begin.

## IR Methods Used

| Method | Where |
|--------|-------|
| Semantic vector search | Exercise retrieval (ChromaDB + SentenceTransformer) |
| Semantic vector search | Rule retrieval (ChromaDB + SentenceTransformer) |
| Metadata filtering | Equipment-aware exercise filtering |
| Structured memory retrieval | User preferences from SQLite |
| LLM-based intent parsing | Structured extraction from natural language |

## Architecture

```
React → FastAPI → IR Pipeline (6 steps) → GPT-4o
                     ├── ChromaDB (exercises + rules)
                     └── SQLite (user memory)
```
```

- [ ] **Step 3: Final integration test — start both servers**

Terminal 1:
```bash
cd backend && uvicorn main:app --reload
```

Terminal 2:
```bash
cd frontend && npm run dev
```

Open http://localhost:5173, enter a valid OpenAI API key, and test with:
```
I want to build arm muscles, 3 times a week, I have dumbbells and resistance bands, medium intensity.
```

Verify:
- Plan is generated with exercises
- IR Process panel shows retrieved exercises, rules, and memory
- Left sidebar updates with profile after plan generation
- Generating a second plan shows the first plan in history

- [ ] **Step 4: Final commit**

```bash
git add .env.example README.md
git commit -m "feat: README, .env.example — gym smith complete"
```

---

## Self-Review Checklist

- [x] **Spec coverage:**
  - Intent parser (Step 1) → Task 8 ✓
  - Exercise retriever (Step 2) → Task 9 ✓
  - Equipment filter (Step 3) → Task 6 ✓
  - Rule retriever (Step 4) → Task 9 ✓
  - Memory retriever (Step 5) → Task 10 ✓
  - Context assembler (Step 6) → Task 7 ✓
  - SQLite user memory → Task 3 ✓
  - ChromaDB vector store → Task 4 ✓
  - wger API knowledge base init → Task 5 ✓
  - rules.json → Task 2 ✓
  - FastAPI routes → Task 11 ✓
  - API key input page → Task 13 ✓
  - Main page layout → Task 15 ✓
  - IR Process Panel (assignment demo) → Task 14 ✓
  - Pixel art UI → Tasks 12-15 ✓
  - Safety gate (medical concern) → Tasks 8, 11, 15 ✓
  - README → Task 16 ✓

- [x] **Type consistency:** `filter_by_equipment` takes `list[dict]` with `equipment` string field — matches output of `retrieve_exercises` ✓. `assemble_prompt` takes `list[dict]` rules with `type`, `title`, `content` fields — matches `retrieve_rules` output ✓.

- [x] **No placeholders:** All steps contain actual code. ✓
