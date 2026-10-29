"""Provider-independent embedding generation.

The application is never coupled to a single embedding vendor.  The provider
is selected through ``RAG_EMBEDDING_PROVIDER``:

* ``""`` (default) — not configured; live embedding calls fail with a safe
  configuration error.  The rest of the application runs unchanged.
* ``test`` — deterministic, dependency-free provider used only by tests and
  local development.  It is lexical, not semantic.
* ``openai`` — any OpenAI-compatible ``/embeddings`` endpoint.  Requires
  ``RAG_OPENAI_API_KEY`` to be supplied via the environment.

API keys are never hard-coded; they are read from settings/environment.
"""

import hashlib
import re
from typing import Protocol

from app.config.settings import get_settings

_TOKEN_RE = re.compile(r"[a-z0-9]+")


class EmbeddingError(Exception):
    """Safe, user-presentable embedding failure."""


class EmbeddingConfigurationError(EmbeddingError):
    """Raised when no usable embedding provider is configured."""


class EmbeddingProvider(Protocol):
    model_name: str
    dimensions: int

    def embed_texts(self, texts: list[str]) -> list[list[float]]: ...

    def embed_text(self, text: str) -> list[float]: ...


class TestEmbeddingProvider:
    """Deterministic lexical embedding provider for tests/development only.

    Tokens are hashed into a fixed-size vector with a stable sign, then
    L2-normalised.  Cosine similarity therefore reflects shared vocabulary.
    This is intentionally inexpensive and reproducible — not a semantic model.
    """

    def __init__(self, model_name: str = "test-hashing-embeddings", dimensions: int = 64):
        self.model_name = model_name
        self.dimensions = dimensions

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in _TOKEN_RE.findall((text or "").lower()):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:8], "big") % self.dimensions
            sign = 1.0 if digest[8] & 1 else -1.0
            vector[index] += sign
        norm = sum(value * value for value in vector) ** 0.5
        if norm == 0.0:
            return vector
        return [value / norm for value in vector]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_text(self, text: str) -> list[float]:
        return self._embed(text)


class OpenAIEmbeddingProvider:
    """OpenAI-compatible embeddings adapter built on httpx."""

    def __init__(
        self,
        api_url: str,
        api_key: str,
        model_name: str,
        timeout: float = 30.0,
    ):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.model_name = model_name or "text-embedding-3-small"
        self.timeout = timeout
        self.dimensions = 0  # discovered from the first response

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        import httpx

        if not texts:
            return []
        try:
            response = httpx.post(
                f"{self.api_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": self.model_name, "input": texts},
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:  # network/provider failure — never leak internals
            raise EmbeddingError("Embedding generation failed.") from exc

        data = payload.get("data") or []
        if len(data) != len(texts):
            raise EmbeddingError("Embedding generation failed.")
        embeddings = [
            item["embedding"]
            for item in sorted(data, key=lambda item: item.get("index", 0))
        ]
        if embeddings and not self.dimensions:
            self.dimensions = len(embeddings[0])
        return embeddings

    def embed_text(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]


def get_embedding_provider() -> EmbeddingProvider:
    """Resolve the configured embedding provider or raise a safe error."""
    settings = get_settings()
    provider = (settings.rag_embedding_provider or "").strip().lower()

    if provider == "test":
        return TestEmbeddingProvider(
            model_name=settings.rag_embedding_model or "test-hashing-embeddings"
        )
    if provider == "openai":
        if not settings.rag_openai_api_key:
            raise EmbeddingConfigurationError("AI provider is not configured.")
        return OpenAIEmbeddingProvider(
            api_url=settings.rag_openai_api_url,
            api_key=settings.rag_openai_api_key,
            model_name=settings.rag_embedding_model,
            timeout=settings.rag_openai_timeout_seconds,
        )
    raise EmbeddingConfigurationError("AI provider is not configured.")


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts using the configured provider (batched)."""
    settings = get_settings()
    provider = get_embedding_provider()
    batch_size = max(1, int(settings.rag_embedding_batch_size))
    vectors: list[list[float]] = []
    for start in range(0, len(texts), batch_size):
        vectors.extend(provider.embed_texts(texts[start : start + batch_size]))
    return vectors


def embed_text(text: str) -> list[float]:
    return embed_texts([text])[0]
