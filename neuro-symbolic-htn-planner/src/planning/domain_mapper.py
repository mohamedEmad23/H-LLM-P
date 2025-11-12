"""Domain Mapper for routing problems to HTN domains.

This module maps user-submitted problems to known HTN domains or triggers
dynamic domain generation for novel problem types.
"""

import json
from typing import Optional, Dict, Any
from pathlib import Path

from ..interface.problem_cli import Problem
from .domain import Domain
from .domain_generator import DomainGenerator


class DomainMapper:
    """Maps problems to HTN domains using MMS cache and LLM generation."""

    # Known domain mappings (problem_type -> domain_name)
    KNOWN_DOMAINS = {
        "tower_of_hanoi": "hanoi",
        "tower_of_hanoi_constrained": "hanoi",  # Uses base hanoi with constraints
        "graph_traversal": "graph_traversal",
        "blocks_world": "blocks_world",
        "logistics": "logistics",
    }

    def __init__(self, cache_dir: str = "cache/domains", enable_mms: bool = True):
        """Initialize the domain mapper.

        Args:
            cache_dir: Directory for caching generated domains
            enable_mms: Whether to use MMS for caching (falls back to file cache)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.enable_mms = enable_mms
        self.domain_generator = DomainGenerator()

        # Initialize MMS if available
        self.mms = None
        if enable_mms:
            try:
                from ..memory.mms_core import MMSCore

                self.mms = MMSCore()
            except ImportError:
                print("Warning: MMS not available, using file cache")

    def map_problem_to_domain(self, problem: Problem) -> Domain:
        """Map a problem to an HTN domain.

        This method follows a three-step process:
        1. Check if problem_type maps to a known domain
        2. Check MMS/file cache for previously generated domain
        3. Generate new domain using LLM and cache it

        Args:
            problem: Problem instance to map

        Returns:
            Domain instance ready for HTN planning

        Raises:
            ValueError: If domain cannot be loaded or generated
        """
        # Step 1: Check for known domains
        if problem.problem_type in self.KNOWN_DOMAINS:
            domain_name = self.KNOWN_DOMAINS[problem.problem_type]
            print(f"✓ Using known domain: {domain_name}")
            return self._load_known_domain(domain_name, problem)

        # Step 2: Check cache for previously generated domain
        cached_domain = self._load_from_cache(problem.problem_type)
        if cached_domain:
            print(f"✓ Using cached domain for: {problem.problem_type}")
            return cached_domain

        # Step 3: Generate new domain using LLM
        print(f"⚡ Generating new domain for: {problem.problem_type}")
        generated_domain = self.domain_generator.generate_domain(problem)

        # Cache the generated domain
        self._save_to_cache(problem.problem_type, generated_domain)

        return generated_domain

    def _load_known_domain(self, domain_name: str, problem: Problem) -> Domain:
        """Load a known domain from the codebase.

        Args:
            domain_name: Name of the domain to load
            problem: Problem instance (for initial state)

        Returns:
            Domain instance

        Raises:
            ValueError: If domain is not yet implemented
        """
        # For now, all "known" domains will trigger generation
        # This is a placeholder for future domain implementations
        raise ValueError(
            f"Known domain '{domain_name}' not yet implemented. "
            f"Will generate domain dynamically."
        )

    def _load_from_cache(self, problem_type: str) -> Optional[Domain]:
        """Load a domain from cache (MMS or file).

        Args:
            problem_type: Type of problem to look up

        Returns:
            Cached Domain instance, or None if not found
        """
        # Try MMS first
        if self.mms:
            try:
                # Query long-term memory for cached domain
                query = f"generated_domain:{problem_type}"
                results = self.mms.retrieve(query, memory_type="long_term")

                if results:
                    # Deserialize domain from JSON
                    domain_data = json.loads(results[0]["content"])
                    return self._deserialize_domain(domain_data)
            except Exception as e:
                print(f"Warning: MMS cache lookup failed: {e}")

        # Fall back to file cache
        cache_file = self.cache_dir / f"{problem_type}.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r") as f:
                    domain_data = json.load(f)
                return self._deserialize_domain(domain_data)
            except Exception as e:
                print(f"Warning: File cache read failed: {e}")

        return None

    def _save_to_cache(self, problem_type: str, domain: Domain) -> None:
        """Save a generated domain to cache (MMS and file).

        Args:
            problem_type: Type of problem
            domain: Domain instance to cache
        """
        domain_data = self._serialize_domain(domain)

        # Save to MMS
        if self.mms:
            try:
                self.mms.store(
                    content=json.dumps(domain_data),
                    memory_type="long_term",
                    metadata={
                        "type": "generated_domain",
                        "problem_type": problem_type,
                        "domain_name": domain.name,
                    },
                )
                print("✓ Domain cached in MMS")
            except Exception as e:
                print(f"Warning: MMS cache save failed: {e}")

        # Save to file cache
        cache_file = self.cache_dir / f"{problem_type}.json"
        try:
            with open(cache_file, "w") as f:
                json.dump(domain_data, f, indent=2)
            print(f"✓ Domain cached to file: {cache_file}")
        except Exception as e:
            print(f"Warning: File cache save failed: {e}")

    def _serialize_domain(self, domain: Domain) -> Dict[str, Any]:
        """Serialize a domain to JSON-compatible format.

        Args:
            domain: Domain instance to serialize

        Returns:
            Dictionary representation of domain
        """
        return {
            "name": domain.name,
            "description": getattr(domain, "description", ""),
            "tasks": [
                {
                    "name": task.name,
                    "parameters": task.parameters,
                    "preconditions": task.preconditions,
                    "effects": task.effects,
                }
                for task in domain.tasks
            ],
            "methods": [
                {
                    "name": method.name,
                    "task": method.task,
                    "subtasks": method.subtasks,
                    "preconditions": method.preconditions,
                }
                for method in domain.methods
            ],
            "operators": [
                {
                    "name": op.name,
                    "parameters": op.parameters,
                    "preconditions": op.preconditions,
                    "effects": op.effects,
                }
                for op in domain.operators
            ],
        }

    def _deserialize_domain(self, data: Dict[str, Any]) -> Domain:
        """Deserialize a domain from JSON format.

        Args:
            data: Dictionary containing domain data

        Returns:
            Domain instance
        """
        # Create domain
        domain = Domain(name=data["name"])
        domain.description = data.get("description", "")

        # Recreate tasks (simplified objects)
        for task_data in data.get("tasks", []):
            task = type("SimpleTask", (), task_data)()
            domain.add_task(task)

        # Recreate methods (simplified objects)
        for method_data in data.get("methods", []):
            method = type("SimpleMethod", (), method_data)()
            domain.add_method(method)

        # Recreate operators (simplified objects)
        for op_data in data.get("operators", []):
            operator = type("SimpleOperator", (), op_data)()
            domain.add_operator(operator)

        return domain

    def clear_cache(self, problem_type: Optional[str] = None) -> None:
        """Clear cached domains.

        Args:
            problem_type: Specific problem type to clear, or None to clear all
        """
        if problem_type:
            # Clear specific problem type
            cache_file = self.cache_dir / f"{problem_type}.json"
            if cache_file.exists():
                cache_file.unlink()
                print(f"✓ Cleared cache for: {problem_type}")

            if self.mms:
                # Clear from MMS (implementation depends on MMS API)
                pass
        else:
            # Clear all cached domains
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
            print("✓ Cleared all cached domains")

    def list_cached_domains(self) -> list[str]:
        """List all cached domain types.

        Returns:
            List of problem types with cached domains
        """
        return [f.stem for f in self.cache_dir.glob("*.json")]
