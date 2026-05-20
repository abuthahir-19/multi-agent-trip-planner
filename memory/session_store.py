"""Session store — in-memory dict with optional Redis backend."""
import json
from config.settings import REDIS_URL

_sessions: dict = {}


def _get_redis():
    if not REDIS_URL:
        return None
    try:
        import redis
        return redis.from_url(REDIS_URL, decode_responses=True)
    except Exception:
        return None


def set_session(session_id: str, key: str, value) -> None:
    r = _get_redis()
    if r:
        try:
            r.hset(f"trip_session:{session_id}", key, json.dumps(value))
            r.expire(f"trip_session:{session_id}", 86400)
            return
        except Exception:
            pass
    if session_id not in _sessions:
        _sessions[session_id] = {}
    _sessions[session_id][key] = value


def get_session(session_id: str, key: str, default=None):
    r = _get_redis()
    if r:
        try:
            val = r.hget(f"trip_session:{session_id}", key)
            return json.loads(val) if val else default
        except Exception:
            pass
    return _sessions.get(session_id, {}).get(key, default)


def clear_session(session_id: str) -> None:
    r = _get_redis()
    if r:
        try:
            r.delete(f"trip_session:{session_id}")
        except Exception:
            pass
    _sessions.pop(session_id, None)
