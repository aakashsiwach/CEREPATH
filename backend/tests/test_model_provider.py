import asyncio

import httpx
import pytest

from app.intelligence.provider import (
    DisabledModelProvider,
    ModelProviderError,
    NoModelConfigured,
    OpenAICompatibleProvider,
    build_model_provider,
)


def test_disabled_provider_fails_closed_without_network_calls():
    provider = DisabledModelProvider()
    with pytest.raises(NoModelConfigured, match="No AI provider"):
        asyncio.run(provider.complete([{"role": "user", "content": "hello"}]))


def test_bynara_configuration_uses_supplied_endpoint_and_model(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "bynara")
    monkeypatch.setenv("BYNARA_API_KEY", "test-secret-key")
    monkeypatch.setenv("AI_HTTP_PROXY", "http://egress-proxy:3128")
    provider = build_model_provider()
    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.base_url == "https://router.bynara.id/v1"
    assert provider.model == "gpt-5.6-luna"
    assert provider.api_key == "test-secret-key"
    assert provider.proxy == "http://egress-proxy:3128"


def test_bynara_is_disabled_when_key_is_missing(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "bynara")
    monkeypatch.delenv("BYNARA_API_KEY", raising=False)
    provider = build_model_provider()
    assert isinstance(provider, DisabledModelProvider)


def test_ollama_provider_never_uses_external_egress_proxy(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    monkeypatch.setenv("AI_HTTP_PROXY", "http://egress-proxy:3128")
    provider = build_model_provider()
    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.name == "ollama"
    assert provider.proxy is None


def test_openai_compatible_provider_sends_expected_chat_payload(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "  Hello from Bynara  "}}]}

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            captured["client_options"] = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url, *, headers, json):
            captured.update({"url": url, "headers": headers, "payload": json})
            return FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    provider = OpenAICompatibleProvider(
        name="bynara",
        base_url="https://router.bynara.id/v1/",
        model="gpt-5.6-luna",
        api_key="secret",
        proxy="http://egress-proxy:3128",
    )
    messages = [{"role": "user", "content": "Hello"}]
    reply = asyncio.run(provider.complete(messages))

    assert reply.text == "Hello from Bynara"
    assert reply.provider == "bynara"
    assert captured["url"] == "https://router.bynara.id/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer secret"
    assert captured["payload"] == {
        "model": "gpt-5.6-luna",
        "messages": messages,
        "stream": False,
    }
    assert captured["client_options"]["proxy"] == "http://egress-proxy:3128"
    assert captured["client_options"]["trust_env"] is False


def test_provider_does_not_leak_upstream_error_body(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            request = httpx.Request("POST", "https://router.bynara.id/v1/chat/completions")
            response = httpx.Response(401, request=request, text="sensitive upstream content")
            raise httpx.HTTPStatusError("unauthorized", request=request, response=response)

    class FakeAsyncClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, *_args, **_kwargs):
            return FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    provider = OpenAICompatibleProvider(name="bynara", base_url="https://router.bynara.id/v1", model="gpt-5.6-luna")
    with pytest.raises(ModelProviderError, match="HTTP 401") as error:
        asyncio.run(provider.complete([{"role": "user", "content": "Hi"}]))
    assert "sensitive upstream content" not in str(error.value)
