"""
Centralized Output Paths Configuration
All PANDA output files are organized under a single results directory.

Directory Structure:
    ./results/panda-results/
    ├── domain_registry.json       # Registered HDDL domains
    ├── problem_cache.json         # Cached problem solutions
    ├── method_library.json        # Stored HDDL methods
    ├── agent_interactions/        # Workflow execution logs
    │   └── session_*.json
    ├── solutions/                 # PANDA plan outputs
    │   └── *.solution, *.plan
    ├── parsed/                    # PANDA parsed files
    │   └── *.parsed
    ├── grounded/                  # PANDA grounded files (SAS+)
    │   └── *.sas
    ├── panda-temp/                # Temporary HDDL files during validation
    │   └── panda_*.hddl
    ├── similarity_index/          # FAISS similarity search index
    │   ├── faiss_index.bin
    │   └── metadata.json
    └── failure_logs/              # Error logs for debugging
        └── *.log
"""

from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class OutputPaths:
    """
    Centralized configuration for all output file paths.
    
    Usage:
        paths = OutputPaths()  # Uses default ./results/panda-results
        paths = OutputPaths(base_dir="./custom/results")
        
        # Access paths
        print(paths.domain_registry)  # ./results/panda-results/domain_registry.json
        print(paths.solutions_dir)    # ./results/panda-results/solutions
    """
    
    # Base directory for all outputs
    base_dir: str = "./results/panda-results"
    
    # Domain storage
    domains_dir: str = "./src/domains"
    
    def __post_init__(self):
        """Ensure all directories exist"""
        self._base = Path(self.base_dir)
        self._domains = Path(self.domains_dir)
        
        # Create all directories
        self._base.mkdir(parents=True, exist_ok=True)
        self._domains.mkdir(parents=True, exist_ok=True)
        
        for subdir in ["agent_interactions", "solutions", "parsed", 
                       "grounded", "panda-temp", "similarity_index", "failure_logs"]:
            (self._base / subdir).mkdir(parents=True, exist_ok=True)
    
    # ========== Registry and Cache Paths ==========
    
    @property
    def domain_registry(self) -> str:
        """Path to domain registry JSON"""
        return str(self._base / "domain_registry.json")
    
    @property
    def problem_cache(self) -> str:
        """Path to problem cache JSON"""
        return str(self._base / "problem_cache.json")
    
    @property
    def method_library(self) -> str:
        """Path to method library JSON"""
        return str(self._base / "method_library.json")
    
    # ========== PANDA Output Directories ==========
    
    @property
    def solutions_dir(self) -> str:
        """Directory for PANDA plan outputs"""
        return str(self._base / "solutions")
    
    @property
    def parsed_dir(self) -> str:
        """Directory for PANDA parsed files"""
        return str(self._base / "parsed")
    
    @property
    def grounded_dir(self) -> str:
        """Directory for grounded SAS+ files"""
        return str(self._base / "grounded")
    
    @property
    def temp_dir(self) -> str:
        """Directory for temporary HDDL files"""
        return str(self._base / "panda-temp")
    
    # ========== Agent Interaction Logs ==========
    
    @property
    def agent_interactions_dir(self) -> str:
        """Directory for workflow execution logs"""
        return str(self._base / "agent_interactions")
    
    @property
    def failure_logs_dir(self) -> str:
        """Directory for error logs"""
        return str(self._base / "failure_logs")
    
    # ========== Similarity Search ==========
    
    @property
    def similarity_index_dir(self) -> str:
        """Directory for FAISS similarity index"""
        return str(self._base / "similarity_index")
    
    # ========== Helper Methods ==========
    
    def solution_file(self, name: str) -> str:
        """Get path for a solution file"""
        return str(self._base / "solutions" / f"{name}.solution")
    
    def plan_file(self, name: str) -> str:
        """Get path for an HDDL plan file"""
        return str(self._base / "solutions" / f"{name}.plan")
    
    def parsed_file(self, name: str) -> str:
        """Get path for a parsed file"""
        return str(self._base / "parsed" / f"{name}.parsed")
    
    def grounded_file(self, name: str) -> str:
        """Get path for a grounded SAS+ file"""
        return str(self._base / "grounded" / f"{name}.sas")
    
    def temp_hddl(self, domain: str, attempt: int, file_type: str = "domain") -> str:
        """Get path for a temporary HDDL file"""
        return str(self._base / "panda-temp" / f"panda_{domain}_{file_type}_{attempt}.hddl")
    
    def workflow_log(self, session_id: str) -> str:
        """Get path for a workflow execution log"""
        return str(self._base / "agent_interactions" / f"{session_id}_workflow.json")
    
    def domain_path(self, domain_name: str) -> Path:
        """Get path to a domain directory"""
        return self._domains / domain_name.lower().replace(" ", "_").replace("-", "_")
    
    def domain_hddl(self, domain_name: str) -> str:
        """Get path to domain.hddl for a domain"""
        return str(self.domain_path(domain_name) / "domain.hddl")
    
    def problem_hddl(self, domain_name: str) -> str:
        """Get path to problem.hddl for a domain"""
        return str(self.domain_path(domain_name) / "problem.hddl")
    
    def list_files(self, directory: str = None) -> dict:
        """
        List all files in the output directories
        
        Returns:
            Dict with directory names as keys and file lists as values
        """
        result = {}
        
        dirs_to_list = ["solutions", "parsed", "grounded", "panda-temp", 
                        "agent_interactions", "similarity_index"]
        
        if directory:
            dirs_to_list = [directory]
        
        for dir_name in dirs_to_list:
            dir_path = self._base / dir_name
            if dir_path.exists():
                files = [f.name for f in dir_path.iterdir() if f.is_file()]
                result[dir_name] = files
        
        return result
    
    def get_summary(self) -> dict:
        """
        Get summary of output files
        
        Returns:
            Dict with counts and paths
        """
        files = self.list_files()
        
        return {
            "base_dir": str(self._base),
            "domains_dir": str(self._domains),
            "file_counts": {k: len(v) for k, v in files.items()},
            "registry_exists": Path(self.domain_registry).exists(),
            "cache_exists": Path(self.problem_cache).exists(),
            "method_library_exists": Path(self.method_library).exists()
        }


# ============================================================================
# Singleton instance for easy import
# ============================================================================

# Default instance - can be imported directly
DEFAULT_PATHS = OutputPaths()


def get_output_paths(base_dir: Optional[str] = None) -> OutputPaths:
    """
    Get output paths configuration
    
    Args:
        base_dir: Optional custom base directory
    
    Returns:
        OutputPaths instance
    """
    if base_dir:
        return OutputPaths(base_dir=base_dir)
    return DEFAULT_PATHS


# ============================================================================
# Quick test
# ============================================================================

if __name__ == "__main__":
    paths = OutputPaths()
    
    print("=" * 60)
    print("  OUTPUT PATHS CONFIGURATION")
    print("=" * 60)
    
    print(f"\nBase Directory: {paths.base_dir}")
    print(f"Domains Directory: {paths.domains_dir}")
    
    print(f"\nRegistry Files:")
    print(f"  Domain Registry: {paths.domain_registry}")
    print(f"  Problem Cache: {paths.problem_cache}")
    print(f"  Method Library: {paths.method_library}")
    
    print(f"\nPANDA Output Directories:")
    print(f"  Solutions: {paths.solutions_dir}")
    print(f"  Parsed: {paths.parsed_dir}")
    print(f"  Grounded: {paths.grounded_dir}")
    print(f"  Temp: {paths.temp_dir}")
    
    print(f"\nAgent Logs:")
    print(f"  Interactions: {paths.agent_interactions_dir}")
    print(f"  Failures: {paths.failure_logs_dir}")
    
    print(f"\nSummary:")
    summary = paths.get_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    print("=" * 60)

