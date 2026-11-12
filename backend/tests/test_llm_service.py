
import pytest
from unittest.mock import patch, MagicMock

from app.services.llm_service import LLMService


@patch("app.services.llm_service.GeminiProvider")
def test_default_provider_is_gemini(mock_gemini):
    with patch.dict("os.environ", {}, clear=True):
        service = LLMService()

    mock_gemini.assert_called_once()
    assert isinstance(service.provider, MagicMock)


@patch("app.services.llm_service.GeminiProvider")
def test_gemini_provider_selection(mock_gemini):
    with patch.dict(
        "os.environ",
        {"LLM_PROVIDER": "gemini"},
        clear=True
    ):
        service = LLMService()

    mock_gemini.assert_called_once()


@patch("app.services.llm_service.GeminiProvider")
def test_provider_selection_is_case_insensitive(mock_gemini):
    with patch.dict(
        "os.environ",
        {"LLM_PROVIDER": "GEMINI"},
        clear=True
    ):
        service = LLMService()

    mock_gemini.assert_called_once()


def test_unsupported_provider():
    with patch.dict(
        "os.environ",
        {"LLM_PROVIDER": "unsupported"},
        clear=True
    ):
        with pytest.raises(
            ValueError,
            match="Unsupported LLM provider: unsupported"
        ):
            LLMService()


@patch("app.services.llm_service.GeminiProvider")
def test_generate_response(mock_gemini):
    mock_provider = mock_gemini.return_value

    mock_provider.generate_response.return_value = (
        "Artificial intelligence research result."
    )

    with patch.dict(
        "os.environ",
        {"LLM_PROVIDER": "gemini"},
        clear=True
    ):
        service = LLMService()

    result = service.generate(
        "Explain artificial intelligence"
    )

    assert result == "Artificial intelligence research result."

    mock_provider.generate_response.assert_called_once_with(
        "Explain artificial intelligence"
    )
