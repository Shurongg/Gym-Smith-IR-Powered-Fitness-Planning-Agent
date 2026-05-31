import aiohttp

FREEEXDB_URL = (
    "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/dist/exercises.json"
)

EQUIPMENT_NORM_MAP = {
    # wger values
    "none": "bodyweight",
    "none (bodyweight exercise)": "bodyweight",
    "gym mat": "bodyweight",
    "dumbbell": "dumbbell",
    "barbell": "barbell",
    "sz-bar": "barbell",
    "bench": "bench",
    "incline bench": "bench",
    "pull-up bar": "pull-up bar",
    "kettlebell": "kettlebell",
    "resistance band": "resistance band",
    # Free Exercise DB values
    "body only": "bodyweight",
    "cable": "cable",
    "machine": "machine",
    "bands": "resistance band",
    "e-z curl bar": "barbell",
}


def normalize_equipment(raw: str | None) -> str | None:
    if not raw:
        return None
    return EQUIPMENT_NORM_MAP.get(raw.lower().strip())


def _parse_exercise(raw: dict) -> dict | None:
    canonical_eq = normalize_equipment(raw.get("equipment"))
    if canonical_eq is None:
        return None
    instructions = raw.get("instructions", [])
    description = " ".join(instructions[:3])
    return {
        "exercise_id": f"fex_{raw['id']}",
        "name": raw["name"],
        "category": raw.get("category", "general"),
        "muscles": raw.get("primaryMuscles", []),
        "muscles_secondary": raw.get("secondaryMuscles", []),
        "equipment": [canonical_eq],
        "description": description,
    }


async def fetch_free_exercise_db() -> list[dict]:
    async with aiohttp.ClientSession() as session:
        async with session.get(FREEEXDB_URL, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            resp.raise_for_status()
            data = await resp.json(content_type=None)
    return [ex for raw in data if (ex := _parse_exercise(raw)) is not None]
