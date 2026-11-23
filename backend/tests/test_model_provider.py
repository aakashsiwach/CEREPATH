import asyncio

import pytest

from app.intelligence.provider import DisabledModelProvider, NoModelConfigured


def test_default_model_provider_fails_closed_without_network_calls():
    provider = DisabledModelProvider()
    with pytest.raises(NoModelConfigured, match="External AI calls are disabled"):
        asyncio.run(provider.complete("hello"))
