from db.chroma_store import query_collection
from pipeline.normalize import EQUIPMENT_BOOLEAN_KEYS


def retrieve_exercises(
    target_muscles: list[str],
    goal: str,
    specific_machines: list[str] | None = None,
    equipment_hint: list[str] | None = None,
    n_results_per_query: int = 15,
) -> list[dict]:
    seen_names: set[str] = set()
    exercises: list[dict] = []

    def _absorb(results: dict) -> None:
        for meta in results["metadatas"][0]:
            name = meta.get("name", "")
            if name and name not in seen_names:
                seen_names.add(name)
                out = {
                    "name": name,
                    "category": meta.get("category", ""),
                    "muscles": meta.get("muscles", ""),
                    "muscles_secondary": meta.get("muscles_secondary", ""),
                    "equipment": meta.get("equipment", "None"),
                    "description": meta.get("description", ""),
                }
                for k in EQUIPMENT_BOOLEAN_KEYS:
                    out[k] = bool(meta.get(k, False))
                exercises.append(out)

    equip_str = " ".join(equipment_hint[:2]) if equipment_hint else ""
    queries = [f"{m} {goal} {equip_str} exercises".strip() for m in target_muscles] or [f"{goal} exercises"]
    for q in queries:
        _absorb(query_collection("exercises", q, n_results=n_results_per_query))

    for machine in (specific_machines or []):
        _absorb(query_collection("exercises", f"{machine} exercises", n_results=10))

    return exercises
