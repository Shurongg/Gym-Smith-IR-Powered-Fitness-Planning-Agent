from db.chroma_store import query_collection


def retrieve_exercises(target_muscles: list[str], goal: str, n_results: int = 20) -> list[dict]:
    muscles_str = " ".join(target_muscles)
    query = f"{muscles_str} {goal} exercises"
    results = query_collection("exercises", query, n_results=n_results)

    exercises = []
    for meta in results["metadatas"][0]:
        exercises.append({
            "name": meta.get("name", ""),
            "category": meta.get("category", ""),
            "muscles": meta.get("muscles", ""),
            "muscles_secondary": meta.get("muscles_secondary", ""),
            "equipment": meta.get("equipment", "None"),
            "description": meta.get("description", ""),
        })
    return exercises
