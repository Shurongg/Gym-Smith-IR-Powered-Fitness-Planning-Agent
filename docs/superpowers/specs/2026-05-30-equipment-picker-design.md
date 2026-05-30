# Equipment Picker & Data Expansion — Design Spec
**Date:** 2026-05-30
**Status:** Approved

---

## Problem

When users do not mention equipment in their request, the Intent Parser guesses (often "cable" for arm exercises). Because wger has no cable equipment type, the Equipment Filter passes almost nothing to GPT-4o, which then fills the gap from its own training knowledge — bypassing IR retrieval entirely. Additionally, two bugs compound the issue:

1. wger stores bodyweight exercises as both `"None"` and `"none (bodyweight exercise)"`, but the filter only matches `"none"`, silently dropping 231 bodyweight exercises.
2. The filter matches the entire equipment string, so exercises with multiple equipment values (e.g. `"Barbell, Dumbbell"`) are incorrectly excluded.

---

## Solution Overview

Three coordinated changes:

1. **Data expansion** — add Free Exercise DB (cable, machine, bands) alongside wger in ChromaDB
2. **Pipeline fixes** — fix Intent Parser, Equipment Filter, and add equipment override to API
3. **UI Equipment Picker** — explicit equipment selector below the textarea, with Machine sub-panel and memory persistence

---

## Part 1: Data Layer

### Source
**Free Exercise DB** — static JSON, no API key required.
URL: `https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/dist/exercises.json`
~800 exercises. Downloaded once at startup in `init_knowledge_base.py`.

### ChromaDB Storage
Both wger and Free Exercise DB exercises go into the same `exercises` collection.
- wger IDs: existing integer strings (e.g. `"123"`)
- Free Exercise DB IDs: prefixed `"fex_0001"`

### Canonical Equipment Normalization
All equipment values are normalized at index time to a canonical lowercase set. The `equipment` metadata field stores a single canonical value per exercise.

| Canonical | wger source values | Free Exercise DB source values |
|-----------|-------------------|-------------------------------|
| `bodyweight` | `None`, `none (bodyweight exercise)`, `Gym mat` | `body only` |
| `dumbbell` | `Dumbbell` | `dumbbell` |
| `barbell` | `Barbell`, `SZ-Bar` | `barbell`, `e-z curl bar` |
| `cable` | — | `cable` |
| `machine` | — | `machine` |
| `bench` | `Bench`, `Incline bench` | — |
| `pull-up bar` | `Pull-up bar` | — |
| `kettlebell` | `Kettlebell` | `kettlebell` |
| `resistance band` | `Resistance band` | `bands` |

Values not in this table (e.g. `Swiss Ball`, `medicine ball`, `foam roll`, `other`) are skipped — exercises with only unmapped equipment are not indexed.

### Re-indexing Required
Because wger exercises already in ChromaDB use the old unnormalized strings, `backend/data/chroma/` must be deleted before running `init_knowledge_base.py` with the new code.

---

## Part 2: Pipeline Fixes

### 2a. Intent Parser (`pipeline/intent_parser.py`)
Add to system prompt:
> `equipment: only extract equipment the user explicitly mentions. If the user does not mention any equipment, return []. Do not guess.`

Normalize list updated to canonical names: `bodyweight, dumbbell, barbell, cable, machine, bench, pull-up bar, kettlebell, resistance band`.

### 2b. Equipment Filter (`pipeline/equipment_filter.py`)
Three fixes:

```python
def filter_by_equipment(exercises, user_equipment):
    if not user_equipment:
        return exercises  # no filter when equipment unknown
    allowed = {e.lower() for e in user_equipment} | {"bodyweight"}
    result = []
    for ex in exercises:
        eq_str = ex.get("equipment", "bodyweight")
        ex_equip = {e.strip().lower() for e in eq_str.split(",")}
        if ex_equip & allowed:
            result.append(ex)
    return result
```

- Empty equipment → return all (no restriction)
- Split comma-separated equipment strings and check any-match
- `bodyweight` always in allowed set

### 2c. API Request Model (`main.py`)
`PlanRequest` gains two optional fields:

```python
class PlanRequest(BaseModel):
    session_token: str
    api_key: str
    user_input: str
    equipment_override: list[str] = []      # canonical types for ChromaDB filter
    specific_machines: list[str] = []       # machine names for GPT context
```

Logic in `generate_plan`:
- If `equipment_override` is non-empty → replace `intent["equipment"]` with it
- `specific_machines` is appended to the assembled context prompt

### 2d. Context Assembler (`pipeline/context_assembler.py`)
Accepts new `specific_machines: list[str]` parameter. If non-empty, appends to prompt:
```
USER'S SPECIFIC MACHINES: Leg press, Lat pulldown, Seated row
Prioritize exercises using these machines when generating the plan.
```

### 2e. Memory Store (`db/sqlite_store.py`)
`user_memory` table gains one column:
```sql
ALTER TABLE user_memory ADD COLUMN specific_machines TEXT;
```
`upsert_user_memory` and `get_user_memory` updated to handle this field.

---

## Part 3: Equipment Picker UI

### Component: `EquipmentPicker.jsx`

Placed in `frontend/src/components/EquipmentPicker.jsx`.
Rendered inside `MainPage.jsx` between the textarea and the GENERATE PLAN button.

### Top-Level Chips

Nine chips in a flex-wrap row:

| Chip label | `equipment_override` value |
|------------|--------------------------|
| Bodyweight | `bodyweight` |
| Dumbbell | `dumbbell` |
| Barbell | `barbell` |
| Cable | `cable` |
| Machine ▾ | `machine` (+ opens sub-panel) |
| Bench | `bench` |
| Pull-up bar | `pull-up bar` |
| Kettlebell | `kettlebell` |
| Resistance band | `resistance band` |

**Chip styles:**
- Unselected: off-white bg, 1px dashed border, muted text, VT323 font 16px
- Selected: `var(--primary)` mint green bg, `var(--border)` solid border, pixel shadow `2px 2px 0px #2D2D2D`, dark text

**CLEAR button:**
- Appears at top-right of the picker only when at least one item is selected
- Ghost style, small (`0.45rem` Press Start 2P font)
- Clears all top-level chips and all Machine sub-selections in one click

### Machine Sub-Panel

Expands below the chip row when Machine chip is selected. Contains:

**Search box** — pixel-bordered input, placeholder `search machines...`, filters chips in real time (case-insensitive substring match on machine name). Groups with no matching machines are hidden.

**Machine list grouped by body part:**

| Group | Machines |
|-------|---------|
| CHEST & PUSH | Chest press, Pec deck, Smith machine |
| BACK & PULL | Lat pulldown, Seated row, Assisted pull-up |
| LEGS | Leg press, Leg curl, Leg extension, Hip abductor, Hip adductor, Calf raise |
| SHOULDERS | Shoulder press, Rear delt machine |
| ARMS | Preacher curl, Tricep machine, Assisted dip |
| CORE | Ab crunch machine, Back extension |

Each machine is a small chip (same style as top-level chips, smaller text). Multiple selection allowed.

Machine chip count displayed on top-level Machine chip: `Machine ×3`.

Panel closes if Machine chip is deselected (sub-selections are cleared).

### Props

```jsx
<EquipmentPicker
  selected={selectedEquipment}          // string[] of canonical types
  specificMachines={specificMachines}   // string[] of machine names
  onChange={(eq, machines) => ...}      // called on any change
/>
```

---

## Part 4: Memory Integration

### SQLite Changes
`user_memory` table: new `specific_machines TEXT` column (JSON array, nullable).

### Save (after plan generation)
`upsert_user_memory` receives `equipment_override` and `specific_machines` from the request. Both saved to `user_memory`.

### Load (on session fetch)
`get_user_memory` returns `specific_machines` alongside `equipment`. Frontend pre-populates `EquipmentPicker` from these values on mount via `useEffect` watching `sessionData`.

### NEW PLAN behaviour
Clicking `+ NEW PLAN` clears input and result but **keeps** equipment selection (user likely still in same gym environment).

### CLEAR button behaviour
Resets all equipment selections (both canonical types and specific machines) to empty. Next plan generation will not send any `equipment_override`.

---

## File Changes Summary

| File | Change |
|------|--------|
| `backend/data/freeexdb_client.py` | New — fetch and parse Free Exercise DB JSON |
| `backend/init_knowledge_base.py` | Add Free Exercise DB indexing, equipment normalization for both sources |
| `backend/pipeline/intent_parser.py` | Prompt update: don't guess equipment |
| `backend/pipeline/equipment_filter.py` | Fix empty/multi-value/bodyweight handling |
| `backend/pipeline/context_assembler.py` | Accept + render `specific_machines` |
| `backend/db/sqlite_store.py` | Add `specific_machines` column, update upsert/get |
| `backend/main.py` | `PlanRequest` new fields, pass to pipeline |
| `frontend/src/components/EquipmentPicker.jsx` | New component |
| `frontend/src/pages/MainPage.jsx` | Add picker state, pre-populate from memory, pass to API |
| `frontend/src/api.js` | Update `generatePlan` to send `equipment_override` + `specific_machines` |

---

## Out of Scope

- Per-exercise sub-categories for non-machine equipment (Cable, Barbell, etc.)
- User-defined custom equipment
- Equipment availability saved per-location (home vs gym)
