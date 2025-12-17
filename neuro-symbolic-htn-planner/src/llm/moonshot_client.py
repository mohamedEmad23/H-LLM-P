"""
Moonshot Kimi K2 LLM Client
============================

Client for Moonshot AI's Kimi K2 model API.
Uses OpenAI SDK with custom base_url (OpenAI-compatible API).

Features:
- OpenAI-compatible API
- Kimi K2 model family support (kimi-k2-turbo-preview, kimi-k2-0905-preview, etc.)
- Large context windows (up to 128k tokens)
- Competitive pricing and rate limits

Documentation: https://platform.moonshot.ai/docs/api/chat

Author: HTN Planner Team
Date: December 15, 2025
"""

import os
from typing import List, Dict, Any, Optional
from openai import OpenAI
from openai.types.chat import ChatCompletion
from loguru import logger

try:
    from .local_llm_interface import (
        BaseLLMClient,
        LLMResponse,
        LLMConfig,
        LLMException,
        LLMAPIError,
        LLMRateLimitError,
        LLMTimeoutError,
        LLMConnectionError,
        retry_on_failure,
    )
except ImportError:
    # For standalone testing
    from local_llm_interface import (
        BaseLLMClient,
        LLMResponse,
        LLMConfig,
        LLMException,
        LLMAPIError,
        LLMRateLimitError,
        LLMTimeoutError,
        LLMConnectionError,
        retry_on_failure,
    )


class MoonshotClient(BaseLLMClient):
    """
    Client for Moonshot AI API - Kimi K2 models.

    Uses OpenAI SDK with custom base_url for compatibility.

    Supports multiple models including:
    - kimi-k2-turbo-preview (recommended, balanced performance)
    - kimi-k2-0905-preview (latest version)
    - kimi-k2-0711-preview
    - kimi-k2-thinking (reasoning model)
    - kimi-k2-thinking-turbo
    - moonshot-v1-8k, moonshot-v1-32k, moonshot-v1-128k

    Usage:
        client = MoonshotClient(api_key="your-key", config=LLMConfig(model_name="kimi-k2-turbo-preview"))
        response = client.generate("Explain HTN planning")
    """

    DEFAULT_MODEL = "kimi-k2-turbo-preview"
    BASE_URL = "https://api.moonshot.ai/v1"

    # Moonshot models and their context windows
    SUPPORTED_MODELS = {
        "kimi-k2-turbo-preview": 128000,
        "kimi-k2-0905-preview": 128000,
        "kimi-k2-0711-preview": 128000,
        "kimi-k2-thinking": 128000,
        "kimi-k2-thinking-turbo": 128000,
        "moonshot-v1-8k": 8192,
        "moonshot-v1-32k": 32768,
        "moonshot-v1-128k": 128000,
        "moonshot-v1-auto": 128000,
        "kimi-latest": 128000,
    }

    def __init__(
        self, api_key: Optional[str] = None, config: Optional[LLMConfig] = None
    ):
        """
        Initialize Moonshot client.

        Args:
            api_key: Moonshot API key (or set MOONSHOT_API_KEY env var)
            config: LLM configuration
        """
        # Set up config with defaults
        if config is None:
            config = LLMConfig(model_name=self.DEFAULT_MODEL)
        elif not config.model_name or config.model_name == "default":
            config.model_name = self.DEFAULT_MODEL

        super().__init__(api_key=api_key, config=config)

        # Get API key from environment if not provided
        if self.api_key is None:
            self.api_key = os.getenv("MOONSHOT_API_KEY")

        if not self.api_key:
            raise ValueError(
                "Moonshot API key not provided. Set MOONSHOT_API_KEY environment variable "
                "or pass api_key to constructor."
            )

        # Validate model
        if self.config.model_name not in self.SUPPORTED_MODELS:
            logger.warning(
                f"Model {self.config.model_name} not in known models. "
                f"Supported: {list(self.SUPPORTED_MODELS.keys())}"
            )

        # Initialize OpenAI client with Moonshot base URL
        try:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.BASE_URL,
            )
            logger.success(
                f"Moonshot client initialized with model: {self.config.model_name}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Moonshot client: {e}")
            raise LLMConnectionError(
                f"Failed to connect to Moonshot API: {str(e)}",
                provider="moonshot",
                original_error=e,
            )

    @retry_on_failure(max_retries=3, delay=1.0)
    def generate(
        self, prompt: str, system_prompt: Optional[str] = None, **kwargs
    ) -> LLMResponse:
        """
        Generate text completion from Moonshot.

        Args:
            prompt: The main prompt/query
            system_prompt: Optional system instructions
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            LLMResponse with generated content
        """
        try:
            # Build messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            logger.debug(
                f"Generating with Moonshot ({self.config.model_name}): {prompt[:100]}..."
            )

            # Call Moonshot API (OpenAI-compatible)
            response: ChatCompletion = self.client.chat.completions.create(
                model=self.config.model_name,
                messages=messages,
                temperature=kwargs.get("temperature", self.config.temperature),
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                top_p=kwargs.get("top_p", self.config.top_p),
                stream=False,
            )

            # Extract response
            content = response.choices[0].message.content
            if content is None:
                raise LLMAPIError(
                    "Moonshot returned empty response", provider="moonshot", status_code=None
                )

            finish_reason = response.choices[0].finish_reason

            # Get token usage
            tokens_used = None
            if hasattr(response, "usage") and response.usage:
                tokens_used = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            logger.success(f"Moonshot generated {len(content)} characters")

            return LLMResponse(
                content=content,
                model=self.config.model_name,
                provider="moonshot",
                tokens_used=tokens_used,
                finish_reason=finish_reason,
                metadata={
                    "response_id": response.id,
                    "created": response.created,
                    "system_fingerprint": getattr(response, "system_fingerprint", None),
                },
            )

        except Exception as e:
            # Categorize errors
            error_msg = str(e).lower()

            if "rate" in error_msg or "429" in error_msg or "rate_limit" in error_msg:
                raise LLMRateLimitError(
                    "Moonshot rate limit exceeded", provider="moonshot", retry_after=60
                )
            elif "timeout" in error_msg:
                raise LLMTimeoutError(
                    f"Moonshot request timed out: {str(e)}",
                    provider="moonshot",
                    timeout=self.config.timeout,
                )
            elif "api" in error_msg or "key" in error_msg or "auth" in error_msg or "401" in error_msg:
                raise LLMAPIError(
                    f"Moonshot API error: {str(e)}", provider="moonshot", status_code=None
                )
            else:
                raise LLMException(f"Moonshot error: {str(e)}", provider="moonshot")

    @retry_on_failure(max_retries=3, delay=1.0)
    def generate_with_history(
        self, messages: List[Dict[str, str]], **kwargs
    ) -> LLMResponse:
        """
        Generate response with conversation history.

        Args:
            messages: List of message dicts with 'role' and 'content'
                     Roles: 'system', 'user', 'assistant'
            **kwargs: Additional parameters

        Returns:
            LLMResponse with generated content
        """
        try:
            logger.debug(f"Generating with Moonshot chat ({len(messages)} messages)")

            # Call Moonshot API with chat history
            response: ChatCompletion = self.client.chat.completions.create(
                model=self.config.model_name,
                messages=messages,
                temperature=kwargs.get("temperature", self.config.temperature),
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                top_p=kwargs.get("top_p", self.config.top_p),
                stream=False,
            )

            # Extract response
            content = response.choices[0].message.content
            if content is None:
                raise LLMAPIError(
                    "Moonshot returned empty response", provider="moonshot", status_code=None
                )

            finish_reason = response.choices[0].finish_reason

            # Get token usage
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
                provider="moonshot",
                tokens_used=tokens_used,
                finish_reason=finish_reason,
                metadata={
                    "response_id": response.id,
                    "created": response.created,
                },
            )

        except Exception as e:
            error_msg = str(e).lower()

            if "rate" in error_msg or "429" in error_msg:
                raise LLMRateLimitError(
                    "Moonshot rate limit exceeded", provider="moonshot", retry_after=60
                )
            elif "timeout" in error_msg:
                raise LLMTimeoutError(
                    f"Moonshot request timed out: {str(e)}",
                    provider="moonshot",
                    timeout=self.config.timeout,
                )
            else:
                raise LLMException(f"Moonshot error: {str(e)}", provider="moonshot")

    def is_available(self) -> bool:
        """
        Check if Moonshot service is available.

        Returns:
            True if service is accessible
        """
        try:
            # Simple test request
            response = self.client.chat.completions.create(
                model=self.config.model_name,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5,
            )
            return response.choices[0].message.content is not None
        except Exception as e:
            logger.error(f"Moonshot availability check failed: {e}")
            return False

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model."""
        return {
            "model": self.config.model_name,
            "provider": "moonshot",
            "max_context": self.SUPPORTED_MODELS.get(self.config.model_name, "unknown"),
            "base_url": self.BASE_URL,
            "supports_streaming": True,
            "supports_function_calling": True,
        }


# Test code
if __name__ == "__main__":
    # Test Moonshot client
    try:
        client = MoonshotClient()

        # Test single generation
        response = client.generate(
            "What is HTN planning in AI? Answer in 2 sentences.",
            system_prompt="You are a helpful AI assistant.",
        )
        print(f"\nResponse: {response.content}")
        print(f"Model: {response.model}")
        print(f"Tokens: {response.tokens_used}")

        # Test with history
        chat_response = client.generate_with_history(
            [
                {"role": "system", "content": "You are a math tutor."},
                {"role": "user", "content": "What is 2+2?"},
            ]
        )
        print(f"\nChat response: {chat_response.content}")

        # Test availability
        print(f"\nMoonshot available: {client.is_available()}")
        print(f"Model info: {client.get_model_info()}")

    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise
