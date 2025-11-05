"""
Base LLM Interface for HTN Planner
===================================

This module defines the abstract base class that all LLM clients must implement.
It ensures a consistent API across all LLM providers (local and cloud-based).

Author: HTN Planner Team
Date: October 8, 2025
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class LLMResponse:
    """Encapsulates the response from an LLM"""

    content: str  # The generated text
    model: str  # Model used
    provider: str  # Provider name (e.g., "gemini", "ollama")
    tokens_used: Optional[Dict[str, int]] = None  # Token usage breakdown (if available)
    finish_reason: Optional[str] = None  # Why generation stopped
    metadata: Optional[Dict[str, Any]] = None  # Additional provider-specific data

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class LLMConfig:
    """Configuration for LLM client"""

    model_name: str  # Model identifier
    temperature: float = (
        0.7  # Sampling temperature (0.0 = deterministic, 1.0 = creative)
    )
    max_tokens: int = 2048  # Maximum tokens to generate
    top_p: float = 0.9  # Nucleus sampling parameter
    timeout: int = 60  # Request timeout in seconds
    retries: int = 3  # Number of retries on failure
    stream: bool = False  # Stream responses (if supported)

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            "model": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "timeout": self.timeout,
            "retries": self.retries,
            "stream": self.stream,
        }


class BaseLLMClient(ABC):
    """
    Abstract base class for all LLM clients.

    All LLM implementations (Gemini, Groq, Cohere, Mistral, Ollama, etc.)
    must inherit from this class and implement its abstract methods.

    This ensures:
    - Consistent API across all providers
    - Easy switching between providers
    - Standardized error handling
    - Unified logging and monitoring
    """

    def __init__(
        self, api_key: Optional[str] = None, config: Optional[LLMConfig] = None
    ):
        """
        Initialize LLM client.

        Args:
            api_key: API key for the provider (None for local models)
            config: LLM configuration (uses defaults if not provided)
        """
        self.api_key = api_key
        self.config = config or LLMConfig(model_name="default")
        self.provider_name = self.__class__.__name__.replace("Client", "").lower()
        logger.info(f"Initializing {self.provider_name} LLM client")

    @abstractmethod
    def generate(
        self, prompt: str, system_prompt: Optional[str] = None, **kwargs
    ) -> LLMResponse:
        """
        Generate text completion from a prompt.

        Args:
            prompt: The main prompt/query
            system_prompt: Optional system instructions
            **kwargs: Provider-specific parameters

        Returns:
            LLMResponse object with generated content

        Raises:
            LLMException: If generation fails
        """
        pass

    @abstractmethod
    def generate_with_history(
        self, messages: List[Dict[str, str]], **kwargs
    ) -> LLMResponse:
        """
        Generate completion with conversation history.

        Args:
            messages: List of message dicts with 'role' and 'content'
                     Example: [{"role": "user", "content": "Hello"}]
            **kwargs: Provider-specific parameters

        Returns:
            LLMResponse object with generated content

        Raises:
            LLMException: If generation fails
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the LLM service is available.

        Returns:
            True if service is reachable and functioning
        """
        pass

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model.

        Returns:
            Dictionary with model details
        """
        return {
            "provider": self.provider_name,
            "model": self.config.model_name,
            "config": self.config.to_dict(),
        }

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for a text (rough approximation).

        Args:
            text: Input text

        Returns:
            Estimated number of tokens
        """
        # Rough estimate: ~4 characters per token for English
        return len(text) // 4

    def validate_config(self) -> bool:
        """
        Validate the current configuration.

        Returns:
            True if configuration is valid
        """
        if self.config.temperature < 0 or self.config.temperature > 2:
            logger.warning(
                f"Temperature {self.config.temperature} outside recommended range [0, 2]"
            )
            return False

        if self.config.max_tokens <= 0:
            logger.error(f"Invalid max_tokens: {self.config.max_tokens}")
            return False

        return True

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.config.model_name}, provider={self.provider_name})"


class LLMException(Exception):
    """Base exception for LLM-related errors"""

    def __init__(
        self,
        message: str,
        provider: str = "unknown",
        original_error: Optional[Exception] = None,
        **kwargs,
    ):
        self.message = message
        self.provider = provider
        self.original_error = original_error
        # Store any additional metadata
        for key, value in kwargs.items():
            setattr(self, key, value)
        super().__init__(f"[{provider}] {message}")


class LLMRateLimitError(LLMException):
    """Raised when rate limit is exceeded"""

    def __init__(
        self,
        message: str,
        provider: str = "unknown",
        retry_after: int = 60,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(message, provider, original_error)
        self.retry_after = retry_after


class LLMAPIError(LLMException):
    """Raised when API returns an error"""

    def __init__(
        self,
        message: str,
        provider: str = "unknown",
        status_code: Optional[int] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(message, provider, original_error)
        self.status_code = status_code


class LLMTimeoutError(LLMException):
    """Raised when request times out"""

    def __init__(
        self,
        message: str,
        provider: str = "unknown",
        timeout: Optional[float] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(message, provider, original_error)
        self.timeout = timeout


class LLMConnectionError(LLMException):
    """Raised when connection to LLM service fails"""

    pass


# Utility functions for LLM clients


def format_messages_for_chat(messages: List[Dict[str, str]]) -> str:
    """
    Convert message history to a single formatted prompt.
    Useful for models that don't support native chat format.

    Args:
        messages: List of message dicts with 'role' and 'content'

    Returns:
        Formatted prompt string
    """
    formatted = []
    for msg in messages:
        role = msg.get("role", "user").upper()
        content = msg.get("content", "")
        formatted.append(f"{role}: {content}")
    return "\n\n".join(formatted)


def truncate_prompt(prompt: str, max_length: int = 10000) -> str:
    """
    Truncate prompt if it exceeds maximum length.

    Args:
        prompt: Input prompt
        max_length: Maximum character length

    Returns:
        Truncated prompt with indicator if truncated
    """
    if len(prompt) <= max_length:
        return prompt

    truncated = prompt[: max_length - 50]
    return f"{truncated}\n\n[... prompt truncated for length ...]"


def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """
    Decorator for retrying LLM requests on failure.

    Args:
        max_retries: Maximum number of retry attempts
        delay: Delay between retries in seconds
    """
    import time
    from functools import wraps

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception: Optional[Exception] = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (
                    LLMRateLimitError,
                    LLMAPIError,
                    LLMTimeoutError,
                    LLMConnectionError,
                ) as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = delay * (2**attempt)  # Exponential backoff
                        logger.warning(
                            f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s..."
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(f"All {max_retries} attempts failed: {e}")

            # This should never happen since we always catch and set last_exception
            if last_exception is None:
                raise LLMException(
                    "Retry logic failed without catching an exception", "unknown"
                )
            raise last_exception

        return wrapper

    return decorator
