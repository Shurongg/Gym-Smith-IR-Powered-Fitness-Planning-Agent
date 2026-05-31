# Gym Smith — IR Agent Design Spec
**Date:** 2026-05-30  
**Project:** Information Retrieval Assignment 2  
**Status:** Approved

---

## Overview

Gym Smith is a retrieval-augmented fitness planning agent. Users describe their training goals, frequency, available equipment, and intensity preferences in natural language. The agent retrieves relevant exercises, training principles, and nutrition rules from a knowledge base, then generates a structured weekly training plan. User preferences and plan history are persisted for future sessions.

**Scope:** General workout plans for healthy adults. Does not provide medical advice, rehabilitation programs, calorie counting, supplement recommendations, or guaranteed results.

---

## Architecture

### Stack
- **Frontend:** React (pixel art UI style)
- **Backend:** Python + FastAPI
- **Vector Store:** ChromaDB (exercise + rule embeddings)
- **Relational Store:** SQLite (user memory + plan history)
- **LLM:** OpenAI API (GPT-4o), key provided by user at runtime
- **Embedding Model:** OpenAI `text-embedding-3-small` (used for both exercise and rule embeddings)
- **Exercise Knowledge Base:** wger REST API (`https://wger.de/api/v2/`)
- **Rules Knowledge Base:** `backend/data/rules.json` (hand-authored)

### High-Level Flow
```
React Frontend
     │ REST API
FastAPI Backend
     │
     ├── IR Pipeline
     │     ├── 1. Intent Parser       (GPT-4o, lightweight call)
     │     ├── 2. Exercise Retriever  (ChromaDB semantic search)
     │     ├── 3. Equipment Filter    (metadata filter on wger equipment field)
     │     ├── 4. Rule Retriever      (ChromaDB semantic search)
     │     ├── 5. Memory Retriever    (SQLite query)
     │     └── 6. Context Assembler   (builds final prompt)
     │
     └── OpenAI API (GPT-4o, plan generation call)

Storage:
  ChromaDB  — exercise embeddings, rule embeddings
  SQLite    — users, user_memory, plan_history
```

### Startup Sequence
1. `init_knowledge_base.py` runs on first launch:
   - Fetches all English exercises from wger `/api/v2/exerciseinfo/?language=2` (~847 exercises)
   - Embeds each as `"{name} - {category} - muscles: {muscles} - {description}"` → ChromaDB `exercises` collection
   - Loads `rules.json`, embeds each rule as `"{title}: {content}"` → ChromaDB `rules` collection
2. FastAPI server starts (`uvicorn backend.main:app --reload`)
3. React dev server starts (`npm run dev`)

---

## IR Pipeline — Detailed

### Step 1: Intent Parser
A lightweight GPT-4o call converts free-form user input into structured parameters:
```json
{
  "target_muscles": ["biceps", "triceps"],
  "equipment": ["dumbbell", "resistance band"],
  "frequency": 3,
  "intensity": "medium",
  "goal": "hypertrophy",
  "flags": []
}
```
**Safety gate:** If the parser detects medical concern keywords (injury, pain, pregnant, illness, eating disorder, surgery, etc.), it sets `flags: ["medical_concern"]`. The pipeline terminates immediately and returns a fixed safety message recommending professional consultation. No training plan is generated.

### Step 2: Exercise Retriever
Constructs a semantic query from parsed intent (e.g., `"biceps hypertrophy dumbbell exercises"`) and retrieves Top 20 semantically similar exercises from ChromaDB `exercises` collection.

### Step 3: Equipment Filter
Filters Step 2 results to only include exercises whose `equipment` metadata matches the user's available equipment. Target: 8–12 exercises retained. Bodyweight exercises (`equipment: none`) are always included as alternatives.

### Step 4: Rule Retriever
Constructs a semantic query from the training goal (e.g., `"hypertrophy training principles rest time sets reps"`) and retrieves:
- Top 5 training/recovery rules from ChromaDB `rules` collection
- Top 3 nutrition rules from ChromaDB `rules` collection

### Step 5: Memory Retriever
Queries SQLite `user_memory` table for the current user's stored preferences: previous goal, equipment list, intensity preference, and most recent plan summary. Returns empty context for new users.

### Step 6: Context Assembler
Combines all retrieved context into a structured prompt:
- User's original message
- Parsed intent parameters
- Retrieved exercises (name, muscles, equipment, description)
- Retrieved training + nutrition rules
- User memory (if any)
- Output format instructions (structured JSON plan)
- Explicit out-of-scope constraints (no calorie counting, no supplements, no medical advice)

The assembled prompt is sent to GPT-4o for plan generation. The response is a structured JSON object rendered directly by the frontend.

---

## Data Models

### ChromaDB Collections

**`exercises`**
```
document:  "{name} - {category} - muscles: {muscles} - {description}"
metadata:  {
  exercise_id: int,
  name: str,
  category: str,           // "Arms", "Chest", "Back", "Legs", "Abs", "Shoulders", "Calves", "Cardio"
  muscles: list[str],      // primary muscles (English names)
  muscles_secondary: list[str],
  equipment: list[str],    // "Dumbbell", "Barbell", "None", etc.
  description: str
}
```

**`rules`**
```
document:  "{title}: {content}"
metadata:  {
  rule_id: str,
  type: str,               // "training_principle" | "recovery_rule" | "nutrition_rule"
  title: str,
  content: str,
  tags: list[str]          // e.g. ["hypertrophy", "strength", "beginner"]
}
```

### SQLite Tables

**`users`**
```sql
id            INTEGER PRIMARY KEY
session_token TEXT UNIQUE   -- UUID generated server-side on first visit, stored in browser localStorage
created_at    DATETIME
```

**`user_memory`**
```sql
id                   INTEGER PRIMARY KEY
user_id              INTEGER REFERENCES users(id)
equipment            TEXT    -- JSON array
intensity_preference TEXT
last_goal            TEXT
updated_at           DATETIME
```

**`plan_history`**
```sql
id          INTEGER PRIMARY KEY
user_id     INTEGER REFERENCES users(id)
user_input  TEXT
plan_json   TEXT    -- full generated plan as JSON string
created_at  DATETIME
```

### rules.json Structure
```json
{
  "training_principles": [
    {
      "id": "tp1",
      "title": "Progressive Overload",
      "content": "Gradually increase weight, reps, or sets over time to continue making progress.",
      "tags": ["hypertrophy", "strength", "general"]
    }
  ],
  "recovery_rules": [...],
  "nutrition_rules": [...]
}
```
Target: ~10 training principles, ~8 recovery rules, ~10 nutrition rules (≈28 total).

---

## UI Design

### Visual Style
- **Theme:** Pixel art, fresh & healthy
- **Fonts:** `Press Start 2P` (headings/labels) + `VT323` (body text)
- **Color Palette:**
  ```
  Background:    #F5F0E8  (cream white)
  Primary:       #7BC67E  (mint green — buttons, highlights)
  Secondary:     #A8D8A8  (light green — card borders, tags)
  Text:          #2D2D2D  (dark charcoal)
  Warning:       #FF8A65  (warm coral — safety messages)
  Card bg:       #FFFDF5  (off-white)
  Border:        2px solid #2D2D2D
  Pixel shadow:  4px 4px 0px #2D2D2D
  ```
- **Decorative icons:** Pixel art fitness equipment icons (from Kenney.nl free asset pack)

### Page 1 — API Key Entry
- Centered layout, pixel art logo "GYM SMITH"
- Single text input for OpenAI API key
- `CONNECT` button (mint green, pixel shadow)
- Connection status indicator (green dot = connected, coral X = invalid)

### Page 2 — Main Interface
Two-column layout:
- **Left sidebar:** User stats (equipment, intensity, goal from memory) + plan history list + `NEW PLAN` button
- **Main area:**
  - Multi-line pixel-bordered input textarea
  - `GENERATE PLAN` button
  - Plan output cards (one card per training day, collapsible)
  - `IR PROCESS` collapsible panel (shows retrieved exercises, rules used, memory loaded — key for assignment demo)

### IR Process Panel (assignment demo feature)
Displays the full retrieval trace:
- Parsed intent JSON
- Top exercises retrieved + which were filtered out by equipment
- Training rules retrieved
- Nutrition rules retrieved
- Memory loaded (or "No previous session found")

---

## Error Handling

| Scenario | Behaviour |
|----------|-----------|
| Invalid OpenAI API key | Page 1 shows coral error, blocks navigation to main page |
| Medical concern detected | Pipeline stops, returns safety message, no plan generated |
| wger API timeout | Use cached ChromaDB data (no live dependency after init) |
| ChromaDB not initialized | `init_knowledge_base.py` auto-triggered on startup |
| Out-of-scope request (calories, supplements, body fat %) | GPT-4o system prompt explicitly rejects these, returns scoped response |
| New user (no memory) | Memory retrieval returns empty, plan generated without prior context |

---

## Out of Scope

- Medical advice, injury rehabilitation
- Calorie counting or precise macro calculations
- Supplement recommendations
- Body fat percentage prediction
- Guaranteed results ("you will have abs in 2 months")
- Image-based exercise recognition
- Real-time posture correction
- Full personal trainer system

---

## Project Structure

```
gym-smith/
├── backend/
│   ├── main.py
│   ├── pipeline/
│   │   ├── intent_parser.py
│   │   ├── exercise_retriever.py
│   │   ├── rule_retriever.py
│   │   ├── memory_retriever.py
│   │   └── context_assembler.py
│   ├── data/
│   │   └── rules.json
│   ├── db/
│   │   ├── chroma_store.py
│   │   └── sqlite_store.py
│   ├── init_knowledge_base.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── ApiKeyPage.jsx
│   │   │   └── MainPage.jsx
│   │   ├── components/
│   │   │   ├── PlanCard.jsx
│   │   │   ├── IrProcessPanel.jsx
│   │   │   ├── SidebarMemory.jsx
│   │   │   └── PixelButton.jsx
│   │   ├── styles/
│   │   │   └── pixel.css
│   │   └── App.jsx
│   └── package.json
├── .env.example
└── README.md
```

---

## Deliverables Checklist (Assignment Requirements)

- [ ] Runnable code on GitHub with API key in OpenAI format
- [ ] Working memory system (SQLite user_memory)
- [ ] IR methods demonstrated (ChromaDB vector search, wger API retrieval, equipment filter)
- [ ] Extendable with additional IR tools and actions
- [ ] IR process visible in UI (IR Process Panel)
- [ ] README with setup instructions
- [ ] Demo video of working system
