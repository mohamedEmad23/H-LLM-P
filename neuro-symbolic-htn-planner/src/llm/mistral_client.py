"""
Mistral AI LLM Client Implementation

This module provides a client for interacting with Mistral AI's language models via their API.
Supports models like mistral-large-latest, ministral-8b-latest, and codestral-latest.

Features:
- Chat completion with message history
- Support for all Mistral AI models
- Automatic retry with exponential backoff
- Comprehensive error handling and categorization
- Token usage tracking

Example:
    >>> from mistral_client import MistralClient
    >>> client = MistralClient(api_key="your-api-key")
    >>> response = client.generate("Explain quantum computing")
    >>> print(response.content)
"""

import os
from typing import Dict, List, Optional, Any
from loguru import logger

try:
    from mistralai import Mistral
except ImportError:
    logger.error("mistralai package not installed. Run: pip install mistralai")
    raise

try:
    from .local_llm_interface import (
        BaseLLMClient,
        LLMResponse,
        LLMConfig,
        LLMException,
        LLMRateLimitError,
        LLMAPIError,
        LLMTimeoutError,
        LLMConnectionError,
        retry_on_failure,
    )
except ImportError:
    from local_llm_interface import (
        BaseLLMClient,
        LLMResponse,
        LLMConfig,
        LLMException,
        LLMRateLimitError,
        LLMAPIError,
        LLMTimeoutError,
        LLMConnectionError,
        retry_on_failure,
    )


class MistralClient(BaseLLMClient):
    """
    Client for Mistral AI API.

    Supports multiple Mistral models optimized for different use cases:
    - mistral-large-latest: Most capable model for complex reasoning
    - ministral-8b-latest: Fast, efficient model for most tasks
    - codestral-latest: Specialized for code generation
    - mistral-small-latest: Lightweight model for simple tasks

    Attributes:
        DEFAULT_MODEL: The default model to use if none specified
        SUPPORTED_MODELS: Dictionary of available models with their context windows
        api_key: Mistral AI API key
        config: LLM configuration settings
        client: Mistral API client instance
    """

    DEFAULT_MODEL = "mistral-large-latest"
    SUPPORTED_MODELS = {
        "mistral-large-latest": 128000,  # Most powerful model
        "mistral-small-latest": 128000,  # Lightweight model
        "ministral-8b-latest": 128000,  # Fast, efficient model
        "ministral-3b-latest": 128000,  # Smallest model
        "codestral-latest": 256000,  # Code generation specialist
        "open-mistral-nemo": 128000,  # Open source variant
    }

    def __init__(
        self, api_key: Optional[str] = None, config: Optional[LLMConfig] = None
    ):
        """
        Initialize Mistral client.

        Args:
            api_key: Mistral AI API key. If not provided, reads from MISTRAL_API_KEY env var
            config: LLM configuration. Uses defaults if not provided

        Raises:
            LLMException: If API key is not found
        """
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY")
        if not self.api_key:
            raise LLMException(
                "Mistral API key not found. Set MISTRAL_API_KEY environment variable."
            )

        self.config = config or LLMConfig(model_name=self.DEFAULT_MODEL)

        # Initialize base class (sets provider_name)
        super().__init__(api_key=self.api_key, config=self.config)

        # Validate model
        if self.config.model_name not in self.SUPPORTED_MODELS:
            logger.warning(
                f"Model {self.config.model_name} not in supported models. Using default: {self.DEFAULT_MODEL}"
            )
            self.config.model_name = self.DEFAULT_MODEL

        # Initialize Mistral client
        self.client = Mistral(api_key=self.api_key)
        logger.success(
            f"Mistral client initialized with model: {self.config.model_name}"
        )

    @retry_on_failure(max_retries=3, delay=1.0)
    def generate(
        self, prompt: str, system_prompt: Optional[str] = None, **kwargs
    ) -> LLMResponse:
        """
        Generate text from a prompt using Mistral AI.

        Args:
            prompt: The user prompt/question
            system_prompt: Optional system instruction to guide model behavior
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            LLMResponse containing generated text and metadata

        Raises:
            LLMRateLimitError: If rate limit is exceeded
            LLMTimeoutError: If request times out
            LLMAPIError: For other API errors
            LLMException: For unexpected errors
        """
        try:
            # Build messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            # Extract parameters
            temperature = kwargs.get("temperature", self.config.temperature)
            max_tokens = kwargs.get("max_tokens", self.config.max_tokens)
            top_p = kwargs.get("top_p", self.config.top_p)

            # Call Mistral API
            response = self.client.chat.complete(
                model=self.config.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
            )

            # Extract response content
            content = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason

            # Extract token usage
            tokens_used = None
            if hasattr(response, "usage") and response.usage:
                tokens_used = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            return LLMResponse(
                content=content,
                model=self.config.model_name,
                provider="mistral",
                tokens_used=tokens_used,
                finish_reason=finish_reason,
                metadata={
                    "response_id": response.id if hasattr(response, "id") else None
                },
            )

        except Exception as e:
            error_str = str(e).lower()

            # Categorize error
            if "rate" in error_str or "429" in error_str:
                raise LLMRateLimitError(
                    "Mistral API rate limit exceeded",
                    provider="mistral",
                    retry_after=60,
                )
            elif "timeout" in error_str or "timed out" in error_str:
                raise LLMTimeoutError(
                    "Mistral API request timed out",
                    provider="mistral",
                    timeout=self.config.timeout,
                )
            elif "unauthorized" in error_str or "401" in error_str:
                raise LLMAPIError(
                    "Invalid Mistral API key", provider="mistral", status_code=401
                )
            elif "connection" in error_str:
                raise LLMConnectionError(
                    "Failed to connect to Mistral API",
                    provider="mistral",
                    original_error=e,
                )
            else:
                raise LLMException(f"Mistral API error: {str(e)}", provider="mistral")

    @retry_on_failure(max_retries=3, delay=1.0)
    def generate_with_history(
        self, messages: List[Dict[str, str]], **kwargs
    ) -> LLMResponse:
        """
        Generate text with conversation history.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
                     Roles can be 'system', 'user', or 'assistant'
            **kwargs: Additional parameters

        Returns:
            LLMResponse containing generated text and metadata

        Raises:
            LLMRateLimitError: If rate limit is exceeded
            LLMTimeoutError: If request times out
            LLMAPIError: For other API errors
        """
        try:
            # Extract parameters
            temperature = kwargs.get("temperature", self.config.temperature)
            max_tokens = kwargs.get("max_tokens", self.config.max_tokens)
            top_p = kwargs.get("top_p", self.config.top_p)

            # Call Mistral API with message history
            response = self.client.chat.complete(
                model=self.config.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
            )

            # Extract response
            content = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason

            # Extract token usage
            tokens_used = None
            if hasattr(response, "usage") and response.usage:
                tokens_used = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            return LLMResponse(
                content=content,
                model=self.config.model_name,
                provider="mistral",
                tokens_used=tokens_used,
                finish_reason=finish_reason,
                metadata={
                    "response_id": response.id if hasattr(response, "id") else None
                },
            )

        except Exception as e:
            error_str = str(e).lower()

            if "rate" in error_str or "429" in error_str:
                raise LLMRateLimitError(
                    "Mistral API rate limit exceeded",
                    provider="mistral",
                    retry_after=60,
                )
            elif "timeout" in error_str:
                raise LLMTimeoutError(
                    "Mistral API request timed out",
                    provider="mistral",
                    timeout=self.config.timeout,
                )
            elif "unauthorized" in error_str or "401" in error_str:
                raise LLMAPIError(
                    "Invalid Mistral API key", provider="mistral", status_code=401
                )
            else:
                raise LLMException(f"Mistral API error: {str(e)}", provider="mistral")

    def is_available(self) -> bool:
        """
        Check if Mistral API is available.

        Returns:
            True if API is accessible, False otherwise
        """
        try:
            # Test with minimal request
            _ = self.client.chat.complete(
                model=self.config.model_name,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5,
            )
            return True
        except Exception as e:
            logger.error(f"Mistral API availability check failed: {str(e)}")
            return False

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model.

        Returns:
            Dictionary with model information
        """
        return {
            "model": self.config.model_name,
            "provider": "mistral",
            "max_context": self.SUPPORTED_MODELS.get(self.config.model_name, 128000),
            "supports_streaming": True,
            "supports_function_calling": True,
            "supports_json_mode": True,
        }


# Test code
if __name__ == "__main__":
    import sys

    # Get API key from environment
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        logger.error("MISTRAL_API_KEY not found in environment")
        sys.exit(1)

    try:
        # Initialize client
        client = MistralClient(api_key=api_key)

        # Test 1: Simple generation
        logger.info("Test 1: Simple generation")
        response = client.generate(
            "Explain HTN planning in AI in 2 sentences.", max_tokens=100
        )
        logger.info(f"Generated {len(response.content)} characters")
        logger.info(f"Response: {response.content}")
        logger.info(f"Model: {response.model}")
        logger.info(f"Tokens: {response.tokens_used}")

        # Test 2: Chat with history
        logger.info("\nTest 2: Chat with history")
        messages = [
            {"role": "user", "content": "What is 2 + 2?"},
            {"role": "assistant", "content": "2 + 2 = 4."},
            {"role": "user", "content": "What about 3 + 3?"},
        ]
        chat_response = client.generate_with_history(messages, max_tokens=50)
        logger.info(f"Chat response: {chat_response.content}")

        # Test 3: Check availability
        logger.info("\nTest 3: Availability check")
        available = client.is_available()
        logger.info(f"Mistral available: {available}")

        # Test 4: Get model info
        logger.info("\nTest 4: Model info")
        info = client.get_model_info()
        logger.info(f"Model info: {info}")

        logger.success("All tests passed!")

    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        sys.exit(1)
