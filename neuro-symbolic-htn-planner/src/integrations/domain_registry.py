"""
Domain Registry - Track and Lookup Generated HDDL Domains

Enables:
- Tracking all generated and validated HDDL domains
- Looking up existing domains before calling LLM
- Recording domain metadata (generation time, method count, LLM provider)
- Supporting domain evolution and versioning
- Providing statistics on domain generation

This is a critical component for the learning system:
- Without it, LLM is called every time for the same domain
- With it, validated domains are reused across problems
"""

import json
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class RegisteredDomain:
    """Metadata for a registered HDDL domain"""
    
    domain_name: str
    domain_file: str
    problem_file: Optional[str] = None
    
    # Generation metadata
    generated_at: str = ""
    generation_time_ms: float = 0.0
    method_count: int = 0
    action_count: int = 0
    predicate_count: int = 0
    
    # Source information
    source: str = "llm_generated"  # llm_generated | hand_coded | imported
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    
    # Validation status
    validation_status: str = "valid"  # valid | invalid | pending
    validation_errors: List[str] = field(default_factory=list)
    validation_warnings: List[str] = field(default_factory=list)
    panda_validated: bool = False
    
    # Usage statistics
    usage_count: int = 0
    last_used: Optional[str] = None
    success_count: int = 0
    failure_count: int = 0
    
    # Versioning
    version: int = 1
    previous_version_hash: Optional[str] = None
    
    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now().isoformat()
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate for this domain"""
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


class DomainRegistry:
    """
    Persistent registry for HDDL domains
    
    Tracks all generated and validated domains to enable:
    - Fast lookup before LLM calls (skip LLM if domain exists)
    - Domain reuse across different problems
    - Statistics on domain generation and usage
    - Domain versioning and evolution
    
    Persistence:
    - Registry: ./results/domain_registry.json
    - Domains: ./src/domains/{domain_name}/domain.hddl
    
    Usage:
        >>> registry = DomainRegistry()
        >>> 
        >>> # Check if domain exists before LLM call
        >>> existing = registry.lookup_domain("graph_traversal")
        >>> if existing:
        ...     print(f"Using existing domain at {existing.domain_file}")
        ... else:
        ...     # Generate new domain with LLM
        ...     ...
        >>>
        >>> # Register newly generated domain
        >>> registry.register_domain(
        ...     domain_name="graph_traversal",
        ...     domain_file="./src/domains/graph_traversal/domain.hddl",
        ...     method_count=5,
        ...     llm_provider="groq"
        ... )
    """
    
    def __init__(
        self,
        registry_path: str = "./results/domain_registry.json",
        domains_base_path: str = "./src/domains"
    ):
        """
        Initialize domain registry
        
        Args:
            registry_path: Path to JSON file for persistent storage
            domains_base_path: Base directory where domains are stored
        """
        self.registry_path = Path(registry_path)
        self.domains_base_path = Path(domains_base_path)
        
        # Ensure directories exist
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self.domains_base_path.mkdir(parents=True, exist_ok=True)
        
        # In-memory registry: domain_name -> RegisteredDomain
        self.registry: Dict[str, RegisteredDomain] = {}
        
        # Load existing registry
        self._load()
        
        # Statistics
        self.stats = {
            "lookups": 0,
            "lookup_hits": 0,
            "lookup_misses": 0,
            "registrations": 0,
            "updates": 0
        }
        
        logger.info(
            f"DomainRegistry initialized with {len(self.registry)} domains "
            f"at {self.registry_path}"
        )
    
    def lookup_domain(self, domain_name: str) -> Optional[RegisteredDomain]:
        """
        Look up a domain by name
        
        This should be called BEFORE any LLM generation to check if
        the domain already exists and can be reused.
        
        Args:
            domain_name: Name of the domain to look up
        
        Returns:
            RegisteredDomain if found and valid, None otherwise
        """
        self.stats["lookups"] += 1
        
        # Normalize domain name
        normalized_name = domain_name.lower().replace(" ", "_").replace("-", "_")
        
        if normalized_name in self.registry:
            domain = self.registry[normalized_name]
            
            # Verify the domain file actually exists
            if Path(domain.domain_file).exists():
                # Update usage statistics
                domain.usage_count += 1
                domain.last_used = datetime.now().isoformat()
                self._save()
                
                self.stats["lookup_hits"] += 1
                
                logger.success(
                    f"[REGISTRY] Domain '{domain_name}' found in registry "
                    f"(used {domain.usage_count} times, success_rate={domain.success_rate:.2f})"
                )
                return domain
            else:
                # Domain file doesn't exist, remove from registry
                logger.warning(
                    f"[REGISTRY] Domain file missing: {domain.domain_file}, "
                    f"removing from registry"
                )
                del self.registry[normalized_name]
                self._save()
        
        self.stats["lookup_misses"] += 1
        logger.debug(f"[REGISTRY] Domain '{domain_name}' not found in registry")
        return None
    
    def register_domain(
        self,
        domain_name: str,
        domain_file: str,
        problem_file: Optional[str] = None,
        method_count: int = 0,
        action_count: int = 0,
        predicate_count: int = 0,
        generation_time_ms: float = 0.0,
        source: str = "llm_generated",
        llm_provider: Optional[str] = None,
        llm_model: Optional[str] = None,
        validation_warnings: Optional[List[str]] = None,
        panda_validated: bool = True
    ) -> RegisteredDomain:
        """
        Register a new domain in the registry
        
        This should be called AFTER successful HDDL generation and validation.
        
        Args:
            domain_name: Name of the domain
            domain_file: Path to the domain HDDL file
            problem_file: Path to the problem HDDL file (optional)
            method_count: Number of methods in the domain
            action_count: Number of actions in the domain
            predicate_count: Number of predicates in the domain
            generation_time_ms: Time taken to generate the domain
            source: Source of the domain (llm_generated, hand_coded, imported)
            llm_provider: LLM provider used (if applicable)
            llm_model: LLM model used (if applicable)
            validation_warnings: Any validation warnings
            panda_validated: Whether PANDA validated the domain
        
        Returns:
            The registered domain entry
        """
        # Normalize domain name
        normalized_name = domain_name.lower().replace(" ", "_").replace("-", "_")
        
        # Check if updating existing domain
        if normalized_name in self.registry:
            existing = self.registry[normalized_name]
            existing.version += 1
            logger.info(f"[REGISTRY] Updating domain '{domain_name}' to version {existing.version}")
            self.stats["updates"] += 1
        
        # Create new registration
        domain = RegisteredDomain(
            domain_name=normalized_name,
            domain_file=str(domain_file),
            problem_file=str(problem_file) if problem_file else None,
            method_count=method_count,
            action_count=action_count,
            predicate_count=predicate_count,
            generation_time_ms=generation_time_ms,
            source=source,
            llm_provider=llm_provider,
            llm_model=llm_model,
            validation_status="valid",
            validation_warnings=validation_warnings or [],
            panda_validated=panda_validated,
            success_count=1  # Start with 1 since it was just validated
        )
        
        self.registry[normalized_name] = domain
        self._save()
        
        self.stats["registrations"] += 1
        
        logger.success(
            f"[REGISTRY] Registered domain '{domain_name}' "
            f"(methods={method_count}, source={source}, file={domain_file})"
        )
        
        return domain
    
    def update_success(self, domain_name: str, success: bool) -> None:
        """
        Update success/failure statistics for a domain
        
        This should be called after each planning attempt to track
        which domains are working well.
        
        Args:
            domain_name: Name of the domain
            success: Whether the planning succeeded
        """
        normalized_name = domain_name.lower().replace(" ", "_").replace("-", "_")
        
        if normalized_name not in self.registry:
            logger.warning(f"[REGISTRY] Cannot update unknown domain: {domain_name}")
            return
        
        domain = self.registry[normalized_name]
        
        if success:
            domain.success_count += 1
            logger.debug(f"[REGISTRY] Domain '{domain_name}' success count: {domain.success_count}")
        else:
            domain.failure_count += 1
            logger.debug(f"[REGISTRY] Domain '{domain_name}' failure count: {domain.failure_count}")
        
        domain.last_used = datetime.now().isoformat()
        self._save()
    
    def get_domain_path(self, domain_name: str) -> Path:
        """
        Get the standard path for a domain
        
        Args:
            domain_name: Name of the domain
        
        Returns:
            Path to the domain directory
        """
        normalized_name = domain_name.lower().replace(" ", "_").replace("-", "_")
        return self.domains_base_path / normalized_name
    
    def persist_domain_files(
        self,
        domain_name: str,
        temp_domain_file: str,
        temp_problem_file: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Copy validated domain files from temp location to permanent storage
        
        This is the key method that enables domain learning:
        - Takes validated HDDL files from /tmp/
        - Copies them to ./src/domains/{domain_name}/
        - Enables reuse across sessions
        
        Args:
            domain_name: Name of the domain
            temp_domain_file: Path to temporary domain file
            temp_problem_file: Path to temporary problem file (optional)
        
        Returns:
            Dict with "domain_file" and "problem_file" paths
        """
        domain_dir = self.get_domain_path(domain_name)
        domain_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy domain file
        persistent_domain_file = domain_dir / "domain.hddl"
        shutil.copy(temp_domain_file, persistent_domain_file)
        
        result = {
            "domain_file": str(persistent_domain_file),
            "problem_file": None
        }
        
        # Copy problem file if provided
        if temp_problem_file:
            persistent_problem_file = domain_dir / "problem.hddl"
            shutil.copy(temp_problem_file, persistent_problem_file)
            result["problem_file"] = str(persistent_problem_file)
        
        logger.success(
            f"[REGISTRY] Persisted domain files to {domain_dir}"
        )
        
        return result
    
    def list_domains(self, source: Optional[str] = None) -> List[RegisteredDomain]:
        """
        List all registered domains
        
        Args:
            source: Optional filter by source (llm_generated, hand_coded, imported)
        
        Returns:
            List of registered domains
        """
        domains = list(self.registry.values())
        
        if source:
            domains = [d for d in domains if d.source == source]
        
        # Sort by usage count (most used first)
        domains.sort(key=lambda d: d.usage_count, reverse=True)
        
        return domains
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get registry statistics"""
        domains = list(self.registry.values())
        
        if not domains:
            return {
                "total_domains": 0,
                "llm_generated": 0,
                "hand_coded": 0,
                "total_usage": 0,
                "total_successes": 0,
                "total_failures": 0,
                "overall_success_rate": 0.0,
                "lookup_hit_rate": 0.0,
                **self.stats
            }
        
        llm_generated = sum(1 for d in domains if d.source == "llm_generated")
        hand_coded = sum(1 for d in domains if d.source == "hand_coded")
        total_usage = sum(d.usage_count for d in domains)
        total_successes = sum(d.success_count for d in domains)
        total_failures = sum(d.failure_count for d in domains)
        
        return {
            "total_domains": len(domains),
            "llm_generated": llm_generated,
            "hand_coded": hand_coded,
            "total_usage": total_usage,
            "total_successes": total_successes,
            "total_failures": total_failures,
            "overall_success_rate": total_successes / (total_successes + total_failures) 
                if (total_successes + total_failures) > 0 else 0.0,
            "lookup_hit_rate": self.stats["lookup_hits"] / self.stats["lookups"]
                if self.stats["lookups"] > 0 else 0.0,
            "most_used_domain": max(domains, key=lambda d: d.usage_count).domain_name
                if domains else None,
            **self.stats
        }
    
    def scan_existing_domains(self) -> int:
        """
        Scan the domains directory and register any existing domains
        
        This is useful for:
        - Initializing the registry with hand-coded domains
        - Recovering after registry file loss
        
        Returns:
            Number of new domains registered
        """
        new_domains = 0
        
        if not self.domains_base_path.exists():
            return 0
        
        for domain_dir in self.domains_base_path.iterdir():
            if not domain_dir.is_dir():
                continue
            
            domain_name = domain_dir.name
            domain_file = domain_dir / "domain.hddl"
            problem_file = domain_dir / "problem.hddl"
            
            if not domain_file.exists():
                continue
            
            # Check if already registered
            normalized_name = domain_name.lower().replace(" ", "_").replace("-", "_")
            if normalized_name in self.registry:
                continue
            
            # Register the domain
            self.register_domain(
                domain_name=domain_name,
                domain_file=str(domain_file),
                problem_file=str(problem_file) if problem_file.exists() else None,
                source="hand_coded",
                panda_validated=False  # We don't know if it was validated
            )
            
            new_domains += 1
            logger.info(f"[REGISTRY] Scanned and registered existing domain: {domain_name}")
        
        return new_domains
    
    def _load(self) -> None:
        """Load registry from disk"""
        if not self.registry_path.exists():
            logger.debug(f"No existing registry at {self.registry_path}")
            return
        
        try:
            with open(self.registry_path, 'r') as f:
                data = json.load(f)
            
            self.registry = {
                name: RegisteredDomain(**domain_data)
                for name, domain_data in data.get("domains", {}).items()
            }
            
            # Load stats if present
            if "stats" in data:
                self.stats.update(data["stats"])
            
            logger.info(f"Loaded {len(self.registry)} domains from registry")
            
        except Exception as e:
            logger.error(f"Failed to load domain registry: {e}")
            self.registry = {}
    
    def _save(self) -> None:
        """Save registry to disk"""
        try:
            data = {
                "domains": {
                    name: domain.to_dict()
                    for name, domain in self.registry.items()
                },
                "stats": self.stats,
                "last_updated": datetime.now().isoformat()
            }
            
            with open(self.registry_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.debug(f"Saved {len(self.registry)} domains to registry")
            
        except Exception as e:
            logger.error(f"Failed to save domain registry: {e}")
    
    def clear_domain(self, domain_name: str) -> bool:
        """
        Remove a domain from the registry
        
        Note: This does NOT delete the domain files, only the registry entry.
        
        Args:
            domain_name: Name of the domain to remove
        
        Returns:
            True if domain was removed, False if not found
        """
        normalized_name = domain_name.lower().replace(" ", "_").replace("-", "_")
        
        if normalized_name in self.registry:
            del self.registry[normalized_name]
            self._save()
            logger.info(f"[REGISTRY] Removed domain '{domain_name}' from registry")
            return True
        
        return False
    
    def clear_all(self) -> int:
        """Clear entire registry"""
        count = len(self.registry)
        self.registry.clear()
        self.stats = {
            "lookups": 0,
            "lookup_hits": 0,
            "lookup_misses": 0,
            "registrations": 0,
            "updates": 0
        }
        self._save()
        logger.info(f"[REGISTRY] Cleared all {count} domains from registry")
        return count

