import os
from pathlib import Path

os.environ["ANONYMIZED_TELEMETRY"] = "False"

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

# chromadb 0.5.3 calls posthog.capture(user_id, event_name, properties) with
# three positional args; the installed posthog no longer accepts that signature
# and chromadb logs the resulting error.  Settings(anonymized_telemetry=False)
# does not reliably stop it.  Replacing the actual telemetry method with a
# no-op is the only fix that works in practice.
try:
    from chromadb.telemetry.product.posthog import Posthog as _ChromaPosthog
    _ChromaPosthog._direct_capture = lambda self, event: None
    _ChromaPosthog.capture = lambda self, event: None
except Exception:
    pass

CHROMA_PATH = str(Path(__file__).parent.parent / "data" / "chroma")

_client = None
_ef = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")


def get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        Path(CHROMA_PATH).mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=CHROMA_PATH,
            settings=chromadb.Settings(anonymized_telemetry=False),
        )
    return _client


def get_or_create_collection(name: str) -> chromadb.Collection:
    return get_client().get_or_create_collection(
        name=name,
        embedding_function=_ef,
        metadata={"hnsw:space": "cosine"},
    )


def collection_exists_with_data(name: str) -> bool:
    try:
        col = get_client().get_collection(name, embedding_function=_ef)
        return col.count() > 0
    except Exception:
        return False


def upsert_documents(
    collection_name: str,
    ids: list[str],
    documents: list[str],
    metadatas: list[dict],
):
    col = get_or_create_collection(collection_name)
    col.upsert(ids=ids, documents=documents, metadatas=metadatas)


def query_collection(
    collection_name: str,
    query_text: str,
    n_results: int = 20,
    where: dict = None,
) -> dict:
    col = get_or_create_collection(collection_name)
    kwargs = {"query_texts": [query_text], "n_results": n_results}
    if where:
        kwargs["where"] = where
    return col.query(**kwargs)
