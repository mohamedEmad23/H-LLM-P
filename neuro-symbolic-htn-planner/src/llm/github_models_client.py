"""
GitHub Models Client for HTN Planner

This module provides an interface to GitHub Models, which is an AI inference API 
that lets you run various AI models (OpenAI, Meta, DeepSeek, etc.) using GitHub credentials.

Documentation: https://docs.github.com/en/github-models/quickstart
Marketplace: https://github.com/marketplace/models

Key Features:
- Access to multiple model providers (OpenAI, Meta, etc.) through GitHub
- Uses GitHub Personal Access Token (PAT) with 'models' scope
- Built on OpenAI SDK (OpenAI-compatible API)
- No separate authentication per provider needed

Usage:
    from github_models_client import GitHubModelsClient
    from local_llm_interface import LLMConfig
    
    # Initialize with GitHub token
    config = LLMConfig(model_name="openai/gpt-4o")
    client = GitHubModelsClient(api_key="ghp_...", config=config)
    
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
        BaseLLMClient, LLMResponse, LLMConfig,
        LLMException, LLMRateLimitError, LLMAPIError, LLMTimeoutError, LLMConnectionError,
        retry_on_failure
    )
except ImportError:
    from local_llm_interface import (
        BaseLLMClient, LLMResponse, LLMConfig,
        LLMException, LLMRateLimitError, LLMAPIError, LLMTimeoutError, LLMConnectionError,
        retry_on_failure
    )

# Use OpenAI SDK for GitHub Models
from openai import OpenAI
from openai import OpenAIError, RateLimitError, APIError, APITimeoutError, APIConnectionError, AuthenticationError


class GitHubModelsClient(BaseLLMClient):
    """Client for GitHub Models API using OpenAI SDK."""
    
    # GitHub Models endpoint
    ENDPOINT = "https://models.github.ai/inference"
    
    # Supported models (non-exhaustive list)
    SUPPORTED_MODELS = {
        # OpenAI models
        "openai/gpt-4o": "GPT-4o (128k context)",
        "openai/gpt-4o-mini": "GPT-4o Mini (128k context)",
        "openai/gpt-4.1": "GPT-4.1",
        "openai/gpt-3.5-turbo": "GPT-3.5 Turbo (16k context)",
        
        # Meta Llama models
        "meta-llama/Llama-3.3-70B-Instruct": "Llama 3.3 70B (128k context)",
        "meta-llama/Llama-3.2-11B-Vision-Instruct": "Llama 3.2 11B Vision (128k context)",
        "meta-llama/Llama-3.2-90B-Vision-Instruct": "Llama 3.2 90B Vision (128k context)",
        
        # Mistral models
        "mistralai/Mistral-7B-Instruct-v0.1": "Mistral 7B Instruct",
        "mistralai/Mistral-Nemo-12B-Instruct-2407": "Mistral Nemo 12B (128k context)",
        
        # DeepSeek models
        "deepseek-ai/DeepSeek-R1": "DeepSeek R1",
        "deepseek-ai/DeepSeek-V3": "DeepSeek V3",
    }
    
    def __init__(self, api_key: Optional[str] = None, config: Optional[LLMConfig] = None):
        """
        Initialize GitHub Models client.
        
        Args:
            api_key: GitHub Personal Access Token (PAT) with 'models' scope.
                    If None, reads from GITHUB_TOKEN environment variable.
            config: LLM configuration. If None, uses defaults.
        
        Raises:
            LLMConnectionError: If API key is missing
        """
        super().__init__(api_key=api_key, config=config)
        
        # Get API key
        self.api_key = api_key or os.getenv("GITHUB_TOKEN")
        if not self.api_key:
            raise LLMConnectionError(
                "GitHub token is required. Set GITHUB_TOKEN environment variable or pass api_key parameter.",
                provider="github-models"
            )
        
        # Initialize OpenAI client with GitHub endpoint
        try:
            self.client = OpenAI(
                base_url=self.ENDPOINT,
                api_key=self.api_key,
                timeout=self.config.timeout,
            )
            logger.success(f"GitHub Models client initialized with model: {self.config.model_name}")
        except Exception as e:
            raise LLMConnectionError(
                f"Failed to initialize GitHub Models client: {str(e)}",
                provider="github-models",
                original_error=e
            )
    
    @retry_on_failure(max_retries=3, delay=1.0)
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a response from GitHub Models.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system instructions
            **kwargs: Additional model parameters (temperature, max_tokens, etc.)
        
        Returns:
            LLMResponse object containing the generated text and metadata
        
        Raises:
            LLMRateLimitError: Rate limit exceeded
            LLMAPIError: API error
            LLMTimeoutError: Request timeout
            LLMConnectionError: Connection error
        """
        try:
            logger.debug(f"Generating with GitHub Models ({self.config.model_name}): {prompt[:100]}...")
            
            # Build messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            # Prepare parameters
            params = {
                "model": self.config.model_name,
                "messages": messages,
                "temperature": kwargs.get("temperature", self.config.temperature),
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            }
            
            # Add optional parameters
            if self.config.top_p != 1.0:
                params["top_p"] = kwargs.get("top_p", self.config.top_p)
            
            # Call GitHub Models API
            response = self.client.chat.completions.create(**params)
            
            # Extract response data
            content = response.choices[0].message.content or ""
            finish_reason = response.choices[0].finish_reason
            
            # Extract token usage
            tokens_used = None
            if hasattr(response, 'usage') and response.usage:
                tokens_used = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }
            
            logger.success(f"GitHub Models generated {len(content)} characters")
            
            return LLMResponse(
                content=content,
                model=self.config.model_name,
                provider="github-models",
                tokens_used=tokens_used,
                finish_reason=finish_reason,
                metadata={
                    "response_id": response.id,
                    "created": response.created,
                    "model": response.model,
                }
            )
            
        except AuthenticationError as e:
            raise LLMAPIError(
                "GitHub Models authentication failed - check your GitHub PAT",
                provider="github-models",
                status_code=401,
                original_error=e
            )
        except RateLimitError as e:
            raise LLMRateLimitError(
                "GitHub Models rate limit exceeded",
                provider="github-models",
                retry_after=60,
                original_error=e
            )
        except APITimeoutError as e:
            raise LLMTimeoutError(
                f"GitHub Models request timed out: {str(e)}",
                provider="github-models",
                timeout=self.config.timeout,
                original_error=e
            )
        except APIConnectionError as e:
            raise LLMConnectionError(
                f"Failed to connect to GitHub Models: {str(e)}",
                provider="github-models",
                original_error=e
            )
        except APIError as e:
            raise LLMAPIError(
                f"GitHub Models API error: {str(e)}",
                provider="github-models",
                original_error=e
            )
        except Exception as e:
            if isinstance(e, (LLMException, LLMRateLimitError, LLMTimeoutError, LLMAPIError)):
                raise
            raise LLMException(f"GitHub Models error: {str(e)}", provider="github-models", original_error=e)
    
    @retry_on_failure(max_retries=3, delay=1.0)
    def generate_with_history(
        self,
        messages: List[Dict[str, str]],
        **kwargs
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
            logger.debug(f"Generating with GitHub Models chat ({len(messages)} messages)")
            
            # Prepare parameters
            params = {
                "model": self.config.model_name,
                "messages": messages,
                "temperature": kwargs.get("temperature", self.config.temperature),
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            }
            
            if self.config.top_p != 1.0:
                params["top_p"] = kwargs.get("top_p", self.config.top_p)
            
            # Call API
            response = self.client.chat.completions.create(**params)
            
            content = response.choices[0].message.content or ""
            finish_reason = response.choices[0].finish_reason
            
            tokens_used = None
            if hasattr(response, 'usage') and response.usage:
                tokens_used = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }
            
            return LLMResponse(
                content=content,
                model=self.config.model_name,
                provider="github-models",
                tokens_used=tokens_used,
                finish_reason=finish_reason,
                metadata={"response_id": response.id}
            )
            
        except RateLimitError as e:
            raise LLMRateLimitError(
                "GitHub Models rate limit exceeded",
                provider="github-models",
                retry_after=60,
                original_error=e
            )
        except APITimeoutError as e:
            raise LLMTimeoutError(
                f"GitHub Models request timed out",
                provider="github-models",
                timeout=self.config.timeout,
                original_error=e
            )
        except APIError as e:
            raise LLMAPIError(
                f"GitHub Models API error: {str(e)}",
                provider="github-models",
                original_error=e
            )
        except Exception as e:
            if isinstance(e, (LLMException, LLMRateLimitError, LLMTimeoutError, LLMAPIError)):
                raise
            raise LLMException(f"GitHub Models error: {str(e)}", provider="github-models", original_error=e)
    
    def is_available(self) -> bool:
        """
        Check if GitHub Models API is available.
        
        Returns:
            True if API is accessible, False otherwise
        """
        try:
            # Try a minimal completion
            response = self.client.chat.completions.create(
                model=self.config.model_name,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5,
            )
            return True
        except Exception as e:
            logger.warning(f"GitHub Models availability check failed: {e}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model.
        
        Returns:
            Dictionary with model information
        """
        model_desc = self.SUPPORTED_MODELS.get(
            self.config.model_name,
            "Unknown model"
        )
        
        return {
            "provider": "github-models",
            "model": self.config.model_name,
            "description": model_desc,
            "endpoint": self.ENDPOINT,
            "supports_streaming": False,  # Can be implemented if needed
            "supports_system_prompt": True,
            "supports_chat": True,
        }


# Test code
if __name__ == "__main__":
    logger.info("Testing GitHub Models Client")
    
    try:
        # Initialize client
        config = LLMConfig(
            model_name="openai/gpt-4o-mini",  # Use mini for faster/cheaper testing
            temperature=0.7,
            max_tokens=150,
        )
        
        client = GitHubModelsClient(config=config)
        
        # Test 1: Simple generation
        logger.info("Test 1: Simple generation")
        response = client.generate(
            "What is HTN planning in AI? Answer in 2 sentences."
        )
        print(f"\nResponse: {response.content}")
        print(f"Model: {response.model}")
        if response.tokens_used:
            print(f"Tokens: {response.tokens_used}")
        
        # Test 2: With system prompt
        logger.info("\nTest 2: With system prompt")
        response = client.generate(
            "What is 2 + 2?",
            system_prompt="You are a helpful math tutor. Always show your work."
        )
        print(f"\nResponse: {response.content}")
        
        # Test 3: Chat with history
        logger.info("\nTest 3: Chat with history")
        messages = [
            {"role": "system", "content": "You are a concise assistant."},
            {"role": "user", "content": "What's the capital of France?"},
            {"role": "assistant", "content": "Paris."},
            {"role": "user", "content": "And its population?"}
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
        print(f"\nAPI available: {available}")
        
        logger.success("\n✅ All tests passed!")
        
    except LLMException as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
