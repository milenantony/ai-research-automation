import pytest
from unittest.mock import MagicMock, patch
from app.services.llm_exceptions import LLMProviderError
from app.services.providers.gemini import GeminiProvider

def test_missing_api_key():
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(
            ValueError,
            match="GEMINI_API_KEY is missing"
        ):
            GeminiProvider()

@patch("app.services.providers.gemini.genai.Client")
def test_provider_initialization(mock_client):
    with patch.dict(
        "os.environ",
        {"GEMINI_API_KEY": "test-api-key"},
        clear=True
    ):
        provider = GeminiProvider()

    assert provider.model == "gemini-3.6-flash"
    mock_client.assert_called_once_with(
        api_key="test-api-key"
    )


@patch("app.services.providers.gemini.genai.Client")
def test_generate_response(mock_client):
    mock_response = MagicMock()
    mock_response.text = "This is a test response."

    mock_client.return_value.models.generate_content.return_value = (
        mock_response
    )

    with patch.dict(
        "os.environ",
        {"GEMINI_API_KEY": "test-api-key"},
        clear=True
    ):
        provider = GeminiProvider()

    result = provider.generate_response(
        "Explain artificial intelligence"
    )

    assert result == "This is a test response."

    mock_client.return_value.models.generate_content.assert_called_once_with(
        model="gemini-3.6-flash",
        contents="Explain artificial intelligence"
    )


@patch("app.services.providers.gemini.genai.Client")
def test_empty_prompt(mock_client):
    with patch.dict(
        "os.environ",
        {"GEMINI_API_KEY": "test-api-key"},
        clear=True
    ):
        provider = GeminiProvider()

    with pytest.raises(
        ValueError,
        match="Prompt cannot be empty"
    ):
        provider.generate_response("")


@patch("app.services.providers.gemini.genai.Client")
def test_whitespace_prompt(mock_client):
    with patch.dict(
        "os.environ",
        {"GEMINI_API_KEY": "test-api-key"},
        clear=True
    ):
        provider = GeminiProvider()

    with pytest.raises(
        ValueError,
        match="Prompt cannot be empty"
    ):
        provider.generate_response("   ")


@patch("app.services.providers.gemini.genai.Client")
def test_empty_gemini_response(mock_client):
    mock_response = MagicMock()
    mock_response.text = None

    mock_client.return_value.models.generate_content.return_value = (
        mock_response
    )

    with patch.dict(
        "os.environ",
        {"GEMINI_API_KEY": "test-api-key"},
        clear=True
    ):
        provider = GeminiProvider()

    with pytest.raises(
        RuntimeError,
        match="Gemini returned an empty response"
    ):
        provider.generate_response("Test prompt")



@patch("app.services.providers.gemini.genai.Client")
def test_gemini_api_error(mock_client):
    mock_client.return_value.models.generate_content.side_effect = (
        RuntimeError("API connection failed")
    )

    with patch.dict(
        "os.environ",
        {"GEMINI_API_KEY": "test-api-key"},
        clear=True
    ):
        provider = GeminiProvider()

    with pytest.raises(
        LLMProviderError,
        match="Gemini API request failed"
    ) as exc_info:
        provider.generate_response("Test prompt")

    # Verify original exception is preserved
    assert isinstance(exc_info.value.__cause__, RuntimeError)

    assert str(exc_info.value.__cause__) == "API connection failed"
