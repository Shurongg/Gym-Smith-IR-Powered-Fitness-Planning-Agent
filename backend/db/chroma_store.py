import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from pathlib import Path

CHROMA_PATH = str(Path(__file__).parent.parent / "data" / "chroma")

_client = None
_ef = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")


def get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=CHROMA_PATH)
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
