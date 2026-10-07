from __future__ import annotations

from linkedin.core.config import settings
from linkedin.integrations.openai.client import get_openai_client


def create_embeddings(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    response = get_openai_client().embeddings.create(
        model=settings.embedding_model,
        input=texts,
    )
    return [list(item.embedding) for item in response.data]
