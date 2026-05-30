from db.sqlite_store import get_user_memory


def retrieve_memory(user_id: int) -> dict | None:
    return get_user_memory(user_id)
