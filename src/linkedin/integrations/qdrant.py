from __future__ import annotations

from functools import lru_cache
from typing import Any

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance,
        FieldCondition,
        Filter,
        MatchValue,
        PointStruct,
        VectorParams,
    )
except ImportError:
    QdrantClient = None
    Distance = None
    FieldCondition = None
    Filter = None
    MatchValue = None
    PointStruct = None
    VectorParams = None

from linkedin.core.config import settings


@lru_cache
def get_qdrant_client() -> Any:
    if QdrantClient is None:
        raise RuntimeError("qdrant-client is not installed. Run `uv sync`.")
    return QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)


def ensure_qdrant_collection() -> None:
    client = get_qdrant_client()
    if client.collection_exists(settings.qdrant_collection_name):
        return

    client.create_collection(
        collection_name=settings.qdrant_collection_name,
        vectors_config=VectorParams(
            size=settings.embedding_dimensions,
            distance=Distance.COSINE,
        ),
    )


def upsert_knowledge_vectors(
    *,
    vectors: list[list[float]],
    payloads: list[dict[str, Any]],
    point_ids: list[str],
) -> None:
    if not vectors:
        return

    ensure_qdrant_collection()
    points = [
        PointStruct(
            id=point_id,
            vector=vector,
            payload=payload,
        )
        for point_id, vector, payload in zip(point_ids, vectors, payloads, strict=True)
    ]
    get_qdrant_client().upsert(
        collection_name=settings.qdrant_collection_name,
        points=points,
    )


def search_knowledge_vectors(
    *,
    query_vector: list[float],
    user_id: str,
    project_id: str,
    limit: int,
) -> list[dict[str, Any]]:
    ensure_qdrant_collection()
    query_filter = Filter(
        must=[
            FieldCondition(key="user_id", match=MatchValue(value=user_id)),
            FieldCondition(key="project_id", match=MatchValue(value=project_id)),
            FieldCondition(key="status", match=MatchValue(value="active")),
        ]
    )
    results = get_qdrant_client().query_points(
        collection_name=settings.qdrant_collection_name,
        query=query_vector,
        query_filter=query_filter,
        limit=limit,
        with_payload=True,
    )
    return [
        {
            "chunk_id": str(point.id),
            "score": float(point.score),
            "payload": dict(point.payload or {}),
        }
        for point in results.points
    ]
