"""
Cohere LLM Client
=================

Client for Cohere's enterprise-grade LLM API.
Uses the cohere Python SDK.

Features:
- Command family models (Command A, Command R+, Command R)
- Multilingual support (23+ languages)
- Enterprise-grade reliability
- Free trial tier available

Author: HTN Planner Team
Date: October 8, 2025
"""

import os
from typing import List, Dict, Any, Optional
import cohere
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
        retry_on_failure
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
        retry_on_failure
    )


class CohereClient(BaseLLMClient):
    """
    Client for Cohere API.
    
    Supports multiple Command models including:
    - command-a-03-2025 (latest, most performant, 256k context)
    - command-r7b-12-2024 (small, fast, 128k context)
    - command-r-08-2024 (balanced, 128k context)
    - command-r-plus-08-2024 (powerful, 128k context)
    
    Usage:
        client = CohereClient(api_key="your-key", config=LLMConfig(model_name="command-a-03-2025"))
        response = client.generate("Explain HTN planning")
    """
    
    DEFAULT_MODEL = "command-a-03-2025"
    
    # Cohere models and their context windows
    SUPPORTED_MODELS = {
        "command-a-03-2025": 256000,
        "command-r7b-12-2024": 128000,
        "command-r-08-2024": 128000,
        "command-r-plus-08-2024": 128000,
        "command-r": 128000,  # Alias for command-r-08-2024
        "command-r-plus": 128000,  # Alias for command-r-plus-08-2024
    }
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        config: Optional[LLMConfig] = None
    ):
        """
        Initialize Cohere client.
        
        Args:
            api_key: Cohere API key (or set COHERE_API_KEY env var)
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
            self.api_key = os.getenv("COHERE_API_KEY")
        
        if not self.api_key:
            raise ValueError(
                "Cohere API key not provided. Set COHERE_API_KEY environment variable "
                "or pass api_key to constructor."
            )
        
        # Validate model
        if self.config.model_name not in self.SUPPORTED_MODELS:
            logger.warning(
                f"Model {self.config.model_name} not in known models. "
                f"Supported: {list(self.SUPPORTED_MODELS.keys())}"
            )
        
        # Initialize Cohere client (v2 API)
        try:
            self.client = cohere.ClientV2(api_key=self.api_key)
            logger.success(f"Cohere client initialized with model: {self.config.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Cohere client: {e}")
            raise LLMConnectionError(
                f"Failed to connect to Cohere API: {str(e)}",
                provider="cohere",
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
        Generate text completion from Cohere.
        
        Args:
            prompt: The main prompt/query
            system_prompt: Optional system instructions
            **kwargs: Additional Cohere-specific parameters
        
        Returns:
            LLMResponse with generated content
        """
        try:
            # Build messages list
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            logger.debug(f"Generating with Cohere ({self.config.model_name}): {prompt[:100]}...")
            
            # Call Cohere API (v2)
            response = self.client.chat(
                model=self.config.model_name,
                messages=messages,
                temperature=kwargs.get("temperature", self.config.temperature),
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                p=kwargs.get("top_p", self.config.top_p),
            )
            
            # Extract response content
            content = None
            if response.message and response.message.content:
                first_content = response.message.content[0]
                if hasattr(first_content, 'text'):
                    content = first_content.text
            if content is None:
                raise LLMAPIError(
                    "Cohere returned empty response",
                    provider="cohere",
                    status_code=None
                )
            
            finish_reason = response.finish_reason
            
            # Get token usage
            tokens_used = None
            if hasattr(response, "usage") and response.usage:
                tokens_used = {
                    "input_tokens": response.usage.tokens.input_tokens,
                    "output_tokens": response.usage.tokens.output_tokens,
                    "total_tokens": response.usage.tokens.input_tokens + response.usage.tokens.output_tokens,
                }
            
            logger.success(f"Cohere generated {len(content)} characters")
            
            return LLMResponse(
                content=content,
                model=self.config.model_name,
                provider="cohere",
                tokens_used=tokens_used,
                finish_reason=finish_reason,
                metadata={
                    "response_id": response.id,
                }
            )
            
        except Exception as e:
            # Categorize errors
            error_msg = str(e).lower()
            
            if "rate" in error_msg or "429" in error_msg or "too many" in error_msg:
                raise LLMRateLimitError(
                    "Cohere rate limit exceeded",
                    provider="cohere",
                    retry_after=60
                )
            elif "timeout" in error_msg:
                raise LLMTimeoutError(
                    f"Cohere request timed out: {str(e)}",
                    provider="cohere",
                    timeout=self.config.timeout
                )
            elif "api" in error_msg or "key" in error_msg or "auth" in error_msg:
                raise LLMAPIError(
                    f"Cohere API error: {str(e)}",
                    provider="cohere",
                    status_code=None
                )
            else:
                raise LLMException(
                    f"Cohere error: {str(e)}",
                    provider="cohere"
                )
    
    @retry_on_failure(max_retries=3, delay=1.0)
    def generate_with_history(
        self, 
        messages: List[Dict[str, str]], 
        **kwargs
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
            logger.debug(f"Generating with Cohere chat ({len(messages)} messages)")
            
            # Call Cohere API with chat history (v2)
            response: NonStreamedChatResponse = self.client.chat(
                model=self.config.model_name,
                messages=messages,
                temperature=kwargs.get("temperature", self.config.temperature),
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                p=kwargs.get("top_p", self.config.top_p),
            )
            
            # Extract response content
            content = response.message.content[0].text if response.message.content else None
            if content is None:
                raise LLMAPIError(
                    "Cohere returned empty response",
                    provider="cohere",
                    status_code=None
                )
            
            finish_reason = response.finish_reason
            
            # Get token usage
            tokens_used = None
            if hasattr(response, "usage") and response.usage:
                tokens_used = {
                    "input_tokens": response.usage.tokens.input_tokens,
                    "output_tokens": response.usage.tokens.output_tokens,
                    "total_tokens": response.usage.tokens.input_tokens + response.usage.tokens.output_tokens,
                }
            
            return LLMResponse(
                content=content,
                model=self.config.model_name,
                provider="cohere",
                tokens_used=tokens_used,
                finish_reason=finish_reason,
                metadata={
                    "response_id": response.id,
                }
            )
            
        except Exception as e:
            error_msg = str(e).lower()
            
            if "rate" in error_msg or "429" in error_msg or "too many" in error_msg:
                raise LLMRateLimitError(
                    "Cohere rate limit exceeded",
                    provider="cohere",
                    retry_after=60
                )
            elif "timeout" in error_msg:
                raise LLMTimeoutError(
                    f"Cohere request timed out: {str(e)}",
                    provider="cohere",
                    timeout=self.config.timeout
                )
            else:
                raise LLMException(
                    f"Cohere error: {str(e)}",
                    provider="cohere"
                )
    
    def is_available(self) -> bool:
        """
        Check if Cohere service is available.
        
        Returns:
            True if service is accessible
        """
        try:
            # Simple test request
            response = self.client.chat(
                model=self.config.model_name,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5,
            )
            return response.message.content[0].text is not None
        except Exception as e:
            logger.error(f"Cohere availability check failed: {e}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model."""
        return {
            "model": self.config.model_name,
            "provider": "cohere",
            "max_context": self.SUPPORTED_MODELS.get(self.config.model_name, "unknown"),
            "supports_streaming": True,
            "supports_function_calling": True,
            "supports_multilingual": True,
        }


# Test code
if __name__ == "__main__":
    # Test Cohere client
    try:
        client = CohereClient()
        
        # Test single generation
        response = client.generate(
            "What is HTN planning in AI? Answer in 2 sentences.",
            system_prompt="You respond concisely."
        )
        print(f"\nResponse: {response.content}")
        print(f"Model: {response.model}")
        print(f"Tokens: {response.tokens_used}")
        
        # Test with history
        chat_response = client.generate_with_history([
            {"role": "system", "content": "You are a math tutor."},
            {"role": "user", "content": "What is 2+2?"},
        ])
        print(f"\nChat response: {chat_response.content}")
        
        # Test availability
        print(f"\nCohere available: {client.is_available()}")
        print(f"Model info: {client.get_model_info()}")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise
