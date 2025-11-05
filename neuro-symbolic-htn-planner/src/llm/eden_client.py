"""
Eden AI LLM Client Implementation

This module provides a client for interacting with Eden AI's unified LLM API.
Eden AI is a platform that aggregates multiple AI providers into a single API.

Features:
- Access to multiple LLM providers through one API
- Chat completion with message history
- Automatic retry with exponential backoff
- Comprehensive error handling
- Token usage tracking

Example:
    >>> from eden_client import EdenClient
    >>> client = EdenClient(api_key="your-api-key")
    >>> response = client.generate("Explain quantum computing")
    >>> print(response.content)
"""

import json
import os
import requests
from typing import Dict, List, Optional, Any
from loguru import logger

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


class EdenClient(BaseLLMClient):
    """
    Client for Eden AI unified LLM API.

    Eden AI provides access to multiple LLM providers through a single API:
    - OpenAI (GPT-4, GPT-3.5)
    - Anthropic (Claude)
    - Google (Gemini)
    - Mistral
    - Meta (LLaMA)
    - And many more

    Attributes:
        DEFAULT_PROVIDER: The default provider to use
        DEFAULT_MODEL: The default model to use
        BASE_URL: Eden AI API base URL
        api_key: Eden AI API key (JWT token)
        config: LLM configuration settings
    """

    DEFAULT_PROVIDER = "openai"
    DEFAULT_MODEL = "gpt-4o"
    BASE_URL = "https://api.edenai.run/v2"

    # Supported providers and their models
    SUPPORTED_PROVIDERS = {
        "openai": ["gpt-4o", "gpt-4", "gpt-3.5-turbo"],
        "anthropic": ["claude-3-5-sonnet-20241022", "claude-3-opus"],
        "google": ["gemini-2.0-flash-exp", "gemini-1.5-pro"],
        "mistral": ["mistral-large-latest", "mistral-small-latest"],
        "meta": ["llama-3-70b", "llama-3-8b"],
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        config: Optional[LLMConfig] = None,
        provider: Optional[str] = None,
    ):
        """
        Initialize Eden AI client.

        Args:
            api_key: Eden AI API key (JWT token). If not provided, reads from EDEN_API_KEY env var
            config: LLM configuration. Uses defaults if not provided
            provider: LLM provider to use (openai, anthropic, google, etc.)

        Raises:
            LLMException: If API key is not found
        """
        self.api_key = api_key or os.getenv("EDEN_API_KEY")
        if not self.api_key:
            raise LLMException(
                "Eden AI API key not found. Set EDEN_API_KEY environment variable."
            )

        self.provider = provider or self.DEFAULT_PROVIDER
        self.config = config or LLMConfig(model_name=self.DEFAULT_MODEL)

        # Initialize base class (sets provider_name)
        super().__init__(api_key=self.api_key, config=self.config)

        logger.success(
            f"Eden AI client initialized with provider: {self.provider}, model: {self.config.model_name}"
        )

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for Eden AI API requests."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    @retry_on_failure(max_retries=3, delay=1.0)
    def generate(
        self, prompt: str, system_prompt: Optional[str] = None, **kwargs
    ) -> LLMResponse:
        """
        Generate text from a prompt using Eden AI.

        Args:
            prompt: The user prompt/question
            system_prompt: Optional system instruction (used as chatbot_global_action)
            **kwargs: Additional parameters (temperature, max_tokens, provider, etc.)

        Returns:
            LLMResponse containing generated text and metadata

        Raises:
            LLMRateLimitError: If rate limit is exceeded
            LLMTimeoutError: If request times out
            LLMAPIError: For other API errors
            LLMException: For unexpected errors
        """
        try:
            # Build request payload
            payload = {
                "providers": kwargs.get("provider", self.provider),
                "text": prompt,
                "temperature": kwargs.get("temperature", self.config.temperature),
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            }

            # Add system prompt if provided
            if system_prompt:
                payload["chatbot_global_action"] = system_prompt

            # Add model if specified
            if "model" in kwargs:
                payload["model"] = kwargs["model"]
            elif self.config.model_name:
                payload["model"] = self.config.model_name

            # Call Eden AI API
            url = f"{self.BASE_URL}/text/chat"
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=self.config.timeout,
            )

            # Parse response
            if response.status_code != 200:
                self._handle_error(response)

            result = response.json()

            # Extract response from provider result
            provider_result = result.get(self.provider, {})
            content = provider_result.get("generated_text", "")

            # Extract token usage if available
            tokens_used = None
            cost = provider_result.get("cost")
            if cost:
                tokens_used = {
                    "total_tokens": cost,  # Eden AI returns cost, not token count
                }

            return LLMResponse(
                content=content,
                model=self.config.model_name,
                provider=f"eden-ai-{self.provider}",
                tokens_used=tokens_used,
                finish_reason="stop",
                metadata={"cost": cost},
            )

        except requests.exceptions.Timeout:
            raise LLMTimeoutError(
                "Eden AI request timed out",
                provider="eden-ai",
                timeout=self.config.timeout,
            )
        except requests.exceptions.ConnectionError as e:
            raise LLMConnectionError(
                "Failed to connect to Eden AI", provider="eden-ai", original_error=e
            )
        except Exception as e:
            if isinstance(
                e, (LLMException, LLMRateLimitError, LLMTimeoutError, LLMAPIError)
            ):
                raise
            raise LLMException(f"Eden AI error: {str(e)}", provider="eden-ai")

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
            # Extract system prompt and user message
            system_prompt = None
            user_message = None
            previous_history = []

            for msg in messages:
                role = msg.get("role")
                content = msg.get("content")

                if role == "system":
                    system_prompt = content
                elif role == "user":
                    user_message = content
                elif role == "assistant":
                    previous_history.append({"role": "assistant", "message": content})

            if not user_message:
                raise LLMException("No user message found in message history")

            # Build payload
            payload = {
                "providers": kwargs.get("provider", self.provider),
                "text": user_message,
                "temperature": kwargs.get("temperature", self.config.temperature),
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            }

            if system_prompt:
                payload["chatbot_global_action"] = system_prompt

            if previous_history:
                payload["previous_history"] = previous_history

            if "model" in kwargs:
                payload["model"] = kwargs["model"]
            elif self.config.model_name:
                payload["model"] = self.config.model_name

            # Call API
            url = f"{self.BASE_URL}/text/chat"
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=self.config.timeout,
            )

            if response.status_code != 200:
                self._handle_error(response)

            result = response.json()
            provider_result = result.get(self.provider, {})
            content = provider_result.get("generated_text", "")

            tokens_used = None
            cost = provider_result.get("cost")
            if cost:
                tokens_used = {"total_tokens": cost}

            return LLMResponse(
                content=content,
                model=self.config.model_name,
                provider=f"eden-ai-{self.provider}",
                tokens_used=tokens_used,
                finish_reason="stop",
                metadata={"cost": cost},
            )

        except requests.exceptions.Timeout:
            raise LLMTimeoutError(
                "Eden AI request timed out",
                provider="eden-ai",
                timeout=self.config.timeout,
            )
        except requests.exceptions.ConnectionError as e:
            raise LLMConnectionError(
                "Failed to connect to Eden AI", provider="eden-ai", original_error=e
            )
        except Exception as e:
            if isinstance(
                e, (LLMException, LLMRateLimitError, LLMTimeoutError, LLMAPIError)
            ):
                raise
            raise LLMException(f"Eden AI error: {str(e)}", provider="eden-ai")

    def _handle_error(self, response: requests.Response):
        """Handle API errors and raise appropriate exceptions."""
        try:
            error_data = response.json()
            error_message = error_data.get(
                "message", error_data.get("detail", response.text)
            )
        except (json.JSONDecodeError, KeyError):
            error_message = response.text

        if response.status_code == 429:
            raise LLMRateLimitError(
                "Eden AI rate limit exceeded", provider="eden-ai", retry_after=60
            )
        elif response.status_code == 401:
            raise LLMAPIError(
                "Invalid Eden AI API key", provider="eden-ai", status_code=401
            )
        elif response.status_code >= 500:
            raise LLMAPIError(
                f"Eden AI server error: {error_message}",
                provider="eden-ai",
                status_code=response.status_code,
            )
        else:
            raise LLMAPIError(
                f"Eden AI API error: {error_message}",
                provider="eden-ai",
                status_code=response.status_code,
            )

    def is_available(self) -> bool:
        """
        Check if Eden AI API is available.

        Returns:
            True if API is accessible, False otherwise
        """
        try:
            _ = self.generate("test", max_tokens=5)
            return True
        except Exception as e:
            logger.error(f"Eden AI availability check failed: {str(e)}")
            return False

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model.

        Returns:
            Dictionary with model information
        """
        return {
            "model": self.config.model_name,
            "provider": f"eden-ai-{self.provider}",
            "unified_api": True,
            "supports_streaming": False,
            "supports_multiple_providers": True,
            "available_providers": list(self.SUPPORTED_PROVIDERS.keys()),
        }


# Test code
if __name__ == "__main__":
    import sys

    # Get API key from environment
    api_key = os.getenv("EDEN_API_KEY")
    if not api_key:
        logger.error("EDEN_API_KEY not found in environment")
        sys.exit(1)

    try:
        # Initialize client with OpenAI provider
        client = EdenClient(api_key=api_key, provider="openai")

        # Test 1: Simple generation
        logger.info("Test 1: Simple generation")
        response = client.generate(
            "Explain HTN planning in AI in 2 sentences.", max_tokens=100, model="gpt-4o"
        )
        logger.info(f"Generated {len(response.content)} characters")
        logger.info(f"Response: {response.content}")
        logger.info(f"Model: {response.model}")
        logger.info(f"Provider: {response.provider}")
        logger.info(f"Tokens/Cost: {response.tokens_used}")

        # Test 2: Chat with history
        logger.info("\nTest 2: Chat with history")
        messages = [
            {"role": "user", "content": "What is 2 + 2?"},
            {"role": "assistant", "content": "2 + 2 = 4."},
            {"role": "user", "content": "What about 3 + 3?"},
        ]
        chat_response = client.generate_with_history(
            messages, max_tokens=50, model="gpt-4o"
        )
        logger.info(f"Chat response: {chat_response.content}")

        # Test 3: Check availability
        logger.info("\nTest 3: Availability check")
        available = client.is_available()
        logger.info(f"Eden AI available: {available}")

        # Test 4: Get model info
        logger.info("\nTest 4: Model info")
        info = client.get_model_info()
        logger.info(f"Model info: {info}")

        logger.success("All tests passed!")

    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
