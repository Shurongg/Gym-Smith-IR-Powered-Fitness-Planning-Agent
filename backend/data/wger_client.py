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
