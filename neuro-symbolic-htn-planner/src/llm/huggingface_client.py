"""
Hugging Face Inference API Client

Provides access to 1000+ open-source models hosted on Hugging Face.
Supports both serverless inference API (free tier) and dedicated endpoints.

Popular models:
- meta-llama/Llama-3.2-3B-Instruct
- meta-llama/Llama-3.1-8B-Instruct
- mistralai/Mistral-7B-Instruct-v0.3
- Qwen/Qwen2.5-7B-Instruct
- microsoft/Phi-3-mini-4k-instruct

Features:
- Free tier serverless inference
- Chat completion with message history
- Automatic retry with exponential backoff
- Token usage tracking
- Model validation
"""

import os
import requests
from typing import Dict, List, Optional
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


class HuggingFaceClient(BaseLLMClient):
    """
    Client for Hugging Face Inference Providers API.

    Provides access to thousands of open-source models via inference providers.
    Free tier available with rate limits.

    Attributes:
        BASE_URL: Hugging Face Inference Providers endpoint (OpenAI-compatible)
        DEFAULT_MODEL: Default model if none specified
        RECOMMENDED_MODELS: Curated list of high-quality models
    """

    BASE_URL = "https://router.huggingface.co/v1/chat/completions"
    DEFAULT_MODEL = "meta-llama/Llama-3.3-70B-Instruct"

    # Recommended models for HTN planning (sorted by size)
    RECOMMENDED_MODELS = {
        # Small models (fast, lower quality)
        "microsoft/Phi-3.5-mini-instruct": "3.8B - Fast",
        "Qwen/Qwen2.5-7B-Instruct": "7B - Qwen 2.5",
        # Medium models (balanced)
        "meta-llama/Llama-3.1-8B-Instruct": "8B - Llama 3.1",
        "mistralai/Mistral-7B-Instruct-v0.3": "7B - Mistral",
        # Large models (high quality)
        "meta-llama/Llama-3.3-70B-Instruct": "70B - Best (default)",
        "NousResearch/Hermes-3-Llama-3.1-70B": "70B - Reasoning",
    }

    def __init__(
        self, api_key: Optional[str] = None, config: Optional[LLMConfig] = None
    ):
        """
        Initialize Hugging Face client.

        Args:
            api_key: HuggingFace API token (read/write).
                    If not provided, reads from HF_TOKEN or HUGGINGFACE_API_KEY env var
            config: LLM configuration. Uses defaults if not provided

        Raises:
            LLMException: If API key is not found
        """
        self.api_key = (
            api_key or os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY")
        )
        if not self.api_key:
            raise LLMException(
                "Hugging Face API token not found. Set HF_TOKEN or HUGGINGFACE_API_KEY. "
                "Get your token at: https://huggingface.co/settings/tokens"
            )

        self.config = config or LLMConfig(model_name=self.DEFAULT_MODEL)

        # Initialize base class
        super().__init__(api_key=self.api_key, config=self.config)

        logger.success(
            f"Hugging Face client initialized with model: {self.config.model_name}"
        )

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for API requests."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    @retry_on_failure(max_retries=3, delay=2.0)
    def generate(
        self, prompt: str, system_prompt: Optional[str] = None, **kwargs
    ) -> LLMResponse:
        """
        Generate text using Hugging Face Inference Providers API.

        Args:
            prompt: The user prompt/question
            system_prompt: Optional system instruction
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            LLMResponse containing generated text and metadata

        Raises:
            LLMRateLimitError: If rate limit exceeded
            LLMTimeoutError: If request times out
            LLMAPIError: For API errors
        """
        try:
            # Build messages for chat completion
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            # Prepare request payload (OpenAI-compatible format)
            payload = {
                "model": self.config.model_name,
                "messages": messages,
                "temperature": kwargs.get("temperature", self.config.temperature),
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                "top_p": kwargs.get("top_p", self.config.top_p),
                "stream": False,
            }

            # Make API request to chat completions endpoint
            response = requests.post(
                self.BASE_URL,
                headers=self._get_headers(),
                json=payload,
                timeout=self.config.timeout,
            )

            # Handle errors
            if response.status_code != 200:
                self._handle_error(response)

            # Parse response (OpenAI-compatible format)
            result = response.json()

            # Extract generated text from choices
            if "choices" in result and len(result["choices"]) > 0:
                choice = result["choices"][0]
                generated_text = choice.get("message", {}).get("content", "")
                finish_reason = choice.get("finish_reason", "stop")
            else:
                generated_text = str(result)
                finish_reason = "unknown"

            # Extract token usage
            usage = result.get("usage", {})
            tokens_used = {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            }

            return LLMResponse(
                content=generated_text.strip(),
                model=result.get("model", self.config.model_name),
                provider="huggingface",
                tokens_used=tokens_used,
                finish_reason=finish_reason,
                metadata={
                    "response_id": result.get("id"),
                    "created": result.get("created"),
                    "system_fingerprint": result.get("system_fingerprint"),
                },
            )

        except requests.exceptions.Timeout:
            raise LLMTimeoutError(
                "Hugging Face API request timed out",
                provider="huggingface",
                timeout=self.config.timeout,
            )
        except requests.exceptions.ConnectionError as e:
            raise LLMConnectionError(
                "Failed to connect to Hugging Face API",
                provider="huggingface",
                original_error=e,
            )
        except Exception as e:
            if "rate limit" in str(e).lower():
                raise LLMRateLimitError(
                    "Hugging Face API rate limit exceeded",
                    provider="huggingface",
                    retry_after=60,
                )
            error_msg = str(e)
            raise LLMException(
                f"Hugging Face API error: {error_msg}", provider="huggingface"
            )

    def _handle_error(self, response: requests.Response):
        """Handle API error responses."""
        try:
            error_data = response.json()
            error_msg = error_data.get("error", str(error_data))
        except Exception:
            error_msg = response.text

        if response.status_code == 429:
            raise LLMRateLimitError(
                f"Hugging Face rate limit: {error_msg}",
                provider="huggingface",
                retry_after=60,
            )
        elif response.status_code in [401, 403]:
            raise LLMAPIError(
                f"Hugging Face authentication error: {error_msg}",
                provider="huggingface",
                status_code=response.status_code,
            )
        elif response.status_code == 503:
            raise LLMAPIError(
                "Model is loading, please retry in a few seconds",
                provider="huggingface",
                status_code=503,
            )
        else:
            raise LLMAPIError(
                f"Hugging Face API error ({response.status_code}): " f"{error_msg}",
                provider="huggingface",
                status_code=response.status_code,
            )

    @retry_on_failure(max_retries=3, delay=2.0)
    def generate_with_history(
        self, messages: List[Dict[str, str]], **kwargs
    ) -> LLMResponse:
        """
        Generate text with conversation history.

        Args:
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional parameters

        Returns:
            LLMResponse containing generated text
        """
        try:
            # Prepare request payload
            payload = {
                "model": self.config.model_name,
                "messages": messages,
                "temperature": kwargs.get("temperature", self.config.temperature),
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                "top_p": kwargs.get("top_p", self.config.top_p),
                "stream": False,
            }

            response = requests.post(
                self.BASE_URL,
                headers=self._get_headers(),
                json=payload,
                timeout=self.config.timeout,
            )

            if response.status_code != 200:
                self._handle_error(response)

            result = response.json()

            # Extract generated text
            if "choices" in result and len(result["choices"]) > 0:
                generated_text = (
                    result["choices"][0].get("message", {}).get("content", "")
                )
            else:
                generated_text = str(result)

            # Extract token usage
            usage = result.get("usage", {})
            tokens_used = {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            }

            return LLMResponse(
                content=generated_text.strip(),
                model=result.get("model", self.config.model_name),
                provider="huggingface",
                tokens_used=tokens_used,
                finish_reason="stop",
            )

        except Exception as e:
            raise LLMException(f"Hugging Face history generation error: {str(e)}")

    def is_available(self) -> bool:
        """
        Check if the Hugging Face API and model are available.

        Returns:
            True if API is reachable and model is available
        """
        try:
            # Quick health check with minimal payload
            payload = {
                "model": self.config.model_name,
                "messages": [{"role": "user", "content": "test"}],
                "max_tokens": 5,
            }

            response = requests.post(
                self.BASE_URL, headers=self._get_headers(), json=payload, timeout=10
            )

            # 200 = success
            if response.status_code == 200:
                logger.info("Hugging Face API is available")
                return True

            logger.warning(f"Hugging Face API check failed: " f"{response.status_code}")
            return False

        except Exception as e:
            logger.error(f"Hugging Face availability check failed: {e}")
            return False


# Convenience function
def get_recommended_model(size: str = "medium") -> str:
    """
    Get a recommended model based on size preference.

    Args:
        size: One of "small", "medium", "large"

    Returns:
        Model ID string
    """
    recommendations = {
        "small": "meta-llama/Llama-3.2-3B-Instruct",
        "medium": "mistralai/Mistral-7B-Instruct-v0.3",
        "large": "meta-llama/Llama-3.1-70B-Instruct",
    }
    return recommendations.get(size, recommendations["medium"])


if __name__ == "__main__":
    print("=" * 80)
    print("Hugging Face Client - Example Usage")
    print("=" * 80)

    # Show recommended models
    print("\n📚 Recommended Models:")
    print("-" * 80)
    client = HuggingFaceClient.__new__(HuggingFaceClient)
    for model, desc in client.RECOMMENDED_MODELS.items():
        print(f"  • {model}")
        print(f"    {desc}")

    print("\n" + "=" * 80)
    print("💡 Get your free API token at: https://huggingface.co/settings/tokens")
    print("=" * 80)
