from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.llm_exceptions import LLMProviderError
from app.services.paper_discovery_agent import PaperDiscoveryAgent


@pytest.mark.parametrize("response_text", ["", "   ", "solar forecasting\nmachine learning"])
@pytest.mark.asyncio
async def test_rejects_empty_or_multiline_query(response_text):
    agent = object.__new__(PaperDiscoveryAgent)
    agent.agent = SimpleNamespace(
        run=AsyncMock(return_value=SimpleNamespace(text=response_text))
    )

    with pytest.raises(LLMProviderError):
        await agent.build_search_query("solar irradiance forecasting")

    agent.agent.run.assert_awaited_once_with("solar irradiance forecasting")