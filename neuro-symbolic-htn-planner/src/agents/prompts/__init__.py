"""
Agent Prompts Module

Contains prompt templates for all agents in the multi-agent system.

Author: H-LLM-P Project
Phase: 4A - Multi-Agent Core
"""

from .decomposition_prompts import (
    DECOMPOSITION_SYSTEM_PROMPT,
    DECOMPOSITION_USER_PROMPT,
    build_decomposition_prompt,
    parse_decomposition_response,
)

from .verification_prompts import (
    VERIFICATION_SYSTEM_PROMPT,
    VERIFICATION_USER_PROMPT,
    build_verification_prompt,
    parse_verification_response,
    calculate_quality_metrics,
)

__all__ = [
    "DECOMPOSITION_SYSTEM_PROMPT",
    "DECOMPOSITION_USER_PROMPT",
    "build_decomposition_prompt",
    "parse_decomposition_response",
    "VERIFICATION_SYSTEM_PROMPT",
    "VERIFICATION_USER_PROMPT",
    "build_verification_prompt",
    "parse_verification_response",
    "calculate_quality_metrics",
]
