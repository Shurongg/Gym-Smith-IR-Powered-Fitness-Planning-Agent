# Gym Smith — IR-Powered Fitness Planning Agent

A retrieval-augmented fitness-planning agent built on a **two-stage GPT-4o pipeline** with ChromaDB vector search over two exercise databases (wger REST API + Free Exercise DB) plus a hand-authored rules KB. Generates personalized weekly training plans grounded in retrieved knowledge.

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
1. Initialize the SQLite database (with idempotent schema migrations)
2. Download the sentence-transformer model `all-MiniLM-L6-v2` (~80MB, one-time)
3. Fetch ~847 exercises from the wger REST API
4. Fetch ~800 exercises from Free Exercise DB (GitHub, no API key)
5. Index everything in ChromaDB with normalized equipment metadata (~5 minutes)
6. Index training/nutrition rules from markdown files

Subsequent startups are instant. To re-index, delete `backend/data/chroma/` first.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — first-time users land on an onboarding screen (nickname + training level), then enter their OpenAI key.

## Project Structure

```
assignment_2/
├── backend/
│   ├── main.py                      # FastAPI app, two-stage agent loop, API routes
│   ├── init_knowledge_base.py       # KB initialization (idempotent)
│   ├── pipeline/
│   │   ├── intent_parser.py         # Medical safety gate (slim; rest moved to agent)
│   │   ├── context_assembler.py     # STAGE1_REASONING_PROMPT + Stage-2 SYSTEM_PROMPT
│   │   ├── exercise_retriever.py    # Per-muscle ChromaDB vector search
│   │   ├── equipment_filter.py      # Metadata filter (with cable/machine name fallback)
│   │   ├── rule_retriever.py        # Rule semantic search
│   │   ├── memory_retriever.py      # User memory lookup
│   │   └── web_search.py            # DuckDuckGo fallback
│   ├── data/
│   │   ├── wger_client.py           # wger REST API client
│   │   ├── freeexdb_client.py       # Free Exercise DB client
│   │   └── rules/                   # 7 markdown rule files (~40 rules)
│   ├── db/
│   │   ├── chroma_store.py          # ChromaDB wrapper (telemetry-silenced)
│   │   └── sqlite_store.py          # Sessions, memory, plan history, identity, pinning
│   └── tests/                       # pytest test suite
└── frontend/
    ├── public/hero.png              # Pixel-art hero artwork
    └── src/
        ├── App.jsx                  # Routing: Onboarding → ApiKey → MainPage
        ├── pages/
        │   ├── IdentityPage.jsx     # Onboarding: nickname + training level
        │   ├── ApiKeyPage.jsx       # OpenAI key validation
        │   └── MainPage.jsx         # Main dashboard (hero + input + plan)
        ├── components/
        │   ├── EquipmentPicker.jsx  # 9 chips + 11-group machine sub-panel + custom input
        │   ├── SidebarMemory.jsx    # Identity / Pinned plan / Activity / History
        │   ├── GoalCardB.jsx        # Structured 2-col reasoning card with pin button
        │   ├── PlanCard.jsx         # Day card (renders inside responsive grid)
        │   ├── IrProcessPanel.jsx   # IR transparency panel (Stage-1 reasoning + retrieval trace)
        │   └── PixelButton.jsx      # Styled pixel-art button
        └── styles/pixel.css         # Cream + Peach + Sage + Wood palette
```

## IR Pipeline — Two-Stage Agent

| Stage | Method | Detail |
|---|---|---|
| 0. Safety gate | Keyword scan + LLM check | Detects medical concerns and short-circuits with a fixed message |
| 1. Plan Reasoning | GPT-4o (no tools) | Emits a structured JSON blueprint: `interpreted_goal`, `target_muscles`, `training_split`, `intensity`, `sets_reps_scheme`, `daily_cardio` |
| 2. Tool-Calling Execution | GPT-4o (5 tools) | Retrieves exercises per muscle, training rules, user memory, web fallbacks; appends cardio verbatim |
| 3. Post-validation | chrF++ | Strips exercise names not within character-n-gram fuzzy match of retrieved set (cardio exempted) |

**Tools available in Stage 2:**
- `search_exercises(muscle, goal)` — per-muscle ChromaDB semantic query
- `web_search_exercises(query)` — DuckDuckGo fallback for niche equipment (TRX, sandbag, …)
- `search_training_rules(goal)` — ChromaDB over rule embeddings
- `get_user_memory()` — SQLite lookup (incl. nickname + training_level)
- `web_search_nutrition(query)` — DuckDuckGo for nutrition guidance

## Data Sources

- **wger REST API** — ~847 exercises (bodyweight, dumbbell, barbell, kettlebell, bench, pull-up bar, resistance band)
- **Free Exercise DB** — ~800 exercises (adds cable + machine coverage)
- Both normalized to a shared canonical equipment taxonomy at index time
- wger entries that wrongly land as `bodyweight` despite being cable/machine moves are re-tagged via a name-based override during indexing

## UI Highlights

- **Onboarding** captures nickname + training level on first visit (stored in `user_memory`); training level feeds back into Stage-1 reasoning to calibrate exercise difficulty.
- **Sidebar** has four sections: Identity (avatar slot + editable nickname/level), Pinned Plan, Activity (aggregated stats: total plans, top muscles, top equipment), History.
- **Pinned plan** — click ★ on any plan; sidebar shows a compact preview, and the plan auto-loads on the next visit for zero-click access.
- **Goal Card (Stage-1 view)** renders the reasoning blueprint as a 2-column dashboard (Split / Intensity / Scheme / Cardio + per-field reasoning) so the agent's logic is inspectable.
- **IR PROCESS TRACE** panel exposes Stage-1 JSON, retrieved exercises, post-filter set, rules used, web queries, and memory loaded.
- **Equipment Picker** — 9 standard chips, 11-group machine sub-panel with 35+ named machines, a CARDIO group (treadmill / elliptical / bike / rower / etc.), and a free-text input for custom equipment.
- **Hero block** — pixel-art workshop banner sets the visual tone (Cream + Peach + Sage + Wood palette throughout).

## Safety

If the user mentions injury, pain, illness, pregnancy, or any medical condition, Gym Smith short-circuits before any plan is generated and recommends consulting a professional. No medical advice, rehabilitation plans, or calorie counting.
