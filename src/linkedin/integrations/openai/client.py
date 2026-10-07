from __future__ import annotations

from typing import Any

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from linkedin.core.config import settings


def get_openai_client() -> Any:
    if OpenAI is None:
        raise RuntimeError(
            "The OpenAI SDK is not installed. Run `uv sync` to install dependencies."
        )
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured.")
    return OpenAI(api_key=settings.openai_api_key)
