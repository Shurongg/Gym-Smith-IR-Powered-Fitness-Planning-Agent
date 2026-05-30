from db.chroma_store import query_collection


def retrieve_rules(goal: str, n_training: int = 5, n_nutrition: int = 3) -> list[dict]:
    training_query = f"{goal} training principles sets reps rest recovery"
    nutrition_query = f"{goal} nutrition protein diet food"

    training_results = query_collection("rules", training_query, n_results=n_training,
                                         where={"type": {"$ne": "nutrition_rule"}})
    nutrition_results = query_collection("rules", nutrition_query, n_results=n_nutrition,
                                          where={"type": {"$eq": "nutrition_rule"}})

    rules = []
    for meta in training_results["metadatas"][0]:
        rules.append(dict(meta))
    for meta in nutrition_results["metadatas"][0]:
        rules.append(dict(meta))
    return rules
