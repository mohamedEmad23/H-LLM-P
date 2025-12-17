"""
Test Domain Persistence System
Verifies that the DomainRegistry, LLM feedback loop, and method library work correctly
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from src.integrations.domain_registry import DomainRegistry, RegisteredDomain
from src.integrations.panda_method_library import PANDAMethodLibrary


class TestDomainPersistence:
    """Test suite for domain persistence system"""
    
    def __init__(self):
        # Use test-specific paths
        self.test_dir = Path("./tests/test_results")
        self.test_dir.mkdir(parents=True, exist_ok=True)
        
        self.registry_path = str(self.test_dir / "test_domain_registry.json")
        self.method_library_path = str(self.test_dir / "test_method_library.json")
        self.domains_path = str(self.test_dir / "test_domains")
        
    def test_domain_registry_basic(self):
        """Test basic DomainRegistry operations"""
        print("\n" + "=" * 60)
        print("TEST 1: Domain Registry Basic Operations")
        print("=" * 60)
        
        # Create fresh registry
        registry = DomainRegistry(
            registry_path=self.registry_path,
            domains_base_path=self.domains_path
        )
        
        # Clear any existing data
        registry.clear_all()
        
        # Create a test domain file first
        test_domain_dir = Path(self.domains_path) / "test_graph_traversal"
        test_domain_dir.mkdir(parents=True, exist_ok=True)
        
        test_domain_file = test_domain_dir / "domain.hddl"
        test_problem_file = test_domain_dir / "problem.hddl"
        
        # Write test HDDL content
        test_domain_file.write_text("""(define (domain test_graph_traversal)
  (:requirements :hierarchy :typing)
  (:types node - object)
  (:predicates (at ?n - node))
)""")
        test_problem_file.write_text("""(define (problem test)
  (:domain test_graph_traversal)
  (:objects A B - node)
  (:init (at A))
)""")
        
        # Test 1: Register a domain
        print("\n[1.1] Registering a new domain...")
        domain = registry.register_domain(
            domain_name="test_graph_traversal",
            domain_file=str(test_domain_file),
            problem_file=str(test_problem_file),
            method_count=5,
            action_count=3,
            predicate_count=4,
            generation_time_ms=1500.5,
            source="llm_generated",
            llm_provider="groq",
            llm_model="llama-70b",
            panda_validated=True
        )
        
        assert domain is not None, "Domain registration failed"
        assert domain.domain_name == "test_graph_traversal", "Domain name mismatch"
        assert domain.method_count == 5, "Method count mismatch"
        print(f"  ✓ Domain registered: {domain.domain_name}")
        print(f"    - Methods: {domain.method_count}")
        print(f"    - Source: {domain.source}")
        print(f"    - LLM: {domain.llm_provider}")
        
        # Test 2: Lookup domain
        print("\n[1.2] Looking up registered domain...")
        found = registry.lookup_domain("test_graph_traversal")
        assert found is not None, "Domain lookup failed"
        assert found.usage_count >= 1, "Usage count not incremented"
        print(f"  ✓ Domain found: {found.domain_name}")
        print(f"    - Usage count: {found.usage_count}")
        print(f"    - Success rate: {found.success_rate:.2%}")
        
        # Test 3: Update success
        print("\n[1.3] Updating success statistics...")
        registry.update_success("test_graph_traversal", success=True)
        registry.update_success("test_graph_traversal", success=True)
        registry.update_success("test_graph_traversal", success=False)
        
        found = registry.lookup_domain("test_graph_traversal")
        assert found.success_count >= 3, "Success count mismatch"
        assert found.failure_count >= 1, "Failure count mismatch"
        print(f"  ✓ Stats updated:")
        print(f"    - Success count: {found.success_count}")
        print(f"    - Failure count: {found.failure_count}")
        print(f"    - Success rate: {found.success_rate:.2%}")
        
        # Test 4: List domains
        print("\n[1.4] Listing all domains...")
        all_domains = registry.list_domains()
        assert len(all_domains) >= 1, "No domains found"
        print(f"  ✓ Found {len(all_domains)} domains")
        for d in all_domains:
            print(f"    - {d.domain_name} (used {d.usage_count} times)")
        
        # Test 5: Get statistics
        print("\n[1.5] Getting registry statistics...")
        stats = registry.get_statistics()
        print(f"  ✓ Registry stats:")
        print(f"    - Total domains: {stats['total_domains']}")
        print(f"    - LLM generated: {stats['llm_generated']}")
        print(f"    - Total usage: {stats['total_usage']}")
        print(f"    - Lookup hit rate: {stats['lookup_hit_rate']:.2%}")
        
        print("\n✓ TEST 1 PASSED: Domain Registry basic operations work correctly")
        return True
    
    def test_method_library_basic(self):
        """Test basic PANDAMethodLibrary operations"""
        print("\n" + "=" * 60)
        print("TEST 2: Method Library Basic Operations")
        print("=" * 60)
        
        # Create fresh library
        library = PANDAMethodLibrary(storage_path=self.method_library_path)
        
        # Test 1: Store a method
        print("\n[2.1] Storing a new method...")
        library.store_method(
            domain="test_graph",
            task_name="find_path",
            method_name="find_path_recursive",
            hddl_text="""(:method find_path_recursive
  :parameters (?start ?end)
  :task (find_path ?start ?end)
  :precondition (and (at ?start))
  :subtasks (and (traverse ?start ?mid) (find_path ?mid ?end))
)""",
            parameters={"start": "node", "end": "node"},
            preconditions=["at ?start"],
            subtasks=[{"name": "traverse", "parameters": ["?start", "?mid"]}, 
                      {"name": "find_path", "parameters": ["?mid", "?end"]}],
            ordering=[]
        )
        print("  ✓ Method stored: find_path_recursive")
        
        # Test 2: Retrieve method
        print("\n[2.2] Retrieving stored method...")
        method = library.retrieve_method(
            domain="test_graph",
            task_name="find_path"
        )
        assert method is not None, "Method retrieval failed"
        assert method.method_name == "find_path_recursive", "Method name mismatch"
        print(f"  ✓ Method retrieved: {method.method_name}")
        print(f"    - Task: {method.task_name}")
        print(f"    - Success rate: {method.success_rate:.2%}")
        
        # Test 3: Update success
        print("\n[2.3] Updating method success stats...")
        library.update_success("test_graph", "find_path", "find_path_recursive", success=True)
        library.update_success("test_graph", "find_path", "find_path_recursive", success=True)
        
        method = library.retrieve_method("test_graph", "find_path")
        assert method.success_count >= 3, "Success count mismatch"
        print(f"  ✓ Stats updated:")
        print(f"    - Success count: {method.success_count}")
        print(f"    - Success rate: {method.success_rate:.2%}")
        
        # Test 4: Get statistics
        print("\n[2.4] Getting library statistics...")
        stats = library.get_statistics()
        print(f"  ✓ Library stats:")
        print(f"    - Total methods: {stats['total_methods']}")
        print(f"    - Domains: {stats['domains']}")
        print(f"    - Tasks: {stats['tasks']}")
        print(f"    - Overall success rate: {stats['overall_success_rate']:.2%}")
        
        print("\n✓ TEST 2 PASSED: Method Library basic operations work correctly")
        return True
    
    def test_domain_persistence_flow(self):
        """Test the complete domain persistence flow"""
        print("\n" + "=" * 60)
        print("TEST 3: Complete Domain Persistence Flow")
        print("=" * 60)
        
        # Create registry
        registry = DomainRegistry(
            registry_path=self.registry_path,
            domains_base_path=self.domains_path
        )
        
        # Test 1: Check for non-existent domain
        print("\n[3.1] Checking for non-existent domain...")
        result = registry.lookup_domain("new_domain_xyz")
        assert result is None, "Should return None for non-existent domain"
        print("  ✓ Correctly returned None for non-existent domain")
        
        # Test 2: Simulate LLM domain generation and persistence
        print("\n[3.2] Simulating domain persistence from /tmp to ./src/domains...")
        
        # Create a temp domain file
        temp_dir = Path("/tmp/test_panda")
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        temp_domain_file = temp_dir / "test_domain.hddl"
        temp_problem_file = temp_dir / "test_problem.hddl"
        
        # Write test HDDL
        temp_domain_file.write_text("""(define (domain test_persistence)
  (:requirements :hierarchy :typing)
  (:types node - object)
  (:predicates (at ?n - node) (connected ?n1 ?n2 - node))
  (:task find_path :parameters (?start - node ?end - node))
  (:method find_path_direct
    :parameters (?start - node ?end - node)
    :task (find_path ?start ?end)
    :precondition (connected ?start ?end)
    :subtasks (traverse ?start ?end)
  )
  (:action traverse
    :parameters (?from - node ?to - node)
    :precondition (and (at ?from) (connected ?from ?to))
    :effect (and (not (at ?from)) (at ?to))
  )
)""")
        
        temp_problem_file.write_text("""(define (problem test_problem)
  (:domain test_persistence)
  (:objects A B C - node)
  (:init (at A) (connected A B) (connected B C))
  (:goal (at C))
)""")
        
        # Persist the files
        persisted = registry.persist_domain_files(
            domain_name="test_persistence",
            temp_domain_file=str(temp_domain_file),
            temp_problem_file=str(temp_problem_file)
        )
        
        assert persisted["domain_file"] is not None, "Domain file not persisted"
        assert Path(persisted["domain_file"]).exists(), "Persisted domain file doesn't exist"
        print(f"  ✓ Domain persisted to: {persisted['domain_file']}")
        
        # Register the domain
        registry.register_domain(
            domain_name="test_persistence",
            domain_file=persisted["domain_file"],
            problem_file=persisted.get("problem_file"),
            method_count=1,
            action_count=1,
            source="llm_generated",
            panda_validated=True
        )
        print("  ✓ Domain registered in registry")
        
        # Test 3: Verify we can look it up
        print("\n[3.3] Verifying domain can be looked up...")
        found = registry.lookup_domain("test_persistence")
        assert found is not None, "Persisted domain not found"
        assert Path(found.domain_file).exists(), "Domain file doesn't exist"
        print(f"  ✓ Domain found: {found.domain_name}")
        print(f"    - File: {found.domain_file}")
        print(f"    - Exists: {Path(found.domain_file).exists()}")
        
        print("\n✓ TEST 3 PASSED: Complete persistence flow works correctly")
        return True
    
    def test_scan_existing_domains(self):
        """Test scanning existing domains into registry"""
        print("\n" + "=" * 60)
        print("TEST 4: Scan Existing Domains")
        print("=" * 60)
        
        # Create fresh registry pointing to actual domains
        registry = DomainRegistry(
            registry_path=str(self.test_dir / "scan_test_registry.json"),
            domains_base_path="./src/domains"
        )
        
        # Clear and scan
        registry.clear_all()
        
        print("\n[4.1] Scanning ./src/domains for existing domains...")
        scanned = registry.scan_existing_domains()
        print(f"  ✓ Scanned {scanned} new domains")
        
        # List what we found
        all_domains = registry.list_domains()
        print(f"\n[4.2] Found domains:")
        for d in all_domains:
            print(f"    - {d.domain_name}")
            print(f"      File: {d.domain_file}")
            print(f"      Source: {d.source}")
        
        print("\n✓ TEST 4 PASSED: Domain scanning works correctly")
        return True
    
    def cleanup(self):
        """Clean up test files"""
        import shutil
        
        print("\n" + "-" * 60)
        print("Cleaning up test files...")
        
        # Remove test directory
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
            print(f"  ✓ Removed {self.test_dir}")
        
        # Remove temp files
        temp_dir = Path("/tmp/test_panda")
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            print(f"  ✓ Removed {temp_dir}")
    
    def run_all_tests(self, cleanup_after: bool = True):
        """Run all tests"""
        print("\n" + "=" * 70)
        print("  DOMAIN PERSISTENCE TEST SUITE")
        print("  Testing: DomainRegistry, PANDAMethodLibrary, Persistence Flow")
        print("=" * 70)
        
        results = []
        
        try:
            results.append(("Domain Registry Basic", self.test_domain_registry_basic()))
            results.append(("Method Library Basic", self.test_method_library_basic()))
            results.append(("Persistence Flow", self.test_domain_persistence_flow()))
            results.append(("Scan Existing Domains", self.test_scan_existing_domains()))
        except Exception as e:
            logger.error(f"Test failed with error: {e}")
            import traceback
            traceback.print_exc()
            results.append(("ERROR", False))
        
        if cleanup_after:
            self.cleanup()
        
        # Summary
        print("\n" + "=" * 70)
        print("  TEST SUMMARY")
        print("=" * 70)
        
        passed = sum(1 for _, r in results if r)
        total = len(results)
        
        for name, result in results:
            status = "✓ PASSED" if result else "✗ FAILED"
            print(f"  {status}: {name}")
        
        print("-" * 70)
        print(f"  Total: {passed}/{total} tests passed")
        print("=" * 70)
        
        return passed == total


def main():
    """Run tests"""
    test_suite = TestDomainPersistence()
    success = test_suite.run_all_tests(cleanup_after=True)
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())

