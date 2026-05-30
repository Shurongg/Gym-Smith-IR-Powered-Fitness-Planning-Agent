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
