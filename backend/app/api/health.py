from fastapi import APIRouter
from qdrant_client import QdrantClient
from redis import Redis
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import engine
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/health", response_model=HealthResponse)
def health():
    postgres = "ok"
    redis = "ok"
    qdrant = "ok"
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        postgres = "down"
    try:
        Redis.from_url(settings.redis_url).ping()
    except Exception:
        redis = "down"
    try:
        QdrantClient(url=settings.qdrant_url).get_collections()
    except Exception:
        qdrant = "down"
    overall = "ok" if postgres == redis == qdrant == "ok" else "degraded"
    return HealthResponse(status=overall, postgres=postgres, redis=redis, qdrant=qdrant)
