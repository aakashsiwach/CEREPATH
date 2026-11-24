from __future__ import annotations

import math
import os
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx

EMBEDDING_DIMENSIONS = 384


class EmbeddingProviderError(RuntimeError):
    """Raised when the configured local embedding model cannot produce vectors."""


@dataclass(frozen=True)
class LocalOllamaEmbeddingProvider:
    """Local-only embedding adapter using Ollama's /api/embed endpoint.

    Embedding requests are sent directly to the configured local Ollama host;
    no hosted embedding fallback exists. The default all-minilm model produces
    384-dimensional vectors for the pgvector schema.
    """

    base_url: str
    model: str = "all-minilm"
    dimensions: int = EMBEDDING_DIMENSIONS
    timeout_seconds: float = 120.0

    @classmethod
    def from_environment(cls) -> "LocalOllamaEmbeddingProvider | None":
        selected = os.getenv("EMBEDDING_PROVIDER", "disabled").strip().lower()
        if selected in {"", "disabled", "none"}:
            return None
        if selected != "ollama":
            raise EmbeddingProviderError(
                "Unsupported EMBEDDING_PROVIDER. Choose 'ollama' or 'disabled'."
            )

        configured = os.getenv("OLLAMA_EMBEDDING_BASE_URL", "").strip()
        if not configured:
            configured = os.getenv(
                "OLLAMA_BASE_URL", "http://host.docker.internal:11434/v1"
            ).strip()
        parsed = urlsplit(configured)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise EmbeddingProviderError("OLLAMA_EMBEDDING_BASE_URL must be an HTTP(S) URL.")

        # The chat-compatible URL often ends in /v1; Ollama's native embedding
        # API is rooted at /api/embed on the same host.
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        model = os.getenv("OLLAMA_EMBEDDING_MODEL", "all-minilm").strip()
        if not model:
            raise EmbeddingProviderError("OLLAMA_EMBEDDING_MODEL cannot be empty.")
        return cls(base_url=base_url, model=model)

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if any(not text.strip() for text in texts):
            raise ValueError("Embedding inputs cannot contain empty text.")

        vectors: list[list[float]] = []
        # Keep the batch deliberately small to fit local machines.
        with httpx.Client(
            timeout=self.timeout_seconds,
            trust_env=False,
        ) as client:
            for offset in range(0, len(texts), 16):
                batch = texts[offset : offset + 16]
                try:
                    response = client.post(
                        f"{self.base_url}/api/embed",
                        json={"model": self.model, "input": batch},
                    )
                    response.raise_for_status()
                    payload = response.json()
                except (httpx.HTTPError, ValueError) as exc:
                    raise EmbeddingProviderError(
                        "Local Ollama embedding request failed. Check that Ollama is running "
                        "and the configured embedding model is installed."
                    ) from exc

                batch_vectors = payload.get("embeddings")
                if not isinstance(batch_vectors, list) or len(batch_vectors) != len(batch):
                    raise EmbeddingProviderError(
                        "Ollama returned an invalid embedding batch."
                    )
                for vector in batch_vectors:
                    if not isinstance(vector, list) or len(vector) != self.dimensions:
                        actual = len(vector) if isinstance(vector, list) else "unknown"
                        raise EmbeddingProviderError(
                            f"Embedding dimension mismatch: expected {self.dimensions}, got {actual}. "
                            "Use the configured all-minilm model or migrate the vector schema."
                        )
                    try:
                        values = [float(value) for value in vector]
                    except (TypeError, ValueError) as exc:
                        raise EmbeddingProviderError("Embedding contains non-numeric values.") from exc
                    if not all(math.isfinite(value) for value in values):
                        raise EmbeddingProviderError("Embedding contains non-finite values.")
                    vectors.append(values)
        return vectors

    @staticmethod
    def to_pgvector(vector: list[float]) -> str:
        if len(vector) != EMBEDDING_DIMENSIONS:
            raise ValueError(
                f"Expected a {EMBEDDING_DIMENSIONS}-dimensional vector, got {len(vector)}."
            )
        if not all(math.isfinite(float(value)) for value in vector):
            raise ValueError("Vector values must be finite numbers.")
        return "[" + ",".join(format(float(value), ".8g") for value in vector) + "]"
