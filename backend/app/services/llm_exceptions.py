
class LLMConfigurationError(ValueError):
    """Raised when the LLM provider configuration is invalid."""


class LLMProviderError(RuntimeError):
    """Raised when the LLM provider fails to generate a response."""
