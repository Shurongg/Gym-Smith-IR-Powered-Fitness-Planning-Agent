import sqlite3
import json
import uuid
from datetime import datetime, timezone
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
        cols = {row[1] for row in conn.execute("PRAGMA table_info(user_memory)")}
        if "specific_machines" not in cols:
            conn.execute("ALTER TABLE user_memory ADD COLUMN specific_machines TEXT")
        if "nickname" not in cols:
            conn.execute("ALTER TABLE user_memory ADD COLUMN nickname TEXT")
        if "training_level" not in cols:
            conn.execute("ALTER TABLE user_memory ADD COLUMN training_level TEXT")
        if "pinned_plan_id" not in cols:
            conn.execute("ALTER TABLE user_memory ADD COLUMN pinned_plan_id INTEGER")
        plan_cols = {row[1] for row in conn.execute("PRAGMA table_info(plan_history)")}
        if "plan_reasoning_json" not in plan_cols:
            conn.execute("ALTER TABLE plan_history ADD COLUMN plan_reasoning_json TEXT")


def create_user() -> str:
    token = str(uuid.uuid4())
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO users (session_token, created_at) VALUES (?, ?)",
            (token, datetime.now(timezone.utc).replace(tzinfo=None).isoformat()),
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
        "specific_machines": json.loads(row["specific_machines"]) if row["specific_machines"] else [],
        "nickname": row["nickname"] if "nickname" in row.keys() else None,
        "training_level": row["training_level"] if "training_level" in row.keys() else None,
        "pinned_plan_id": row["pinned_plan_id"] if "pinned_plan_id" in row.keys() else None,
    }


def upsert_user_memory(
    user_id: int,
    equipment: list,
    intensity: str,
    goal: str,
    specific_machines: list | None = None,
):
    """Update training-related memory fields. Identity fields (nickname,
    training_level, pinned_plan_id) are managed by their own dedicated helpers
    so they don't get wiped by a plan generation."""
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


def _ensure_memory_row(conn, user_id: int):
    existing = conn.execute(
        "SELECT id FROM user_memory WHERE user_id = ?", (user_id,)
    ).fetchone()
    if not existing:
        now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        conn.execute(
            "INSERT INTO user_memory (user_id, equipment, specific_machines, updated_at) "
            "VALUES (?, ?, ?, ?)",
            (user_id, "[]", "[]", now),
        )


def set_identity(user_id: int, nickname: str, training_level: str):
    """Persist the identity fields captured during onboarding."""
    now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    with get_connection() as conn:
        _ensure_memory_row(conn, user_id)
        conn.execute(
            "UPDATE user_memory SET nickname=?, training_level=?, updated_at=? WHERE user_id=?",
            (nickname, training_level, now, user_id),
        )


def set_pinned_plan(user_id: int, plan_id: int | None) -> bool:
    """Pin or unpin (plan_id=None) a plan for this user.
    Returns False if plan_id is provided but the plan doesn't belong to the user."""
    with get_connection() as conn:
        if plan_id is not None:
            owned = conn.execute(
                "SELECT 1 FROM plan_history WHERE id=? AND user_id=?",
                (plan_id, user_id),
            ).fetchone()
            if not owned:
                return False
        _ensure_memory_row(conn, user_id)
        now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        conn.execute(
            "UPDATE user_memory SET pinned_plan_id=?, updated_at=? WHERE user_id=?",
            (plan_id, now, user_id),
        )
    return True


def get_plan_by_id(user_id: int, plan_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, user_input, plan_json, plan_reasoning_json, created_at "
            "FROM plan_history WHERE id=? AND user_id=?",
            (plan_id, user_id),
        ).fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "user_input": row["user_input"],
        "plan": json.loads(row["plan_json"]),
        "plan_reasoning": json.loads(row["plan_reasoning_json"]) if row["plan_reasoning_json"] else None,
        "created_at": row["created_at"],
    }


def save_plan(user_id: int, user_input: str, plan: dict, plan_reasoning: dict | None = None) -> int:
    """Persist a plan; returns the new plan's id (needed for pinning the
    just-created plan)."""
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO plan_history (user_id, user_input, plan_json, plan_reasoning_json, created_at) "
            "VALUES (?,?,?,?,?)",
            (
                user_id, user_input, json.dumps(plan),
                json.dumps(plan_reasoning) if plan_reasoning else None,
                datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            ),
        )
        return cursor.lastrowid


def get_plan_history(user_id: int, limit: int = 5) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, user_input, plan_json, plan_reasoning_json, created_at "
            "FROM plan_history WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    out = []
    for r in rows:
        out.append({
            "id": r["id"],
            "user_input": r["user_input"],
            "plan": json.loads(r["plan_json"]),
            "plan_reasoning": json.loads(r["plan_reasoning_json"]) if r["plan_reasoning_json"] else None,
            "created_at": r["created_at"],
        })
    return out


def delete_plan(user_id: int, plan_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM plan_history WHERE id = ? AND user_id = ?",
            (plan_id, user_id),
        )
        # If the deleted plan was pinned, clear the pin (orphan reference)
        conn.execute(
            "UPDATE user_memory SET pinned_plan_id=NULL "
            "WHERE user_id=? AND pinned_plan_id=?",
            (user_id, plan_id),
        )
    return cursor.rowcount > 0
