"""Vector store memory using ChromaDB for persistent user preferences."""
import json
import os
import chromadb
from chromadb.config import Settings


_client = None
_collection = None


def _get_collection():
    global _client, _collection
    if _collection is None:
        persist_dir = os.path.join(os.path.dirname(__file__), "..", "output", "chroma_db")
        os.makedirs(persist_dir, exist_ok=True)
        _client = chromadb.PersistentClient(path=persist_dir)
        _collection = _client.get_or_create_collection(
            name="trip_planner_memory",
            metadata={"description": "User travel preferences and trip history"}
        )
    return _collection


def store_user_preferences(user_id: str, preferences: dict) -> bool:
    """Store user travel preferences in vector DB."""
    try:
        col = _get_collection()
        doc_id = f"user_{user_id}_prefs"
        doc_text = json.dumps(preferences, ensure_ascii=False)
        col.upsert(
            ids=[doc_id],
            documents=[doc_text],
            metadatas=[{"user_id": user_id, "type": "preferences"}]
        )
        return True
    except Exception as e:
        print(f"[Memory] Store error: {e}")
        return False


def retrieve_user_preferences(user_id: str) -> dict:
    """Retrieve past user travel preferences."""
    try:
        col = _get_collection()
        doc_id = f"user_{user_id}_prefs"
        results = col.get(ids=[doc_id])
        if results and results["documents"]:
            return json.loads(results["documents"][0])
        return {}
    except Exception as e:
        print(f"[Memory] Retrieve error: {e}")
        return {}


def store_trip_history(user_id: str, trip_summary: dict) -> bool:
    """Store completed trip as part of user history."""
    try:
        col = _get_collection()
        import time
        doc_id = f"trip_{user_id}_{int(time.time())}"
        doc_text = json.dumps(trip_summary, ensure_ascii=False)
        col.upsert(
            ids=[doc_id],
            documents=[doc_text],
            metadatas=[{
                "user_id": user_id,
                "type": "trip_history",
                "destination": trip_summary.get("destination", ""),
            }]
        )
        return True
    except Exception as e:
        print(f"[Memory] Trip history store error: {e}")
        return False


def search_similar_trips(destination: str, preferences: str, n_results: int = 3) -> list:
    """Semantic search for similar past trips."""
    try:
        col = _get_collection()
        query = f"{destination} {preferences}"
        results = col.query(query_texts=[query], n_results=n_results,
                            where={"type": "trip_history"})
        trips = []
        for doc in (results.get("documents") or [[]])[0]:
            try:
                trips.append(json.loads(doc))
            except Exception:
                pass
        return trips
    except Exception as e:
        print(f"[Memory] Search error: {e}")
        return []
