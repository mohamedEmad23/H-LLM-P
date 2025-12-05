"""
Memory Module for HTN Planner

Provides similarity-based problem matching using FAISS + Gemini embeddings.
"""

from .similarity_search import (
    SimilaritySearch,
    SimilarProblem,
    IndexedProblem,
    GeminiEmbedder,
)

__all__ = [
    "SimilaritySearch",
    "SimilarProblem",
    "IndexedProblem",
    "GeminiEmbedder",
]
