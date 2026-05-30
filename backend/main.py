from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import json

from db.sqlite_store import (
    init_db, create_user, get_user_id, get_user_memory,
    get_plan_history, upsert_user_memory, save_plan
)
from init_knowledge_base import init_knowledge_base
from pipeline.intent_parser import parse_intent
from pipeline.exercise_retriever import retrieve_exercises
from pipeline.equipment_filter import filter_by_equipment
from pipeline.rule_retriever import retrieve_rules
from pipeline.memory_retriever import retrieve_memory
from pipeline.context_assembler import assemble_prompt, SYSTEM_PROMPT


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
