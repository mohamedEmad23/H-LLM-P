"""
Groq LLM Client
===============

Client for Groq's fast inference API.
Uses the groq Python SDK.

Features:
- Ultra-fast inference with LPU technology
- Support for multiple open models (LLaMA, Mixtral, etc.)
- OpenAI-compatible API
- Free tier with generous rate limits

Author: HTN Planner Team
Date: October 8, 2025
"""

import os
from typing import List, Dict, Any, Optional
from groq import Groq
from groq.types.chat import ChatCompletion
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


class GroqClient(BaseLLMClient):
    """
    Client for Groq API - Ultra-fast LLM inference.

    Supports multiple open models including:
    - llama-3.3-70b-versatile (recommended, balanced performance)
    - llama-3.1-70b-versatile
    - mixtral-8x7b-32768 (large context window)
    - gemma-7b-it

    Usage:
        client = GroqClient(api_key="your-key", config=LLMConfig(model_name="llama-3.3-70b-versatile"))
        response = client.generate("Explain HTN planning")
    """

    DEFAULT_MODEL = "llama-3.3-70b-versatile"

    # Groq models and their context windows
    SUPPORTED_MODELS = {
        "llama-3.3-70b-versatile": 128000,
        "llama-3.1-70b-versatile": 128000,
        "llama-3.1-8b-instant": 128000,
        "mixtral-8x7b-32768": 32768,
        "gemma-7b-it": 8192,
        "gemma2-9b-it": 8192,
    }

    def __init__(
        self, api_key: Optional[str] = None, config: Optional[LLMConfig] = None
    ):
        """
        Initialize Groq client.

        Args:
            api_key: Groq API key (or set GROQ_API_KEY env var)
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
            self.api_key = os.getenv("GROQ_API_KEY")

        if not self.api_key:
            raise ValueError(
                "Groq API key not provided. Set GROQ_API_KEY environment variable "
                "or pass api_key to constructor."
            )

        # Validate model
        if self.config.model_name not in self.SUPPORTED_MODELS:
            logger.warning(
                f"Model {self.config.model_name} not in known models. "
                f"Supported: {list(self.SUPPORTED_MODELS.keys())}"
            )

        # Initialize Groq client
        try:
            self.client = Groq(api_key=self.api_key)
            logger.success(
                f"Groq client initialized with model: {self.config.model_name}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Groq client: {e}")
            raise LLMConnectionError(
                f"Failed to connect to Groq API: {str(e)}",
                provider="groq",
                original_error=e,
            )

    @retry_on_failure(max_retries=3, delay=1.0)
    def generate(
        self, prompt: str, system_prompt: Optional[str] = None, **kwargs
    ) -> LLMResponse:
        """
        Generate text completion from Groq.

        Args:
            prompt: The main prompt/query
            system_prompt: Optional system instructions
            **kwargs: Additional Groq-specific parameters (temperature, max_tokens, etc.)

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
                f"Generating with Groq ({self.config.model_name}): {prompt[:100]}..."
            )

            # Call Groq API
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
                    "Groq returned empty response", provider="groq", status_code=None
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

            logger.success(f"Groq generated {len(content)} characters")

            return LLMResponse(
                content=content,
                model=self.config.model_name,
                provider="groq",
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

            if "rate" in error_msg or "429" in error_msg:
                raise LLMRateLimitError(
                    "Groq rate limit exceeded", provider="groq", retry_after=60
                )
            elif "timeout" in error_msg:
                raise LLMTimeoutError(
                    f"Groq request timed out: {str(e)}",
                    provider="groq",
                    timeout=self.config.timeout,
                )
            elif "api" in error_msg or "key" in error_msg or "auth" in error_msg:
                raise LLMAPIError(
                    f"Groq API error: {str(e)}", provider="groq", status_code=None
                )
            else:
                raise LLMException(f"Groq error: {str(e)}", provider="groq")

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
            logger.debug(f"Generating with Groq chat ({len(messages)} messages)")

            # Call Groq API with chat history
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
                    "Groq returned empty response", provider="groq", status_code=None
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
                provider="groq",
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
                    "Groq rate limit exceeded", provider="groq", retry_after=60
                )
            elif "timeout" in error_msg:
                raise LLMTimeoutError(
                    f"Groq request timed out: {str(e)}",
                    provider="groq",
                    timeout=self.config.timeout,
                )
            else:
                raise LLMException(f"Groq error: {str(e)}", provider="groq")

    def is_available(self) -> bool:
        """
        Check if Groq service is available.

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
            logger.error(f"Groq availability check failed: {e}")
            return False

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model."""
        return {
            "model": self.config.model_name,
            "provider": "groq",
            "max_context": self.SUPPORTED_MODELS.get(self.config.model_name, "unknown"),
            "supports_streaming": True,
            "supports_function_calling": True,
        }


# Test code
if __name__ == "__main__":
    # Test Groq client
    try:
        client = GroqClient()

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
        print(f"\nGroq available: {client.is_available()}")
        print(f"Model info: {client.get_model_info()}")

    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise
