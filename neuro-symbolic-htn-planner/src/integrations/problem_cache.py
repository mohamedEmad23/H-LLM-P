"""
Problem Cache - Recognize and reuse solutions for repeated problems

Enables:
- Detecting identical/similar problems by signature (hash of domain + state + goal)
- Skipping LLM + PANDA calls for known problems
- Tracking reuse statistics
- Progressive learning through solution caching
"""

import hashlib
import json
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any
from loguru import logger


@dataclass
class CachedProblem:
    """A cached problem with its solution"""
    signature: str
    domain: str
    problem_name: str
    initial_state_hash: str
    goal_hash: str
    solution: Dict[str, Any]  # The workflow result as dict
    plan_actions: List[Dict[str, Any]]
    strategies: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = ""
    hit_count: int = 0
    last_accessed: Optional[str] = None
    total_time_ms: float = 0.0
    panda_search_time_ms: float = 0.0
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class ProblemCache:
    """
    Cache for recognizing and reusing solutions to repeated problems
    
    Enables:
    - Detecting identical/similar problems
    - Skipping LLM + PANDA calls for known problems
    - Tracking reuse statistics
    - Significant performance improvement for repeated queries
    """
    
    def __init__(self, cache_path: str = "./results/panda-results/problem_cache.json"):
        """
        Initialize problem cache
        
        Args:
            cache_path: Path to JSON file for persistent storage
        """
        self.cache_path = Path(cache_path)
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache: Dict[str, CachedProblem] = {}
        self._load()
        
        logger.info(f"ProblemCache initialized with {len(self.cache)} cached problems")
    
    def create_signature(
        self,
        domain: str,
        initial_state: Dict[str, Any],
        goal_description: str
    ) -> str:
        """
        Create unique signature for a problem
        
        The signature is a hash of:
        - Domain name
        - Sorted predicates from initial state
        - Normalized goal description
        
        Args:
            domain: Domain name
            initial_state: Initial state dict (with 'predicates' key or raw dict)
            goal_description: Goal as string
        
        Returns:
            SHA256 hash signature (16 chars)
        """
        # Normalize initial state (sort predicates for consistency)
        if isinstance(initial_state.get("predicates"), list):
            state_str = json.dumps(sorted(initial_state["predicates"]), sort_keys=True)
        else:
            state_str = json.dumps(initial_state, sort_keys=True)
        
        # Normalize goal (lowercase, strip whitespace)
        normalized_goal = " ".join(goal_description.strip().lower().split())
        
        # Combine components
        combined = f"{domain.lower()}|{state_str}|{normalized_goal}"
        
        # Create hash
        return hashlib.sha256(combined.encode()).hexdigest()[:16]
    
    def check_cache(
        self,
        domain: str,
        initial_state: Dict[str, Any],
        goal_description: str
    ) -> Optional[CachedProblem]:
        """
        Check if problem is in cache
        
        Args:
            domain: Domain name
            initial_state: Initial state dict
            goal_description: Goal as string
        
        Returns:
            CachedProblem if found, None otherwise
        """
        signature = self.create_signature(domain, initial_state, goal_description)
        
        if signature in self.cache:
            cached = self.cache[signature]
            cached.hit_count += 1
            cached.last_accessed = datetime.now().isoformat()
            self._save()
            
            logger.success(
                f"[CACHE HIT] Problem '{cached.problem_name}' found in cache "
                f"(signature: {signature[:8]}..., hits: {cached.hit_count})"
            )
            return cached
        
        logger.debug(f"[CACHE MISS] No cached solution for signature {signature[:8]}...")
        return None
    
    def store_solution(
        self,
        domain: str,
        problem_name: str,
        initial_state: Dict[str, Any],
        goal_description: str,
        solution: Dict[str, Any],
        plan_actions: List[Dict[str, Any]],
        strategies: Optional[List[Dict[str, Any]]] = None,
        total_time_ms: float = 0.0,
        panda_search_time_ms: float = 0.0
    ) -> str:
        """
        Store successful solution in cache
        
        Args:
            domain: Domain name
            problem_name: Problem identifier
            initial_state: Initial state dict
            goal_description: Goal description
            solution: Complete workflow result dict
            plan_actions: List of plan actions
            strategies: Planning strategies (from Phase 1)
            total_time_ms: Total workflow time
            panda_search_time_ms: PANDA search time
        
        Returns:
            Problem signature
        """
        signature = self.create_signature(domain, initial_state, goal_description)
        
        # Create state hashes for debugging
        state_str = json.dumps(initial_state, sort_keys=True)
        initial_state_hash = hashlib.sha256(state_str.encode()).hexdigest()[:8]
        goal_hash = hashlib.sha256(goal_description.encode()).hexdigest()[:8]
        
        cached = CachedProblem(
            signature=signature,
            domain=domain,
            problem_name=problem_name,
            initial_state_hash=initial_state_hash,
            goal_hash=goal_hash,
            solution=solution,
            plan_actions=plan_actions,
            strategies=strategies or [],
            total_time_ms=total_time_ms,
            panda_search_time_ms=panda_search_time_ms
        )
        
        self.cache[signature] = cached
        self._save()
        
        logger.success(
            f"[CACHE STORE] Stored solution for '{problem_name}' "
            f"(signature: {signature[:8]}..., actions: {len(plan_actions)})"
        )
        
        return signature
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.cache:
            return {
                "total_cached_problems": 0,
                "total_cache_hits": 0,
                "domains": [],
                "most_accessed": None,
                "avg_time_saved_ms": 0.0
            }
        
        total_hits = sum(p.hit_count for p in self.cache.values())
        total_time_saved = sum(p.hit_count * p.total_time_ms for p in self.cache.values())
        
        most_accessed = max(self.cache.values(), key=lambda p: p.hit_count)
        
        return {
            "total_cached_problems": len(self.cache),
            "total_cache_hits": total_hits,
            "domains": list(set(p.domain for p in self.cache.values())),
            "most_accessed": most_accessed.problem_name,
            "most_accessed_hits": most_accessed.hit_count,
            "avg_time_saved_ms": total_time_saved / total_hits if total_hits > 0 else 0.0
        }
    
    def clear_domain(self, domain: str) -> int:
        """
        Clear all cached problems for a domain
        
        Args:
            domain: Domain name
        
        Returns:
            Number of problems removed
        """
        to_remove = [sig for sig, prob in self.cache.items() if prob.domain == domain]
        
        for sig in to_remove:
            del self.cache[sig]
        
        if to_remove:
            self._save()
            logger.info(f"Cleared {len(to_remove)} cached problems for domain '{domain}'")
        
        return len(to_remove)
    
    def clear_all(self) -> int:
        """Clear entire cache"""
        count = len(self.cache)
        self.cache.clear()
        self._save()
        logger.info(f"Cleared all {count} cached problems")
        return count
    
    def _load(self) -> None:
        """Load cache from disk"""
        if not self.cache_path.exists():
            logger.debug(f"No existing cache at {self.cache_path}")
            return
        
        try:
            with open(self.cache_path, 'r') as f:
                data = json.load(f)
            
            self.cache = {
                sig: CachedProblem(**problem_data)
                for sig, problem_data in data.items()
            }
            
            logger.info(f"Loaded {len(self.cache)} cached problems from {self.cache_path}")
        except Exception as e:
            logger.error(f"Failed to load problem cache: {e}")
            self.cache = {}
    
    def _save(self) -> None:
        """Save cache to disk"""
        try:
            data = {sig: asdict(prob) for sig, prob in self.cache.items()}
            with open(self.cache_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.debug(f"Saved {len(self.cache)} problems to cache")
        except Exception as e:
            logger.error(f"Failed to save problem cache: {e}")

