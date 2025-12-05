"""
Similarity Search for HTN Problem Reuse

Uses Google Gemini embeddings (gemini-embedding-001) + FAISS for similarity search.
Complements the exact-match ProblemCache by finding similar (not identical) problems
and reusing their planning strategies.

Design Decisions:
- Embedding Model: gemini-embedding-001 via Google AI (768-dim, normalized)
- Task Types: RETRIEVAL_DOCUMENT for indexing, SEMANTIC_SIMILARITY for queries
- Persistence: FAISS index + metadata.json at ./results/panda-results/similarity_index/
- Threshold: 0.75 default, configurable per-domain
- Integration: Separate from ProblemCache, called from PANDAWorkflow
"""

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from loguru import logger

# Lazy imports for optional dependencies
_faiss = None
_genai = None
_types = None


def _load_faiss():
    """Lazy load FAISS to avoid import errors if not installed."""
    global _faiss
    if _faiss is None:
        try:
            import faiss

            _faiss = faiss
        except ImportError:
            raise ImportError(
                "faiss-cpu is required for SimilaritySearch. "
                "Install with: pip install faiss-cpu"
            )
    return _faiss


def _load_genai():
    """Lazy load Google GenAI SDK."""
    global _genai, _types
    if _genai is None:
        try:
            from google import genai
            from google.genai import types

            _genai = genai
            _types = types
        except ImportError:
            raise ImportError(
                "google-genai is required for SimilaritySearch. "
                "Install with: pip install google-genai"
            )
    return _genai, _types


@dataclass
class SimilarProblem:
    """A similar problem found via similarity search."""

    problem_id: str
    domain: str
    similarity_score: float  # 0.0 - 1.0 (higher is more similar)
    strategies: List[Dict[str, Any]]  # From PlanningAgent Phase 1
    plan_length: int
    goal_description: str
    state_summary: str
    success_rate: float = 1.0  # Historical success with this strategy

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class IndexedProblem:
    """Metadata stored alongside each embedding in the FAISS index."""

    problem_id: str
    domain: str
    goal_description: str
    state_summary: str
    strategies: List[Dict[str, Any]]
    plan_actions: List[Dict[str, Any]]
    plan_length: int
    indexed_at: str = ""
    retrieval_count: int = 0
    success_count: int = 0

    def __post_init__(self):
        if not self.indexed_at:
            self.indexed_at = datetime.now().isoformat()


class GeminiEmbedder:
    """
    Wrapper for Google Gemini Embedding API.

    Uses gemini-embedding-001 model with:
    - 768-dimensional embeddings (normalized)
    - RETRIEVAL_DOCUMENT task type for indexing
    - SEMANTIC_SIMILARITY task type for queries
    """

    MODEL_NAME = "gemini-embedding-001"
    EMBEDDING_DIM = 768

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini embedder.

        Args:
            api_key: Google AI API key. If not provided, reads from environment:
                     GOOGLE_GEMINI_API_KEY, GEMINI_API_KEY, or GOOGLE_API_KEY
        """
        genai, types = _load_genai()

        # Get API key from environment if not provided
        if api_key is None:
            api_key = (
                os.getenv("GOOGLE_GEMINI_API_KEY")
                or os.getenv("GEMINI_API_KEY")
                or os.getenv("GOOGLE_API_KEY")
            )

        if not api_key:
            raise ValueError(
                "Gemini API key not provided. Set GEMINI_API_KEY environment variable "
                "or pass api_key to constructor."
            )

        self.client = genai.Client(api_key=api_key)
        self._types = types
        logger.info(f"GeminiEmbedder initialized with model: {self.MODEL_NAME}")

    def embed_for_indexing(self, text: str) -> np.ndarray:
        """
        Create embedding for document indexing.

        Uses RETRIEVAL_DOCUMENT task type optimized for storing documents.

        Args:
            text: Text to embed

        Returns:
            Normalized 768-dimensional embedding vector
        """
        result = self.client.models.embed_content(
            model=self.MODEL_NAME,
            contents=text,
            config=self._types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT", output_dimensionality=self.EMBEDDING_DIM
            ),
        )

        embedding = np.array(result.embeddings[0].values, dtype=np.float32)
        # Normalize for cosine similarity (768-dim needs normalization)
        embedding = embedding / np.linalg.norm(embedding)
        return embedding

    def embed_for_query(self, text: str) -> np.ndarray:
        """
        Create embedding for similarity query.

        Uses SEMANTIC_SIMILARITY task type optimized for comparing texts.

        Args:
            text: Query text

        Returns:
            Normalized 768-dimensional embedding vector
        """
        result = self.client.models.embed_content(
            model=self.MODEL_NAME,
            contents=text,
            config=self._types.EmbedContentConfig(
                task_type="SEMANTIC_SIMILARITY",
                output_dimensionality=self.EMBEDDING_DIM,
            ),
        )

        embedding = np.array(result.embeddings[0].values, dtype=np.float32)
        # Normalize for cosine similarity
        embedding = embedding / np.linalg.norm(embedding)
        return embedding

    def embed_batch(
        self, texts: List[str], for_indexing: bool = True
    ) -> List[np.ndarray]:
        """
        Embed multiple texts in a single API call.

        Args:
            texts: List of texts to embed
            for_indexing: If True, use RETRIEVAL_DOCUMENT; else SEMANTIC_SIMILARITY

        Returns:
            List of normalized embedding vectors
        """
        task_type = "RETRIEVAL_DOCUMENT" if for_indexing else "SEMANTIC_SIMILARITY"

        result = self.client.models.embed_content(
            model=self.MODEL_NAME,
            contents=texts,
            config=self._types.EmbedContentConfig(
                task_type=task_type, output_dimensionality=self.EMBEDDING_DIM
            ),
        )

        embeddings = []
        for emb in result.embeddings:
            vec = np.array(emb.values, dtype=np.float32)
            vec = vec / np.linalg.norm(vec)  # Normalize
            embeddings.append(vec)

        return embeddings


class SimilaritySearch:
    """
    FAISS-based similarity search for HTN problems.

    Uses Google Gemini embeddings (gemini-embedding-001) for semantic similarity:
    - 768-dimensional embeddings
    - ~200-500ms latency per query (API call)
    - Automatic normalization for cosine similarity

    Persistence:
    - FAISS index: similarity_index/faiss_index.bin
    - Metadata: similarity_index/metadata.json

    Usage:
        >>> search = SimilaritySearch()
        >>> search.add_solved_problem(
        ...     problem_id="hanoi_4_disk",
        ...     domain="hanoi",
        ...     goal="Move all disks from peg A to peg C",
        ...     init_state={"n_disks": 4, "pegs": {"A": [4,3,2,1], "B": [], "C": []}},
        ...     strategies=[{"name": "recursive_move", "approach": "Break into subproblems"}],
        ...     plan_actions=[{"name": "move", "params": ["disk_1", "A", "C"]}]
        ... )
        >>> similar = search.find_similar(
        ...     domain="hanoi",
        ...     goal="Move all disks from peg A to peg C",
        ...     init_state={"n_disks": 5, "pegs": {"A": [5,4,3,2,1], "B": [], "C": []}}
        ... )
        >>> print(similar[0].similarity_score)  # ~0.95 (very similar)
    """

    EMBEDDING_DIM = 768  # Gemini embedding dimension

    def __init__(
        self,
        index_path: str = "./results/panda-results/similarity_index",
        similarity_threshold: float = 0.75,
        api_key: Optional[str] = None,
        domain_thresholds: Optional[Dict[str, float]] = None,
    ):
        """
        Initialize SimilaritySearch.

        Args:
            index_path: Directory for persistence (faiss_index.bin + metadata.json)
            similarity_threshold: Default minimum similarity score (0.0-1.0)
            api_key: Google AI API key (optional, reads from env)
            domain_thresholds: Per-domain threshold overrides, e.g. {"hanoi": 0.8}
        """
        self.index_dir = Path(index_path)
        self.similarity_threshold = similarity_threshold
        self.domain_thresholds = domain_thresholds or {}

        # Lazy-loaded components
        self._embedder: Optional[GeminiEmbedder] = None
        self._api_key = api_key
        self._index = None
        self.metadata: List[IndexedProblem] = []

        # Create index directory
        self.index_dir.mkdir(parents=True, exist_ok=True)

        # Try to load existing index
        self._load()

        logger.info(
            f"SimilaritySearch initialized: threshold={similarity_threshold}, "
            f"indexed_problems={len(self.metadata)}, path={index_path}"
        )

    @property
    def embedder(self) -> GeminiEmbedder:
        """Lazy-load the Gemini embedder."""
        if self._embedder is None:
            self._embedder = GeminiEmbedder(api_key=self._api_key)
        return self._embedder

    @property
    def index(self):
        """Lazy-load or create the FAISS index."""
        if self._index is None:
            faiss = _load_faiss()
            # Use Inner Product (cosine similarity for normalized vectors)
            self._index = faiss.IndexFlatIP(self.EMBEDDING_DIM)
            logger.debug("Created new FAISS index")
        return self._index

    def _get_threshold(self, domain: str) -> float:
        """Get similarity threshold for a domain."""
        return self.domain_thresholds.get(domain, self.similarity_threshold)

    def _summarize_state(self, init_state: Dict[str, Any]) -> str:
        """
        Extract key state features for embedding.

        Converts structured state dict to a concise text summary.
        This avoids embedding the entire state (which could be large)
        while capturing the essential scale/structure information.

        Args:
            init_state: Initial state dictionary (various formats supported)

        Returns:
            Concise text summary of the state
        """
        if not init_state:
            return "Empty state"

        summaries = []

        # PDDL-style states with predicates
        if "predicates" in init_state:
            predicates = init_state["predicates"]
            if isinstance(predicates, list):
                summaries.append(f"{len(predicates)} predicates")
                # Sample predicate types
                pred_types = set()
                for pred in predicates[:10]:  # Sample first 10
                    if isinstance(pred, str):
                        pred_type = (
                            pred.split("(")[0] if "(" in pred else pred.split()[0]
                        )
                        pred_types.add(pred_type)
                if pred_types:
                    summaries.append(f"types: {', '.join(sorted(pred_types)[:5])}")

        # Tower of Hanoi problems
        if "n_disks" in init_state:
            summaries.append(f"{init_state['n_disks']} disks")
        if "pegs" in init_state:
            pegs = init_state["pegs"]
            if isinstance(pegs, dict):
                non_empty = [k for k, v in pegs.items() if v]
                summaries.append(f"pegs: {', '.join(sorted(non_empty))}")

        # Graph problems
        if "num_nodes" in init_state or "nodes" in init_state:
            n = init_state.get("num_nodes") or len(init_state.get("nodes", []))
            summaries.append(f"{n} nodes")
        if "edges" in init_state:
            edges = init_state["edges"]
            n_edges = len(edges) if isinstance(edges, (list, dict)) else 0
            summaries.append(f"{n_edges} edges")

        # Sorting problems
        if "nums" in init_state or "array" in init_state:
            arr = init_state.get("nums") or init_state.get("array", [])
            if isinstance(arr, list):
                summaries.append(f"array[{len(arr)}]")

        # Blocksworld
        if "blocks" in init_state:
            blocks = init_state["blocks"]
            n_blocks = len(blocks) if isinstance(blocks, (list, dict)) else 0
            summaries.append(f"{n_blocks} blocks")

        # Generic fallback: count keys
        if not summaries:
            summaries.append(f"keys: {', '.join(sorted(init_state.keys())[:5])}")

        return "; ".join(summaries)

    def _create_problem_text(
        self, domain: str, goal: str, init_state: Dict[str, Any]
    ) -> str:
        """
        Create text representation for embedding.

        Concatenates domain, goal, and state summary into a single text.

        Args:
            domain: Domain name (e.g., "hanoi", "graph_traversal")
            goal: Goal description in natural language
            init_state: Initial state dictionary

        Returns:
            Formatted text for embedding
        """
        state_summary = self._summarize_state(init_state)
        return f"Domain: {domain}\nGoal: {goal}\nInitial State: {state_summary}"

    def add_solved_problem(
        self,
        problem_id: str,
        domain: str,
        goal: str,
        init_state: Dict[str, Any],
        strategies: List[Dict[str, Any]],
        plan_actions: List[Dict[str, Any]],
    ) -> None:
        """
        Store a solved problem for future similarity matching.

        Args:
            problem_id: Unique identifier for the problem
            domain: Domain name
            goal: Goal description
            init_state: Initial state dictionary
            strategies: Planning strategies from Phase 1
            plan_actions: List of plan actions (from solved plan)
        """
        # Check if already indexed
        existing_ids = {m.problem_id for m in self.metadata}
        if problem_id in existing_ids:
            logger.debug(f"Problem {problem_id} already indexed, skipping")
            return

        # Create embedding text
        text = self._create_problem_text(domain, goal, init_state)

        # Get embedding (for indexing/storage)
        embedding = self.embedder.embed_for_indexing(text)

        # Store in FAISS
        self.index.add(embedding.reshape(1, -1))

        # Store metadata (parallel array with FAISS index)
        state_summary = self._summarize_state(init_state)
        metadata = IndexedProblem(
            problem_id=problem_id,
            domain=domain,
            goal_description=goal,
            state_summary=state_summary,
            strategies=strategies,
            plan_actions=plan_actions,
            plan_length=len(plan_actions),
        )
        self.metadata.append(metadata)

        # Persist immediately
        self.save()

        logger.success(
            f"[SIMILARITY] Indexed problem '{problem_id}' "
            f"(domain={domain}, actions={len(plan_actions)}, total_indexed={len(self.metadata)})"
        )

    def find_similar(
        self,
        domain: str,
        goal: str,
        init_state: Dict[str, Any],
        top_k: int = 3,
        threshold: Optional[float] = None,
    ) -> List[SimilarProblem]:
        """
        Find similar solved problems above threshold.

        Args:
            domain: Domain name
            goal: Goal description
            init_state: Initial state dictionary
            top_k: Maximum number of results to return
            threshold: Override similarity threshold (uses domain default if None)

        Returns:
            List of SimilarProblem objects, sorted by similarity (descending)
        """
        if self.index.ntotal == 0:
            logger.debug("[SIMILARITY] Index is empty, no similar problems")
            return []

        # Create query text
        text = self._create_problem_text(domain, goal, init_state)

        # Get query embedding (using SEMANTIC_SIMILARITY task type)
        query_embedding = self.embedder.embed_for_query(text)

        # Search FAISS (returns distances and indices)
        # For IndexFlatIP with normalized vectors, distance = cosine similarity
        k = min(top_k, self.index.ntotal)
        distances, indices = self.index.search(query_embedding.reshape(1, -1), k)

        # Get effective threshold
        effective_threshold = threshold or self._get_threshold(domain)

        # Filter by threshold and convert to SimilarProblem objects
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0:  # FAISS returns -1 for empty slots
                continue

            similarity = float(dist)  # Already cosine similarity for normalized vectors

            if similarity < effective_threshold:
                continue

            # Get metadata
            if idx >= len(self.metadata):
                logger.warning(
                    f"Index {idx} out of bounds for metadata (len={len(self.metadata)})"
                )
                continue

            meta = self.metadata[idx]

            # Update retrieval count
            meta.retrieval_count += 1

            result = SimilarProblem(
                problem_id=meta.problem_id,
                domain=meta.domain,
                similarity_score=similarity,
                strategies=meta.strategies,
                plan_length=meta.plan_length,
                goal_description=meta.goal_description,
                state_summary=meta.state_summary,
                success_rate=(
                    meta.success_count / max(1, meta.retrieval_count)
                    if meta.retrieval_count > 0
                    else 1.0
                ),
            )
            results.append(result)

        if results:
            logger.info(
                f"[SIMILARITY] Found {len(results)} similar problems "
                f"(best: {results[0].problem_id} @ {results[0].similarity_score:.3f})"
            )
        else:
            logger.debug(
                f"[SIMILARITY] No problems above threshold {effective_threshold}"
            )

        return results

    def record_success(self, problem_id: str) -> None:
        """
        Record that a similar problem's strategy was used successfully.

        Args:
            problem_id: The problem ID whose strategy was reused
        """
        for meta in self.metadata:
            if meta.problem_id == problem_id:
                meta.success_count += 1
                self.save()
                logger.debug(f"[SIMILARITY] Recorded success for {problem_id}")
                return

    def save(self) -> None:
        """Persist FAISS index and metadata to disk."""
        faiss = _load_faiss()

        index_path = self.index_dir / "faiss_index.bin"
        metadata_path = self.index_dir / "metadata.json"

        try:
            # Save FAISS index
            faiss.write_index(self.index, str(index_path))

            # Save metadata
            metadata_dicts = [asdict(m) for m in self.metadata]
            with open(metadata_path, "w") as f:
                json.dump(metadata_dicts, f, indent=2, default=str)

            logger.debug(
                f"[SIMILARITY] Saved index ({self.index.ntotal} vectors) "
                f"and metadata ({len(self.metadata)} problems)"
            )
        except Exception as e:
            logger.error(f"[SIMILARITY] Failed to save: {e}")

    def _load(self) -> None:
        """Load FAISS index and metadata from disk if they exist."""
        faiss = _load_faiss()

        index_path = self.index_dir / "faiss_index.bin"
        metadata_path = self.index_dir / "metadata.json"

        if not index_path.exists() or not metadata_path.exists():
            logger.debug(f"[SIMILARITY] No existing index at {self.index_dir}")
            return

        try:
            # Load FAISS index
            self._index = faiss.read_index(str(index_path))

            # Load metadata
            with open(metadata_path, "r") as f:
                metadata_dicts = json.load(f)
            self.metadata = [IndexedProblem(**m) for m in metadata_dicts]

            logger.info(
                f"[SIMILARITY] Loaded index ({self._index.ntotal} vectors) "
                f"and metadata ({len(self.metadata)} problems) from {self.index_dir}"
            )

            # Sanity check
            if self._index.ntotal != len(self.metadata):
                logger.warning(
                    f"[SIMILARITY] Index/metadata mismatch: "
                    f"{self._index.ntotal} vectors vs {len(self.metadata)} metadata entries"
                )
        except Exception as e:
            logger.error(f"[SIMILARITY] Failed to load index: {e}")
            self._index = None
            self.metadata = []

    def clear(self) -> None:
        """Clear the entire index and metadata."""
        faiss = _load_faiss()

        self._index = faiss.IndexFlatIP(self.EMBEDDING_DIM)
        self.metadata = []

        # Delete files
        index_path = self.index_dir / "faiss_index.bin"
        metadata_path = self.index_dir / "metadata.json"

        if index_path.exists():
            index_path.unlink()
        if metadata_path.exists():
            metadata_path.unlink()

        logger.info("[SIMILARITY] Cleared index and metadata")

    def get_statistics(self) -> Dict[str, Any]:
        """Get index statistics for monitoring."""
        if not self.metadata:
            return {
                "total_indexed": 0,
                "domains": [],
                "avg_plan_length": 0,
                "total_retrievals": 0,
                "total_successes": 0,
                "success_rate": 0.0,
                "index_size_vectors": 0,
            }

        domains = list(set(m.domain for m in self.metadata))
        avg_plan_length = sum(m.plan_length for m in self.metadata) / len(self.metadata)
        total_retrievals = sum(m.retrieval_count for m in self.metadata)
        total_successes = sum(m.success_count for m in self.metadata)

        return {
            "total_indexed": len(self.metadata),
            "domains": domains,
            "avg_plan_length": avg_plan_length,
            "total_retrievals": total_retrievals,
            "total_successes": total_successes,
            "success_rate": total_successes / max(1, total_retrievals),
            "index_size_vectors": self.index.ntotal if self._index else 0,
        }
