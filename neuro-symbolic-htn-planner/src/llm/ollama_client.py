"""
Ollama Client for HTN Planner

This module provides an interface to Ollama, a local LLM runtime that allows you to
run large language models locally on your machine.

Documentation: https://ollama.com/
GitHub: https://github.com/ollama/ollama

Key Features:
- Run LLMs locally with full privacy and control
- No API key required
- Support for multiple models (LLaMA, Mistral, CodeLLaMA, etc.)
- Fast inference on consumer hardware
- No rate limits or usage costs

Usage:
    from ollama_client import OllamaClient
    from local_llm_interface import LLMConfig

    # Initialize with local model
    config = LLMConfig(model_name="llama3.1:8b")
    client = OllamaClient(config=config)

    # Generate response
    response = client.generate("Explain HTN planning")
    print(response.content)
"""

import os
from typing import List, Dict, Optional, Any
from loguru import logger

# Handle both standalone and package import
try:
    from .local_llm_interface import (
        BaseLLMClient,
        LLMResponse,
        LLMConfig,
        LLMException,
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
        LLMAPIError,
        LLMTimeoutError,
        LLMConnectionError,
        retry_on_failure,
    )

try:
    import ollama
except ImportError:
    raise ImportError("Ollama package not installed. Install with: pip install ollama")


class OllamaClient(BaseLLMClient):
    """Client for Ollama local LLM runtime."""

    # Default Ollama endpoint
    DEFAULT_HOST = "http://localhost:11434"

    # Popular models (non-exhaustive list)
    POPULAR_MODELS = {
        # LLaMA models
        "llama3.1:8b": "LLaMA 3.1 8B (4.9GB)",
        "llama3.1:70b": "LLaMA 3.1 70B (40GB)",
        "llama3.2:1b": "LLaMA 3.2 1B (1.3GB) - Fast",
        "llama3.2:3b": "LLaMA 3.2 3B (2GB)",
        "llama2:7b": "LLaMA 2 7B (3.8GB)",
        "llama2:13b": "LLaMA 2 13B (7.3GB)",
        # Code models
        "codellama:7b": "Code LLaMA 7B (3.8GB) - Code generation",
        "codellama:13b": "Code LLaMA 13B (7.3GB)",
        "codellama:34b": "Code LLaMA 34B (19GB)",
        # Mistral models
        "mistral:7b": "Mistral 7B (4.1GB)",
        "mistral:7b-instruct": "Mistral 7B Instruct (4.1GB)",
        "mixtral:8x7b": "Mixtral 8x7B (26GB) - Mixture of Experts",
        # Specialized models
        "phi3:mini": "Phi-3 Mini (2.3GB) - Microsoft's small model",
        "gemma:2b": "Gemma 2B (1.4GB) - Google's small model",
        "gemma:7b": "Gemma 7B (4.8GB)",
    }

    def __init__(self, config: Optional[LLMConfig] = None, host: Optional[str] = None):
        """
        Initialize Ollama client.

        Args:
            config: LLM configuration. If None, uses defaults with llama3.1:8b
            host: Ollama server host. If None, uses DEFAULT_HOST (localhost:11434)

        Raises:
            LLMConnectionError: If cannot connect to Ollama server
        """
        # Set default model if not specified
        if config is None:
            config = LLMConfig(model_name="llama3.1:8b")

        super().__init__(config=config)

        # Set Ollama host
        self.host = host or os.getenv("OLLAMA_HOST", self.DEFAULT_HOST)

        # Initialize Ollama client
        try:
            self.client = ollama.Client(host=self.host)

            # Test connection by listing models
            models_response = self.client.list()
            available_models = (
                [m.model for m in models_response.models if m.model]
                if hasattr(models_response, "models")
                else []
            )

            # Check if the requested model is available
            if available_models and not any(
                self.config.model_name in model for model in available_models
            ):
                logger.warning(
                    f"Model {self.config.model_name} not found. "
                    f"Available models: {available_models}. "
                    f"You may need to pull it with: ollama pull {self.config.model_name}"
                )

            logger.success(
                f"Ollama client initialized with model: {self.config.model_name} "
                f"(host: {self.host})"
            )
        except Exception as e:
            raise LLMConnectionError(
                f"Failed to connect to Ollama at {self.host}. "
                f"Make sure Ollama is running (ollama serve). Error: {str(e)}",
                provider="ollama",
                original_error=e,
            )

    @retry_on_failure(max_retries=3, delay=1.0)
    def generate(
        self, prompt: str, system_prompt: Optional[str] = None, **kwargs
    ) -> LLMResponse:
        """
        Generate a response from Ollama.

        Args:
            prompt: The user prompt
            system_prompt: Optional system instructions
            **kwargs: Additional model parameters (temperature, max_tokens, etc.)

        Returns:
            LLMResponse object containing the generated text and metadata

        Raises:
            LLMAPIError: API error
            LLMTimeoutError: Request timeout
            LLMConnectionError: Connection error
        """
        try:
            logger.debug(
                f"Generating with Ollama ({self.config.model_name}): {prompt[:100]}..."
            )

            # Prepare options
            options = {
                "temperature": kwargs.get("temperature", self.config.temperature),
                "num_predict": kwargs.get("max_tokens", self.config.max_tokens),
                "top_p": kwargs.get("top_p", self.config.top_p),
            }

            # Build messages format
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            # Call Ollama API
            response = self.client.chat(
                model=self.config.model_name,
                messages=messages,
                options=options,
                stream=False,
            )

            # Extract response data
            content = response.get("message", {}).get("content", "")

            # Extract token usage if available
            tokens_used = None
            if "eval_count" in response or "prompt_eval_count" in response:
                tokens_used = {
                    "prompt_tokens": response.get("prompt_eval_count", 0),
                    "completion_tokens": response.get("eval_count", 0),
                    "total_tokens": response.get("prompt_eval_count", 0)
                    + response.get("eval_count", 0),
                }

            # Extract performance metrics
            metadata = {
                "model": response.get("model", self.config.model_name),
                "created_at": response.get("created_at"),
                "done": response.get("done", False),
            }

            # Add timing information if available
            if "total_duration" in response:
                metadata["total_duration_ns"] = response["total_duration"]
                metadata["total_duration_s"] = response["total_duration"] / 1e9

            if "load_duration" in response:
                metadata["load_duration_ns"] = response["load_duration"]
                metadata["load_duration_s"] = response["load_duration"] / 1e9

            if "eval_duration" in response:
                metadata["eval_duration_ns"] = response["eval_duration"]
                metadata["eval_duration_s"] = response["eval_duration"] / 1e9

                # Calculate tokens per second
                if tokens_used and tokens_used["completion_tokens"] > 0:
                    metadata["tokens_per_second"] = tokens_used["completion_tokens"] / (
                        response["eval_duration"] / 1e9
                    )

            logger.success(
                f"Ollama generated {len(content)} characters "
                f"({tokens_used['total_tokens'] if tokens_used else '?'} tokens)"
            )

            return LLMResponse(
                content=content,
                model=self.config.model_name,
                provider="ollama",
                tokens_used=tokens_used,
                finish_reason="stop",
                metadata=metadata,
            )

        except Exception as e:
            error_str = str(e).lower()

            # Check for specific error types
            if "connection" in error_str or "refused" in error_str:
                raise LLMConnectionError(
                    f"Failed to connect to Ollama: {str(e)}",
                    provider="ollama",
                    original_error=e,
                )
            elif "timeout" in error_str:
                raise LLMTimeoutError(
                    f"Ollama request timed out: {str(e)}",
                    provider="ollama",
                    timeout=self.config.timeout,
                    original_error=e,
                )
            elif "model" in error_str and "not found" in error_str:
                raise LLMAPIError(
                    f"Model {self.config.model_name} not found. Pull it with: ollama pull {self.config.model_name}",
                    provider="ollama",
                    original_error=e,
                )
            else:
                raise LLMAPIError(
                    f"Ollama error: {str(e)}", provider="ollama", original_error=e
                )

    @retry_on_failure(max_retries=3, delay=1.0)
    def generate_with_history(
        self, messages: List[Dict[str, str]], **kwargs
    ) -> LLMResponse:
        """
        Generate a response with conversation history.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
                     Roles: 'system', 'user', 'assistant'
            **kwargs: Additional model parameters

        Returns:
            LLMResponse object

        Raises:
            Same as generate()
        """
        try:
            logger.debug(f"Generating with Ollama chat ({len(messages)} messages)")

            # Prepare options
            options = {
                "temperature": kwargs.get("temperature", self.config.temperature),
                "num_predict": kwargs.get("max_tokens", self.config.max_tokens),
                "top_p": kwargs.get("top_p", self.config.top_p),
            }

            # Call Ollama API
            response = self.client.chat(
                model=self.config.model_name,
                messages=messages,
                options=options,
                stream=False,
            )

            content = response.get("message", {}).get("content", "")

            # Extract token usage
            tokens_used = None
            if "eval_count" in response or "prompt_eval_count" in response:
                tokens_used = {
                    "prompt_tokens": response.get("prompt_eval_count", 0),
                    "completion_tokens": response.get("eval_count", 0),
                    "total_tokens": response.get("prompt_eval_count", 0)
                    + response.get("eval_count", 0),
                }

            return LLMResponse(
                content=content,
                model=self.config.model_name,
                provider="ollama",
                tokens_used=tokens_used,
                finish_reason="stop",
                metadata={
                    "model": response.get("model"),
                    "created_at": response.get("created_at"),
                },
            )

        except Exception as e:
            error_str = str(e).lower()

            if "connection" in error_str:
                raise LLMConnectionError(
                    f"Failed to connect to Ollama: {str(e)}",
                    provider="ollama",
                    original_error=e,
                )
            elif "timeout" in error_str:
                raise LLMTimeoutError(
                    "Ollama request timed out",
                    provider="ollama",
                    timeout=self.config.timeout,
                    original_error=e,
                )
            else:
                raise LLMAPIError(
                    f"Ollama error: {str(e)}", provider="ollama", original_error=e
                )

    def is_available(self) -> bool:
        """
        Check if Ollama is available and the model is loaded.

        Returns:
            True if Ollama is accessible, False otherwise
        """
        try:
            # Try to list models
            self.client.list()
            return True
        except Exception as e:
            logger.warning(f"Ollama availability check failed: {e}")
            return False

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model.

        Returns:
            Dictionary with model information
        """
        try:
            # Get detailed model info from Ollama
            model_info = self.client.show(self.config.model_name)

            return {
                "provider": "ollama",
                "model": self.config.model_name,
                "host": self.host,
                "description": self.POPULAR_MODELS.get(
                    self.config.model_name, "Local Ollama model"
                ),
                "supports_streaming": True,
                "supports_system_prompt": True,
                "supports_chat": True,
                "model_details": model_info.get("details", {}),
                "model_info": model_info.get("modelinfo", {}),
            }
        except Exception as e:
            logger.warning(f"Failed to get model info: {e}")
            return {
                "provider": "ollama",
                "model": self.config.model_name,
                "host": self.host,
                "description": self.POPULAR_MODELS.get(
                    self.config.model_name, "Local Ollama model"
                ),
                "supports_streaming": True,
                "supports_system_prompt": True,
                "supports_chat": True,
            }

    def list_available_models(self) -> List[str]:
        """
        List all models available in Ollama.

        Returns:
            List of model names
        """
        try:
            models_response = self.client.list()
            return (
                [m.model for m in models_response.models if m.model]
                if hasattr(models_response, "models")
                else []
            )
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []


# Test code
if __name__ == "__main__":
    logger.info("Testing Ollama Client")

    try:
        # Initialize client
        config = LLMConfig(
            model_name="llama3.1:8b",
            temperature=0.7,
            max_tokens=150,
        )

        client = OllamaClient(config=config)

        # Test 0: List available models
        logger.info("Test 0: List available models")
        models = client.list_available_models()
        print(f"\nAvailable models: {models}")

        # Test 1: Simple generation
        logger.info("\nTest 1: Simple generation")
        response = client.generate("What is HTN planning in AI? Answer in 2 sentences.")
        print(f"\nResponse: {response.content}")
        print(f"Model: {response.model}")
        if response.tokens_used:
            print(f"Tokens: {response.tokens_used}")
        if response.metadata and "tokens_per_second" in response.metadata:
            print(f"Speed: {response.metadata['tokens_per_second']:.2f} tokens/sec")

        # Test 2: With system prompt
        logger.info("\nTest 2: With system prompt")
        response = client.generate(
            "What is 2 + 2?", system_prompt="You are a helpful math tutor. Be concise."
        )
        print(f"\nResponse: {response.content}")

        # Test 3: Chat with history
        logger.info("\nTest 3: Chat with history")
        messages = [
            {"role": "system", "content": "You are a concise assistant."},
            {"role": "user", "content": "What's the capital of France?"},
            {"role": "assistant", "content": "Paris."},
            {"role": "user", "content": "And its population?"},
        ]
        response = client.generate_with_history(messages)
        print(f"\nChat response: {response.content}")

        # Test 4: Model info
        logger.info("\nTest 4: Model info")
        info = client.get_model_info()
        print(f"\nModel info: {info}")

        # Test 5: Availability check
        logger.info("\nTest 5: Availability check")
        available = client.is_available()
        print(f"\nOllama available: {available}")

        logger.success("\n✅ All tests passed!")

    except LLMException as e:
        logger.error(f"Test failed: {e}")
        import traceback

        traceback.print_exc()
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback

        traceback.print_exc()
