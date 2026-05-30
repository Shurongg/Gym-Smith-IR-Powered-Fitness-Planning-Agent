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
3. Fetch ~847 exercises from the wger API and index them in ChromaDB (~5 minutes)
4. Index training/nutrition rules

Subsequent startups are instant (idempotent).

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — enter your OpenAI API key to begin.

## Project Structure

```
gym-smith/
├── backend/
│   ├── main.py                    # FastAPI app
│   ├── pipeline/                  # 6-step IR pipeline
│   │   ├── intent_parser.py       # Step 1: parse user intent
│   │   ├── exercise_retriever.py  # Step 2: semantic exercise search
│   │   ├── equipment_filter.py    # Step 3: filter by equipment
│   │   ├── rule_retriever.py      # Step 4: retrieve training rules
│   │   ├── memory_retriever.py    # Step 5: user memory lookup
│   │   └── context_assembler.py   # Step 6: assemble prompt
│   ├── data/
│   │   ├── rules.json             # Training & nutrition rules
│   │   └── wger_client.py         # wger API client
│   ├── db/
│   │   ├── chroma_store.py        # ChromaDB wrapper
│   │   └── sqlite_store.py        # SQLite wrapper
│   └── init_knowledge_base.py     # KB initialization
└── frontend/
    └── src/
        ├── pages/
        │   ├── ApiKeyPage.jsx
        │   └── MainPage.jsx
        └── components/
            ├── PlanCard.jsx
            ├── IrProcessPanel.jsx
            └── SidebarMemory.jsx
```

## IR Methods Used

| Method | Where |
|--------|-------|
| Semantic vector search | Exercise retrieval (ChromaDB + SentenceTransformer) |
| Semantic vector search | Rule retrieval (ChromaDB + SentenceTransformer) |
| Metadata filtering | Equipment-aware exercise filtering |
| Structured memory retrieval | User preferences from SQLite |
| LLM-based intent parsing | Structured extraction from natural language |

## Safety

If you mention injury, pain, illness, pregnancy, or any medical condition, Gym Smith will stop and recommend consulting a professional. It does not provide medical advice, rehabilitation plans, or calorie counting.
