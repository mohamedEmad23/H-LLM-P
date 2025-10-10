"""
GitHub Models Client for HTN Planner (Azure AI SDK)

This module provides an interface to GitHub Models using the Azure AI Inference SDK.
GitHub Models provides access to GPT-5, DeepSeek V3, Llama 4, and other models.

Documentation: https://docs.github.com/en/github-models/quickstart
Marketplace: https://github.com/marketplace/models

Key Features:
- Uses Azure AI Inference SDK (standardized across all models)
- GitHub Personal Access Token (classic or fine-grained with 'models' scope)
- Support for GPT-5, DeepSeek V3, Llama 4 Scout
- Consistent API across all model providers

Usage:
    from github_models_client import GitHubModelsClient
    from local_llm_interface import LLMConfig
    
    # Initialize with GitHub token
    config = LLMConfig(model_name="openai/gpt-5")
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

# Use Azure AI Inference SDK for GitHub Models
try:
    from azure.ai.inference import ChatCompletionsClient
    from azure.ai.inference.models import SystemMessage, UserMessage, AssistantMessage
    from azure.core.credentials import AzureKeyCredential
    from azure.core.exceptions import (
        HttpResponseError, 
        ServiceRequestError,
        ServiceResponseError
    )
except ImportError as e:
    raise ImportError(
        "Azure AI Inference SDK is required for GitHub Models. "
        "Install it with: pip install azure-ai-inference"
    ) from e


class GitHubModelsClient(BaseLLMClient):
    """Client for GitHub Models API using Azure AI Inference SDK."""
    
    # GitHub Models endpoint
    ENDPOINT = "https://models.github.ai/inference"
    
    # Supported models (GitHub Marketplace - verified as of Oct 2025)
    SUPPORTED_MODELS = {
        # OpenAI models (Azure hosted)
        "openai/gpt-5": "GPT-5 (Latest, Azure hosted)",
        
        # DeepSeek models
        "deepseek/DeepSeek-V3-0324": "DeepSeek V3 (671B MoE, March 2024)",
        
        # Meta Llama models
        "meta/Llama-4-Scout-17B-16E-Instruct": "Llama 4 Scout (17B, 16 Experts, Multimodal)",
    }
    
    def __init__(self, api_key: Optional[str] = None, config: Optional[LLMConfig] = None):
        """
        Initialize GitHub Models client using Azure AI Inference SDK.
        
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
        
        # Initialize Azure AI Inference client with GitHub Models endpoint
        try:
            self.client = ChatCompletionsClient(
                endpoint=self.ENDPOINT,
                credential=AzureKeyCredential(self.api_key)
            )
            logger.success(f"GitHub Models client (Azure SDK) initialized with model: {self.config.model_name}")
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
            
            # Build messages using Azure message objects
            messages = []
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            messages.append(UserMessage(content=prompt))
            
            # Prepare parameters
            params = {
                "messages": messages,
                "model": self.config.model_name,
            }
            
            # GPT-5 has specific requirements: only supports temperature=1.0
            # and uses max_completion_tokens instead of max_tokens
            if self.config.model_name.startswith("openai/gpt-5"):
                # GPT-5 only supports temperature=1.0 (default)
                params["temperature"] = 1.0
                params["model_extras"] = {
                    "max_completion_tokens": kwargs.get("max_tokens", self.config.max_tokens)
                }
            elif self.config.model_name.startswith("openai/gpt-4o"):
                params["temperature"] = kwargs.get("temperature", self.config.temperature)
                params["model_extras"] = {
                    "max_completion_tokens": kwargs.get("max_tokens", self.config.max_tokens)
                }
            else:
                # Other models support standard parameters
                params["temperature"] = kwargs.get("temperature", self.config.temperature)
                params["max_tokens"] = kwargs.get("max_tokens", self.config.max_tokens)
            
            # Add optional parameters
            if self.config.top_p != 1.0:
                params["top_p"] = kwargs.get("top_p", self.config.top_p)
            
            # Call GitHub Models API using Azure SDK
            response = self.client.complete(**params)
            
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
            
        except HttpResponseError as e:
            # Handle authentication errors (401)
            if e.status_code == 401:
                raise LLMAPIError(
                    "GitHub Models authentication failed - check your GitHub PAT",
                    provider="github-models",
                    status_code=401,
                    original_error=e
                )
            # Handle rate limit errors (429)
            elif e.status_code == 429:
                raise LLMRateLimitError(
                    "GitHub Models rate limit exceeded",
                    provider="github-models",
                    retry_after=60,
                    original_error=e
                )
            # Generic HTTP errors
            else:
                raise LLMAPIError(
                    f"GitHub Models API error (status {e.status_code}): {str(e)}",
                    provider="github-models",
                    status_code=e.status_code,
                    original_error=e
                )
        except ServiceRequestError as e:
            raise LLMTimeoutError(
                f"GitHub Models request timed out: {str(e)}",
                provider="github-models",
                timeout=self.config.timeout,
                original_error=e
            )
        except ServiceResponseError as e:
            raise LLMConnectionError(
                f"Failed to connect to GitHub Models: {str(e)}",
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
            
            # Convert message dicts to Azure message objects
            azure_messages = []
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                if role == "system":
                    azure_messages.append(SystemMessage(content=content))
                elif role == "assistant":
                    azure_messages.append(AssistantMessage(content=content))
                else:  # user or any other role
                    azure_messages.append(UserMessage(content=content))
            
            # Prepare parameters
            params = {
                "messages": azure_messages,
                "model": self.config.model_name,
            }
            
            # GPT-5 has specific requirements: only supports temperature=1.0
            # and uses max_completion_tokens instead of max_tokens
            if self.config.model_name.startswith("openai/gpt-5"):
                # GPT-5 only supports temperature=1.0 (default)
                params["temperature"] = 1.0
                params["model_extras"] = {
                    "max_completion_tokens": kwargs.get("max_tokens", self.config.max_tokens)
                }
            elif self.config.model_name.startswith("openai/gpt-4o"):
                params["temperature"] = kwargs.get("temperature", self.config.temperature)
                params["model_extras"] = {
                    "max_completion_tokens": kwargs.get("max_tokens", self.config.max_tokens)
                }
            else:
                # Other models support standard parameters
                params["temperature"] = kwargs.get("temperature", self.config.temperature)
                params["max_tokens"] = kwargs.get("max_tokens", self.config.max_tokens)
            
            if self.config.top_p != 1.0:
                params["top_p"] = kwargs.get("top_p", self.config.top_p)
            
            # Call API using Azure SDK
            response = self.client.complete(**params)
            
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
            
        except HttpResponseError as e:
            if e.status_code == 429:
                raise LLMRateLimitError(
                    "GitHub Models rate limit exceeded",
                    provider="github-models",
                    retry_after=60,
                    original_error=e
                )
            else:
                raise LLMAPIError(
                    f"GitHub Models API error (status {e.status_code}): {str(e)}",
                    provider="github-models",
                    status_code=e.status_code,
                    original_error=e
                )
        except ServiceRequestError as e:
            raise LLMTimeoutError(
                f"GitHub Models request timed out",
                provider="github-models",
                timeout=self.config.timeout,
                original_error=e
            )
        except ServiceResponseError as e:
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
            # Try a minimal completion using Azure SDK
            params = {
                "messages": [UserMessage(content="Hi")],
                "model": self.config.model_name,
            }
            
            # Use correct token parameter based on model
            if self.config.model_name.startswith("openai/gpt-5") or self.config.model_name.startswith("openai/gpt-4o"):
                params["model_extras"] = {"max_completion_tokens": 5}
            else:
                params["max_tokens"] = 5
            
            response = self.client.complete(**params)
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


# Test code - Tests all 3 GitHub Marketplace models
if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    
    # Load environment variables from .env
    load_dotenv()
    
    # Define the 3 models to test
    MODELS_TO_TEST = [
        "openai/gpt-5",                              # GPT-5 (Latest OpenAI)
        "deepseek/DeepSeek-V3-0324",                 # DeepSeek V3 (671B MoE)
        "meta/Llama-4-Scout-17B-16E-Instruct",       # Llama 4 Scout (Multimodal)
    ]
    
    # Allow user to specify which model to test
    selected_model = None
    if len(sys.argv) > 1:
        selected_model = sys.argv[1]
        if selected_model not in MODELS_TO_TEST:
            logger.error(f"Invalid model: {selected_model}")
            logger.info(f"Available models: {', '.join(MODELS_TO_TEST)}")
            sys.exit(1)
        models_to_test = [selected_model]
    else:
        models_to_test = MODELS_TO_TEST
    
    logger.info(f"Testing GitHub Models Client (Azure SDK) - {len(models_to_test)} model(s)")
    
    success_count = 0
    fail_count = 0
    
    for model_name in models_to_test:
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing model: {model_name}")
        logger.info(f"{'='*60}")
        
        try:
            # Initialize client
            config = LLMConfig(
                model_name=model_name,
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
            
            logger.success(f"✅ All tests passed for {model_name}!")
            success_count += 1
            
        except LLMException as e:
            logger.error(f"❌ Tests failed for {model_name}: {e}")
            fail_count += 1
        except Exception as e:
            logger.error(f"❌ Unexpected error for {model_name}: {e}")
            import traceback
            traceback.print_exc()
            fail_count += 1
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info(f"Test Summary: {success_count} passed, {fail_count} failed")
    logger.info(f"{'='*60}")
    
    if fail_count == 0:
        logger.success("✅ All models working!")
        sys.exit(0)
    else:
        logger.error(f"❌ {fail_count} model(s) failed")
        sys.exit(1)
