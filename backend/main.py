import re
import warnings

# duckduckgo_search emits a rename warning via warnings.warn() AFTER calling
# warnings.simplefilter("always") (see duckduckgo_search/duckduckgo_search.py:53),
# which wipes any ignore filter we set.  The only reliable mute is to wrap
# warnings.warn itself and swallow that specific message.
_orig_warn = warnings.warn
def _filtered_warn(message, *args, **kwargs):
    if isinstance(message, str) and "duckduckgo_search" in message:
        return
    return _orig_warn(message, *args, **kwargs)
warnings.warn = _filtered_warn

from contextlib import asynccontextmanager
from collections import Counter
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import json


def _chrf(hyp: str, ref: str, max_n: int = 6, beta: float = 2.0) -> float:
    hyp = hyp.lower().replace(" ", "")
    ref = ref.lower().replace(" ", "")
    prec_total, rec_total = 0.0, 0.0
    for n in range(1, max_n + 1):
        h = Counter(hyp[i:i+n] for i in range(max(0, len(hyp)-n+1)))
        r = Counter(ref[i:i+n] for i in range(max(0, len(ref)-n+1)))
        match = sum((h & r).values())
        prec_total += match / sum(h.values()) if h else 0
        rec_total += match / sum(r.values()) if r else 0
    p, r = prec_total / max_n, rec_total / max_n
    if p + r == 0:
        return 0.0
    return (1 + beta**2) * p * r / (beta**2 * p + r)


def _exercise_in_retrieved(gpt_name: str, retrieved_names: set[str], threshold: float = 0.6) -> bool:
    return any(_chrf(gpt_name, name) >= threshold for name in retrieved_names)


_EXERCISE_ACTION = re.compile(
    r'\b(curl|press|row|pull|push|raise|fly(?:e)?|extension|squat|lunge|deadlift|'
    r'pulldown|crunch|dip|shrug|kickback|crossover|thrust|swing|clean|snatch|pullover)\b',
    re.IGNORECASE,
)


def _extract_exercise_names(text: str) -> set[str]:
    """Heuristic: find N-grams around exercise action words in web search snippets."""
    names: set[str] = set()
    words = text.split()
    for i, word in enumerate(words):
        if _EXERCISE_ACTION.match(word.rstrip("s.,;:\"'()")):
            start = max(0, i - 3)
            phrase = " ".join(words[start:i + 1]).strip(".,;:\"'()")
            if len(phrase.split()) >= 2:
                names.add(phrase.title())
    return names


from db.sqlite_store import (
    init_db, create_user, get_user_id, get_user_memory,
    get_plan_history, upsert_user_memory, save_plan, delete_plan,
    set_identity, set_pinned_plan, get_plan_by_id,
)
from init_knowledge_base import init_knowledge_base
from pipeline.intent_parser import check_medical
from pipeline.exercise_retriever import retrieve_exercises
from pipeline.equipment_filter import filter_by_equipment
from pipeline.rule_retriever import retrieve_rules
from pipeline.memory_retriever import retrieve_memory
from pipeline.context_assembler import SYSTEM_PROMPT, STAGE1_REASONING_PROMPT
from pipeline.web_search import web_search
from db.chroma_store import query_collection


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_exercises",
            "description": (
                "Search the exercise knowledge base for exercises targeting a specific muscle group. "
                "Returns a broad set of relevance-ranked candidates — equipment metadata is unreliable, "
                "so some results may use equipment the user does NOT have. "
                "You MUST inspect each returned exercise and reject ones whose equipment does not "
                "match the user's selection. "
                "Call this separately for each target muscle group."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "muscle_group": {
                        "type": "string",
                        "description": "Target muscle group, e.g. 'biceps', 'chest', 'quadriceps'",
                    },
                    "goal": {
                        "type": "string",
                        "description": "Training goal, e.g. 'hypertrophy', 'strength', 'fat loss'",
                    },
                },
                "required": ["muscle_group", "goal"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search_exercises",
            "description": (
                "Search the web for exercises when search_exercises returns empty or insufficient "
                "results for the user's specific equipment. Use ONLY as a fallback when the "
                "knowledge base lacks exercises for the requested equipment type."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query, e.g. 'cable biceps hypertrophy exercises'",
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_training_rules",
            "description": "Search the training rules knowledge base for guidelines relevant to a training goal.",
            "parameters": {
                "type": "object",
                "properties": {
                    "goal": {
                        "type": "string",
                        "description": "Training goal to retrieve rules for",
                    }
                },
                "required": ["goal"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_memory",
            "description": "Retrieve the user's previous session data: past equipment, intensity preference, and last training goal.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search_nutrition",
            "description": "Search the web for nutrition information relevant to the user's fitness goal (e.g., protein intake, meal timing, hydration).",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Nutrition search query",
                    }
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
]


def _run_stage1_reasoning(
    client: OpenAI,
    user_input: str,
    user_equipment: list[str],
    specific_machines: list[str],
    user_memory: dict | None,
) -> dict:
    """Stage 1: the agent reasons about the user's goal and designs the training
    framework (split, intensity, sets/reps, exercise count per day).  No tools
    are exposed in this stage — the model is forced to think before acting."""
    context_lines = [f"USER REQUEST: {user_input}"]
    if user_equipment:
        context_lines.append(f"USER'S AVAILABLE EQUIPMENT: {', '.join(user_equipment)}")
    if specific_machines:
        context_lines.append(
            f"USER'S SPECIFIC MACHINES (the only machines they own): "
            f"{', '.join(specific_machines)}"
        )
    if user_memory:
        if user_memory.get("training_level"):
            context_lines.append(
                f"USER'S TRAINING LEVEL: {user_memory['training_level']} "
                f"(self-reported during onboarding — calibrate exercise difficulty accordingly)"
            )
        if user_memory.get("nickname"):
            context_lines.append(f"USER'S NICKNAME: {user_memory['nickname']}")
        context_lines.append(
            f"USER MEMORY (previous session): "
            f"goal={user_memory.get('last_goal') or 'n/a'}, "
            f"intensity={user_memory.get('intensity_preference') or 'n/a'}"
        )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": STAGE1_REASONING_PROMPT},
            {"role": "user", "content": "\n".join(context_lines)},
        ],
        temperature=0.4,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


def _run_agent_loop(
    client: OpenAI,
    user_input: str,
    plan_reasoning: dict,
    user_id: int,
    user_equipment: list[str],
    specific_machines: list[str],
) -> tuple[dict, dict]:
    all_exercises: list[dict] = []
    all_rules: list[dict] = []
    web_searches_done: list[str] = []
    web_exercise_searches: list[str] = []
    memory_loaded: dict | None = None
    seen_exercise_names: set[str] = set()
    web_exercise_names: set[str] = set()
    seen_rule_titles: set[str] = set()

    def execute_tool(name: str, args: dict) -> str:
        nonlocal memory_loaded
        if name == "search_exercises":
            muscle = args.get("muscle_group", "")
            goal = args.get("goal", "")

            raw = retrieve_exercises([muscle], goal, equipment_hint=user_equipment or None)
            filtered = filter_by_equipment(raw, user_equipment)

            machine_seen = {ex["name"] for ex in filtered}
            for machine in (specific_machines or []):
                machine_results = query_collection(
                    "exercises", f"{machine} exercises", n_results=10
                )
                for meta in machine_results["metadatas"][0]:
                    mname = meta.get("name", "")
                    if mname and mname not in machine_seen and mname not in seen_exercise_names:
                        machine_seen.add(mname)
                        filtered.append({
                            "name": mname,
                            "category": meta.get("category", ""),
                            "muscles": meta.get("muscles", ""),
                            "muscles_secondary": meta.get("muscles_secondary", ""),
                            "equipment": meta.get("equipment", "None"),
                            "description": meta.get("description", "")[:200],
                        })

            for ex in filtered:
                if ex["name"] not in seen_exercise_names:
                    seen_exercise_names.add(ex["name"])
                    all_exercises.append(ex)
            return json.dumps([
                {
                    "name": ex["name"],
                    "category": ex["category"],
                    "muscles": ex["muscles"],
                    "equipment": ex["equipment"],
                    "description": ex["description"][:200],
                }
                for ex in filtered
            ])
        if name == "web_search_exercises":
            query = args.get("query", "")
            web_exercise_searches.append(query)
            result_text = web_search(query)
            extracted = _extract_exercise_names(result_text)
            web_exercise_names.update(extracted)
            return result_text
        if name == "search_training_rules":
            goal = args.get("goal", "")
            rules = retrieve_rules(goal)
            for r in rules:
                if r["title"] not in seen_rule_titles:
                    seen_rule_titles.add(r["title"])
                    all_rules.append(r)
            return json.dumps([
                {"title": r["title"], "content": r["content"], "type": r.get("type", "")}
                for r in rules
            ])
        if name == "get_user_memory":
            memory_loaded = retrieve_memory(user_id)
            return json.dumps(memory_loaded or {})
        if name == "web_search_nutrition":
            query = args.get("query", "")
            web_searches_done.append(query)
            return web_search(query)
        return json.dumps({"error": f"Unknown tool: {name}"})

    initial_msg = (
        f"USER REQUEST: {user_input}\n\n"
        f"PLAN_REASONING (from Stage 1 — this is the structure you MUST build):\n"
        f"{json.dumps(plan_reasoning, indent=2)}\n\n"
    )
    if user_equipment:
        initial_msg += (
            f"USER'S AVAILABLE EQUIPMENT: {', '.join(user_equipment)}\n"
            "CRITICAL: search_exercises returns a broad pool of candidates. Many results "
            "will be for equipment the user does NOT have. After each search_exercises call, "
            "you MUST manually filter the returned list and REJECT any exercise whose "
            "equipment is not in the user's list above. Do NOT include rejected exercises "
            "in the final plan.\n"
        )
    if specific_machines:
        initial_msg += (
            f"USER'S SPECIFIC MACHINES (the ONLY machines they have): "
            f"{', '.join(specific_machines)}\n"
            "If 'machine' is in the general equipment list, this overrides it: the user does NOT "
            "have generic machine access — only the specific machines listed above. REJECT every "
            f"retrieved exercise that requires a machine not in this list. An exercise is "
            f"acceptable for a specific machine ONLY if its name or description plausibly fits "
            f"one of: {', '.join(specific_machines)}.\n"
        )
    initial_msg += (
        "\nEXECUTION ORDER:\n"
        "1. Call search_exercises ONCE PER MUSCLE in PLAN_REASONING.target_muscles.\n"
        "2. Call search_training_rules with the goal implied by PLAN_REASONING.interpreted_goal.\n"
        "3. Call get_user_memory to fetch previous preferences.\n"
        "4. Build weekly_schedule using PLAN_REASONING.training_split as the blueprint — "
        "the number of exercises per day MUST equal exercises_count for that day.\n"
        "5. Apply PLAN_REASONING.sets_reps_scheme to every exercise.\n"
        "6. If filtering leaves a muscle short, call web_search_exercises with a query "
        "that includes the specific equipment / machine name.\n\n"
        "Produce the final plan as JSON when done."
    )

    messages: list = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": initial_msg},
    ]

    plan: dict = {}
    for _ in range(10):
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        msg = response.choices[0].message

        assistant_entry: dict = {"role": "assistant", "content": msg.content}
        if msg.tool_calls:
            assistant_entry["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in msg.tool_calls
            ]
        messages.append(assistant_entry)

        if response.choices[0].finish_reason == "stop":
            plan = json.loads(msg.content)
            break

        for tc in (msg.tool_calls or []):
            tool_result = execute_tool(tc.function.name, json.loads(tc.function.arguments))
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": tool_result})
    else:
        raise HTTPException(status_code=500, detail="Agent did not converge")

    # chrF++ validator: allow exercises from KB or web search, strip pure hallucinations.
    # Cardio entries (muscles == ["cardiovascular"]) come from Stage 1's daily_cardio
    # protocol verbatim, not from any retrieval — exempt them from the chrF++ check.
    all_known_names = seen_exercise_names | web_exercise_names

    def _is_cardio_entry(e: dict) -> bool:
        muscles = e.get("muscles") or []
        return any(str(m).lower() == "cardiovascular" for m in muscles)

    for day in plan.get("weekly_schedule", []):
        day["exercises"] = [
            e for e in day.get("exercises", [])
            if _is_cardio_entry(e)
            or not all_known_names
            or _exercise_in_retrieved(e["name"], all_known_names)
        ]

    # Override equipment_needed with what the user actually selected
    if user_equipment:
        plan["equipment_needed"] = user_equipment + (specific_machines or [])

    ir_process = {
        "plan_reasoning": plan_reasoning,
        "exercises_retrieved": [e["name"] for e in all_exercises[:10]],
        "exercises_after_filter": list(seen_exercise_names),
        "web_exercise_searches": web_exercise_searches,
        "training_rules_used": [r["title"] for r in all_rules if r.get("type") != "nutrition_rule"],
        "nutrition_rules_used": [r["title"] for r in all_rules if r.get("type") == "nutrition_rule"],
        "web_searches": web_searches_done,
        "memory_loaded": memory_loaded,
    }

    return plan, ir_process


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    await init_knowledge_base()
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
    equipment_override: list[str] = []
    specific_machines: list[str] = []


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


@app.delete("/api/plan/{plan_id}")
def delete_plan_route(plan_id: int, session_token: str):
    user_id = get_user_id(session_token)
    if user_id is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if not delete_plan(user_id, plan_id):
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"ok": True}


class IdentityRequest(BaseModel):
    session_token: str
    nickname: str
    training_level: str  # "beginner" | "intermediate" | "advanced"


@app.post("/api/identity")
def set_identity_route(body: IdentityRequest):
    user_id = get_user_id(body.session_token)
    if user_id is None:
        raise HTTPException(status_code=404, detail="Session not found")
    nick = body.nickname.strip()
    if not nick:
        raise HTTPException(status_code=400, detail="nickname required")
    if body.training_level not in ("beginner", "intermediate", "advanced"):
        raise HTTPException(status_code=400, detail="invalid training_level")
    set_identity(user_id, nick, body.training_level)
    return {"ok": True}


@app.post("/api/pin/{plan_id}")
def pin_plan_route(plan_id: int, session_token: str):
    user_id = get_user_id(session_token)
    if user_id is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if not set_pinned_plan(user_id, plan_id):
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"ok": True, "pinned_plan_id": plan_id}


@app.delete("/api/pin")
def unpin_route(session_token: str):
    user_id = get_user_id(session_token)
    if user_id is None:
        raise HTTPException(status_code=404, detail="Session not found")
    set_pinned_plan(user_id, None)
    return {"ok": True, "pinned_plan_id": None}


@app.get("/api/plan/{plan_id}")
def get_plan_route(plan_id: int, session_token: str):
    """Fetch a single plan (used by pinning to load full plan into main area)."""
    user_id = get_user_id(session_token)
    if user_id is None:
        raise HTTPException(status_code=404, detail="Session not found")
    plan = get_plan_by_id(user_id, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


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

    # Safety gate (deterministic + LLM keyword/paraphrase check)
    safety = check_medical(client, body.user_input)
    if "medical_concern" in safety["flags"]:
        return {
            "is_medical_concern": True,
            "message": "This is outside Gym Smith's scope. Please consult a qualified professional such as a doctor or certified personal trainer.",
            "ir_process": {"safety_check": safety},
        }

    user_equipment = body.equipment_override or []
    user_memory = get_user_memory(user_id)

    # Stage 1 — agent designs the training framework from the raw goal
    plan_reasoning = _run_stage1_reasoning(
        client=client,
        user_input=body.user_input,
        user_equipment=user_equipment,
        specific_machines=body.specific_machines,
        user_memory=user_memory,
    )

    # Stage 2 — agent executes Stage-1 plan via tool calling
    plan, ir_process = _run_agent_loop(
        client=client,
        user_input=body.user_input,
        plan_reasoning=plan_reasoning,
        user_id=user_id,
        user_equipment=user_equipment,
        specific_machines=body.specific_machines,
    )

    # Persist memory using the agent's reasoned intensity/goal, not user text
    upsert_user_memory(
        user_id,
        user_equipment,
        plan_reasoning.get("intensity", "medium"),
        plan_reasoning.get("interpreted_goal", ""),
        specific_machines=body.specific_machines,
    )
    new_plan_id = save_plan(user_id, body.user_input, plan, plan_reasoning=plan_reasoning)

    return {
        "is_medical_concern": False,
        "plan": plan,
        "plan_id": new_plan_id,
        "plan_reasoning": plan_reasoning,
        "ir_process": ir_process,
    }
