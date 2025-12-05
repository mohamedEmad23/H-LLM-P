"""
PANDA Method Library - Enhanced MethodLibrary for HDDL storage
Stores successful LLM-generated HDDL methods for reuse
"""

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class HDDLMethod:
    """Stored HDDL method with metadata"""
    domain: str
    task_name: str
    method_name: str
    hddl_text: str
    parameters: Dict[str, str]
    preconditions: List[str]
    subtasks: List[Dict[str, any]]
    ordering: List[tuple]
    success_count: int = 0
    failure_count: int = 0
    last_used: Optional[str] = None
    created_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0


class PANDAMethodLibrary:
    """
    Persistent storage for successful HDDL methods
    
    Enables:
    - Storing LLM-generated HDDL methods that PANDA successfully planned with
    - Retrieving proven methods for similar tasks
    - Tracking success/failure rates for method selection
    - Progressive learning through method reuse
    """
    
    def __init__(self, storage_path: str = "./results/panda-results/method_library.json"):
        """
        Initialize PANDA method library
        
        Args:
            storage_path: Path to JSON file for persistent storage
        """
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # In-memory storage: domain -> task -> list of methods
        self.methods: Dict[str, Dict[str, List[HDDLMethod]]] = {}
        
        # Load existing methods
        self._load()
    
    def store_method(
        self,
        domain: str,
        task_name: str,
        method_name: str,
        hddl_text: str,
        parameters: Dict[str, str],
        preconditions: List[str],
        subtasks: List[Dict[str, any]],
        ordering: List[tuple]
    ) -> None:
        """
        Store a successful HDDL method
        
        Args:
            domain: Domain name
            task_name: Task this method decomposes
            method_name: Unique method name
            hddl_text: Complete HDDL method text
            parameters: Method parameters {name: type}
            preconditions: Precondition list
            subtasks: Subtask decomposition
            ordering: Ordering constraints
        """
        # Check if method already exists
        existing = self._find_method(domain, task_name, method_name)
        
        if existing:
            logger.info(f"Method {method_name} already exists, updating last_used")
            existing.last_used = datetime.now().isoformat()
        else:
            # Create new method entry
            method = HDDLMethod(
                domain=domain,
                task_name=task_name,
                method_name=method_name,
                hddl_text=hddl_text,
                parameters=parameters,
                preconditions=preconditions,
                subtasks=subtasks,
                ordering=ordering,
                success_count=1,
                last_used=datetime.now().isoformat()
            )
            
            # Add to in-memory storage
            if domain not in self.methods:
                self.methods[domain] = {}
            
            if task_name not in self.methods[domain]:
                self.methods[domain][task_name] = []
            
            self.methods[domain][task_name].append(method)
            
            logger.info(f"Stored new HDDL method: {method_name} for task {task_name}")
        
        # Persist to disk
        self._save()
    
    def retrieve_method(
        self,
        domain: str,
        task_name: str,
        context: Optional[Dict[str, any]] = None
    ) -> Optional[HDDLMethod]:
        """
        Retrieve best-matching HDDL method for a task
        
        Args:
            domain: Domain name
            task_name: Task to decompose
            context: Optional context for matching (state, parameters, etc.)
        
        Returns:
            Best HDDLMethod or None if no match
        """
        if domain not in self.methods or task_name not in self.methods[domain]:
            return None
        
        candidates = self.methods[domain][task_name]
        
        if not candidates:
            return None
        
        # Ranking criteria:
        # 1. Highest success rate
        # 2. Most recent usage
        # 3. Most uses (success_count)
        
        ranked = sorted(
            candidates,
            key=lambda m: (m.success_rate, m.last_used or "", m.success_count),
            reverse=True
        )
        
        best_method = ranked[0]
        
        # Update last_used
        best_method.last_used = datetime.now().isoformat()
        self._save()
        
        logger.info(
            f"Retrieved method {best_method.method_name} "
            f"(success_rate={best_method.success_rate:.2f})"
        )
        
        return best_method
    
    def update_success(
        self,
        domain: str,
        task_name: str,
        method_name: str,
        success: bool
    ) -> None:
        """
        Update success/failure statistics for a method
        
        Args:
            domain: Domain name
            task_name: Task name
            method_name: Method name
            success: True if planning succeeded, False if failed
        """
        method = self._find_method(domain, task_name, method_name)
        
        if not method:
            logger.warning(f"Method {method_name} not found for update")
            return
        
        if success:
            method.success_count += 1
            logger.info(f"Method {method_name} success_count: {method.success_count}")
        else:
            method.failure_count += 1
            logger.info(f"Method {method_name} failure_count: {method.failure_count}")
        
        method.last_used = datetime.now().isoformat()
        
        self._save()
    
    def get_all_methods_for_task(
        self,
        domain: str,
        task_name: str
    ) -> List[HDDLMethod]:
        """
        Get all stored methods for a task
        
        Args:
            domain: Domain name
            task_name: Task name
        
        Returns:
            List of HDDLMethod objects (sorted by success rate)
        """
        if domain not in self.methods or task_name not in self.methods[domain]:
            return []
        
        methods = self.methods[domain][task_name]
        return sorted(methods, key=lambda m: m.success_rate, reverse=True)
    
    def get_statistics(self) -> Dict[str, any]:
        """Get library statistics"""
        total_methods = 0
        total_successes = 0
        total_failures = 0
        domains_count = len(self.methods)
        tasks_count = 0
        
        for domain, tasks in self.methods.items():
            tasks_count += len(tasks)
            for task_name, method_list in tasks.items():
                total_methods += len(method_list)
                for method in method_list:
                    total_successes += method.success_count
                    total_failures += method.failure_count
        
        return {
            "total_methods": total_methods,
            "domains": domains_count,
            "tasks": tasks_count,
            "total_successes": total_successes,
            "total_failures": total_failures,
            "overall_success_rate": total_successes / (total_successes + total_failures) 
                                     if (total_successes + total_failures) > 0 else 0.0
        }
    
    def _find_method(
        self,
        domain: str,
        task_name: str,
        method_name: str
    ) -> Optional[HDDLMethod]:
        """Find specific method by name"""
        if domain not in self.methods or task_name not in self.methods[domain]:
            return None
        
        for method in self.methods[domain][task_name]:
            if method.method_name == method_name:
                return method
        
        return None
    
    def _load(self) -> None:
        """Load methods from disk"""
        if not self.storage_path.exists():
            logger.info(f"No existing method library at {self.storage_path}, starting fresh")
            return
        
        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
            
            # Reconstruct in-memory structure
            for domain, tasks in data.items():
                self.methods[domain] = {}
                for task_name, method_list in tasks.items():
                    self.methods[domain][task_name] = [
                        HDDLMethod(**method_data) for method_data in method_list
                    ]
            
            logger.info(f"Loaded {self.get_statistics()['total_methods']} methods from {self.storage_path}")
            
        except Exception as e:
            logger.error(f"Failed to load method library: {e}")
            self.methods = {}
    
    def _save(self) -> None:
        """Save methods to disk"""
        try:
            # Convert to JSON-serializable format
            data = {}
            for domain, tasks in self.methods.items():
                data[domain] = {}
                for task_name, method_list in tasks.items():
                    data[domain][task_name] = [
                        asdict(method) for method in method_list
                    ]
            
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Saved method library to {self.storage_path}")
            
        except Exception as e:
            logger.error(f"Failed to save method library: {e}")
    
    def clear_domain(self, domain: str) -> None:
        """Clear all methods for a domain"""
        if domain in self.methods:
            del self.methods[domain]
            self._save()
            logger.info(f"Cleared all methods for domain: {domain}")
    
    def export_to_hddl(self, domain: str, output_path: str) -> None:
        """
        Export all methods for a domain as a single HDDL file
        
        Args:
            domain: Domain name
            output_path: Output file path
        """
        if domain not in self.methods:
            logger.warning(f"No methods found for domain {domain}")
            return
        
        hddl_parts = []
        hddl_parts.append(f"; HDDL Methods for domain: {domain}")
        hddl_parts.append("; Generated from PANDA Method Library")
        hddl_parts.append(f"; Total methods: {sum(len(m) for m in self.methods[domain].values())}\n")
        
        for task_name, method_list in sorted(self.methods[domain].items()):
            hddl_parts.append(f"; Methods for task: {task_name}")
            for method in method_list:
                hddl_parts.append(method.hddl_text)
                hddl_parts.append("")
        
        output = "\n".join(hddl_parts)
        
        with open(output_path, 'w') as f:
            f.write(output)
        
        logger.info(f"Exported HDDL methods to {output_path}")
