import pytest

from app.intelligence.embeddings import (
    EMBEDDING_DIMENSIONS,
    EmbeddingProviderError,
    LocalOllamaEmbeddingProvider,
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeClient:
    def __init__(self, *args, **kwargs):
        self.posts = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def post(self, url, json):
        self.posts.append((url, json))
        return FakeResponse({"embeddings": [[0.25] * EMBEDDING_DIMENSIONS for _ in json["input"]]})


def test_embeddings_default_to_disabled(monkeypatch):
    monkeypatch.delenv("EMBEDDING_PROVIDER", raising=False)
    assert LocalOllamaEmbeddingProvider.from_environment() is None


def test_local_embedding_provider_strips_openai_v1_suffix(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434/v1")
    monkeypatch.delenv("OLLAMA_EMBEDDING_BASE_URL", raising=False)

    provider = LocalOllamaEmbeddingProvider.from_environment()
    assert provider is not None
    assert provider.base_url == "http://host.docker.internal:11434"
    assert provider.model == "all-minilm"
    assert provider.dimensions == 384


def test_local_embedding_provider_batches_and_validates_dimensions(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_EMBEDDING_BASE_URL", "http://localhost:11434")
    monkeypatch.setattr("app.intelligence.embeddings.httpx.Client", FakeClient)

    provider = LocalOllamaEmbeddingProvider.from_environment()
    assert provider is not None
    vectors = provider.embed(["first lesson", "second lesson"])
    assert len(vectors) == 2
    assert all(len(vector) == EMBEDDING_DIMENSIONS for vector in vectors)
    assert provider.to_pgvector(vectors[0]).startswith("[0.25,0.25,")


def test_embedding_provider_rejects_wrong_dimensions(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_EMBEDDING_BASE_URL", "http://localhost:11434")

    class WrongDimensionClient(FakeClient):
        def post(self, url, json):
            return FakeResponse({"embeddings": [[0.1, 0.2, 0.3]]})

    monkeypatch.setattr("app.intelligence.embeddings.httpx.Client", WrongDimensionClient)
    provider = LocalOllamaEmbeddingProvider.from_environment()
    assert provider is not None
    try:
        provider.embed(["wrong dimension"])
    except EmbeddingProviderError as exc:
        assert "dimension mismatch" in str(exc).lower()
    else:
        raise AssertionError("An embedding with the wrong dimension must be rejected")


def test_vector_formatter_rejects_wrong_size_and_non_finite_values():
    provider = LocalOllamaEmbeddingProvider(base_url="http://localhost:11434")
    with pytest.raises(ValueError, match="384-dimensional"):
        provider.to_pgvector([0.1, 0.2])
    with pytest.raises(ValueError, match="finite"):
        provider.to_pgvector([0.1] * 383 + [float("nan")])
