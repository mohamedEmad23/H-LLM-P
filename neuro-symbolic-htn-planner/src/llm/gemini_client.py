"""
Google Gemini LLM Client
=========================

Client for Google's Gemini API (AI Studio / free tier).
Uses the google-genai SDK.

Features:
- Free tier access via AI Studio
- Support for Gemini 2.5 Flash and other models
- Native chat format support
- Rate limiting and error handling

Author: HTN Planner Team
Date: October 8, 2025
"""

import os
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types
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


class GeminiClient(BaseLLMClient):
    """
    Client for Google Gemini API.
    
    Supports multiple Gemini models including:
    - gemini-2.5-flash (fast, efficient, free tier)
    - gemini-2.5-pro (more capable, reasoning)
    - gemini-1.5-flash
    - gemini-1.5-pro
    
    Usage:
        client = GeminiClient(api_key="your-key", config=LLMConfig(model_name="gemini-2.5-flash"))
        response = client.generate("Explain HTN planning")
    """
    
    DEFAULT_MODEL = "gemini-2.5-flash"
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        config: Optional[LLMConfig] = None
    ):
        """
        Initialize Gemini client.
        
        Args:
            api_key: Google AI Studio API key (or set GEMINI_API_KEY env var)
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
            self.api_key = (os.getenv("GOOGLE_GEMINI_API_KEY") or 
                           os.getenv("GEMINI_API_KEY") or 
                           os.getenv("GOOGLE_API_KEY"))
        
        if not self.api_key:
            raise ValueError(
                "Gemini API key not provided. Set GEMINI_API_KEY environment variable "
                "or pass api_key to constructor."
            )
        
        # Initialize Gemini client
        try:
            # Configure API key
            self.client = genai.Client(api_key=self.api_key)
            logger.success(f"Gemini client initialized with model: {self.config.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            raise LLMConnectionError(
                f"Failed to connect to Gemini API: {str(e)}",
                provider="gemini",
                original_error=e
            )
    
    @retry_on_failure(max_retries=3, delay=1.0)
    def generate(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        disable_thinking: bool = False,
        **kwargs
    ) -> LLMResponse:
        """
        Generate text completion from Gemini.
        
        Args:
            prompt: The main prompt/query
            system_prompt: Optional system instructions (prepended to prompt)
            disable_thinking: Disable thinking mode for faster responses
            **kwargs: Additional Gemini-specific parameters
        
        Returns:
            LLMResponse with generated content
        """
        try:
            # Combine system prompt and user prompt
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
            
            # Build generation config
            gen_config = types.GenerateContentConfig(
                temperature=self.config.temperature,
                max_output_tokens=self.config.max_tokens,
                top_p=self.config.top_p,
            )
            
            # Disable thinking if requested (for speed)
            if disable_thinking:
                gen_config.thinking_config = types.ThinkingConfig(thinking_budget=0)
            
            # Generate
            logger.debug(f"Generating with Gemini ({self.config.model_name}): {full_prompt[:100]}...")
            
            response = self.client.models.generate_content(
                model=self.config.model_name,
                contents=full_prompt,
                config=gen_config
            )
            
            # Extract content
            content = response.text if hasattr(response, 'text') else str(response)
            
            # Ensure content is not None
            if content is None:
                content = ""
            
            # Build response object
            llm_response = LLMResponse(
                content=content,
                model=self.config.model_name,
                provider="gemini",
                tokens_used=None,  # Gemini doesn't always return token count
                finish_reason="stop",
                metadata={
                    "response_obj": response,
                    "prompt_length": len(full_prompt)
                }
            )
            
            logger.success(f"Gemini generated {len(content)} characters")
            return llm_response
            
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            
            # Categorize error
            error_str = str(e).lower()
            
            if "rate limit" in error_str or "quota" in error_str:
                raise LLMRateLimitError(
                    "Gemini rate limit exceeded",
                    provider="gemini",
                    original_error=e
                )
            elif "timeout" in error_str:
                raise LLMTimeoutError(
                    "Gemini request timed out",
                    provider="gemini",
                    original_error=e
                )
            elif "api key" in error_str or "authentication" in error_str:
                raise LLMAPIError(
                    "Gemini authentication failed - check API key",
                    provider="gemini",
                    original_error=e
                )
            else:
                raise LLMAPIError(
                    f"Gemini API error: {str(e)}",
                    provider="gemini",
                    original_error=e
                )
    
    @retry_on_failure(max_retries=3, delay=1.0)
    def generate_with_history(
        self, 
        messages: List[Dict[str, str]],
        disable_thinking: bool = False,
        **kwargs
    ) -> LLMResponse:
        """
        Generate with conversation history.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
                     Roles: 'system', 'user', 'assistant'
            disable_thinking: Disable thinking mode for faster responses
            **kwargs: Additional parameters
        
        Returns:
            LLMResponse with generated content
        """
        try:
            # Convert messages to Gemini format
            system_content = None
            user_messages = []
            
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                if role == "system":
                    system_content = content
                elif role in ["user", "assistant", "model"]:
                    # Gemini uses 'model' for assistant
                    gemini_role = "model" if role == "assistant" else "user"
                    user_messages.append({
                        "role": gemini_role,
                        "parts": [{"text": content}]
                    })
            
            # Build config
            gen_config = types.GenerateContentConfig(
                temperature=self.config.temperature,
                max_output_tokens=self.config.max_tokens,
                top_p=self.config.top_p,
                system_instruction=system_content if system_content else None
            )
            
            if disable_thinking:
                gen_config.thinking_config = types.ThinkingConfig(thinking_budget=0)
            
            # Generate
            logger.debug(f"Generating with Gemini chat ({len(messages)} messages)")
            
            response = self.client.models.generate_content(
                model=self.config.model_name,
                contents=user_messages,
                config=gen_config
            )
            
            content = response.text if hasattr(response, 'text') else str(response)
            
            # Ensure content is not None
            if content is None:
                content = ""
            
            return LLMResponse(
                content=content,
                model=self.config.model_name,
                provider="gemini",
                tokens_used=None,
                finish_reason="stop",
                metadata={"messages_count": len(messages)}
            )
            
        except Exception as e:
            logger.error(f"Gemini chat generation failed: {e}")
            raise LLMAPIError(
                f"Gemini chat API error: {str(e)}",
                provider="gemini",
                original_error=e
            )
    
    def is_available(self) -> bool:
        """
        Check if Gemini API is available.
        
        Returns:
            True if API is reachable
        """
        try:
            # Try a minimal generation request
            response = self.client.models.generate_content(
                model=self.config.model_name,
                contents="test",
                config=types.GenerateContentConfig(
                    max_output_tokens=10,
                    thinking_config=types.ThinkingConfig(thinking_budget=0)
                )
            )
            logger.info("Gemini API is available")
            return True
        except Exception as e:
            logger.warning(f"Gemini API check failed: {e}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get Gemini model information"""
        base_info = super().get_model_info()
        base_info.update({
            "api_version": "google-genai-1.41.0",
            "free_tier": True,
            "supports_thinking": "2.5" in self.config.model_name,
            "supports_vision": True,
            "context_window": 1000000 if "2.5" in self.config.model_name else 32000
        })
        return base_info


# Example usage
if __name__ == "__main__":
    # Test Gemini client
    try:
        client = GeminiClient()
        
        # Test basic generation
        response = client.generate(
            prompt="What is HTN planning in AI? Answer in 2 sentences.",
            disable_thinking=True
        )
        print(f"Response: {response.content}")
        print(f"Model: {response.model}")
        
        # Test chat
        messages = [
            {"role": "system", "content": "You are a helpful AI assistant."},
            {"role": "user", "content": "What is 2+2?"}
        ]
        chat_response = client.generate_with_history(messages, disable_thinking=True)
        print(f"\nChat response: {chat_response.content}")
        
    except Exception as e:
        print(f"Error: {e}")
