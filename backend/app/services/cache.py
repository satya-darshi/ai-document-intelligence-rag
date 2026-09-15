import hashlib
import json

from redis import Redis

from app.core.config import get_settings

settings = get_settings()
redis_client = Redis.from_url(settings.redis_url, decode_responses=True)


def make_key(question: str, document_ids: list[str]) -> str:
    raw = json.dumps({"q": question.strip(), "docs": sorted(document_ids)}, sort_keys=True)
    digest = hashlib.sha256(raw.encode()).hexdigest()
    return f"rag:answer:{digest}"


def get_cached(key: str) -> dict | None:
    value = redis_client.get(key)
    return json.loads(value) if value else None


def set_cached(key: str, value: dict) -> None:
    redis_client.setex(key, settings.cache_ttl_seconds, json.dumps(value))
