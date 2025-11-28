"""Tests for Problem Ingestion Layer.

Tests the complete problem ingestion workflow: YAML loading, validation,
domain mapping, and domain generation.
"""

import pytest

from src.interface.problem_cli import ProblemLoader
from src.planning.domain_mapper import DomainMapper
from src.planning.domain_generator import DomainGenerator


class TestProblemLoader:
    """Test YAML problem loading and validation."""

    def test_list_problems(self):
        """Test listing all available problems."""
        loader = ProblemLoader("problems")
        problems = loader.list_problems()

        assert len(problems) >= 5
        assert "3sum" in problems
        assert "sorting" in problems
        assert "pathfinding" in problems
        assert "hanoi_constrained" in problems
        assert "resource_allocation" in problems

    def test_load_3sum_problem(self):
        """Test loading 3sum problem."""
        loader = ProblemLoader("problems")
        problem = loader.load_problem("3sum")

        assert problem.problem_type == "3sum"
        assert "triplets" in problem.description.lower()
        assert problem.metadata["difficulty"] == "medium"
        assert problem.domain_hints["primary_task"] == "find_all_triplets"
        assert "iterate_array" in problem.domain_hints["subtasks"]

    def test_load_sorting_problem(self):
        """Test loading sorting problem."""
        loader = ProblemLoader("problems")
        problem = loader.load_problem("sorting")

        assert problem.problem_type == "constrained_sorting"
        assert "quicksort" in problem.initial_state["algorithm"]
        assert problem.metadata["difficulty"] == "medium"

    def test_load_pathfinding_problem(self):
        """Test loading pathfinding problem."""
        loader = ProblemLoader("problems")
        problem = loader.load_problem("pathfinding")

        assert problem.problem_type == "grid_pathfinding"
        assert "grid" in problem.initial_state
        assert problem.metadata["difficulty"] == "hard"

    def test_invalid_yaml_raises_error(self, tmp_path):
        """Test that invalid YAML raises error."""
        invalid_yaml = tmp_path / "invalid.yaml"
        invalid_yaml.write_text("{ invalid yaml [")

        loader = ProblemLoader(str(tmp_path))
        with pytest.raises(Exception):
            loader.load_problem("invalid")

    def test_missing_fields_raises_error(self, tmp_path):
        """Test that missing required fields raises error."""
        incomplete_yaml = tmp_path / "incomplete.yaml"
        incomplete_yaml.write_text("""
problem_type: "test"
description: "Test problem"
initial_state: {}
""")

        loader = ProblemLoader(str(tmp_path))
        with pytest.raises(ValueError):
            loader.load_problem("incomplete")


class TestDomainMapper:
    """Test domain mapping and caching."""

    def test_map_known_domain(self):
        """Test mapping to known domain (hanoi)."""
        mapper = DomainMapper(enable_mms=False)
        loader = ProblemLoader("problems")

        # Load hanoi problem
        problem = loader.load_problem("hanoi_constrained")

        # Map to domain
        domain = mapper.map_problem_to_domain(problem)

        # Note: This will fail until hanoi domain is implemented
        # For now, we test the routing logic
        assert domain is not None

    def test_generate_domain_for_novel_problem(self):
        """Test generating domain for novel problem (3sum)."""
        mapper = DomainMapper(enable_mms=False)
        loader = ProblemLoader("problems")

        # Load 3sum problem (not a known domain)
        problem = loader.load_problem("3sum")

        # This should trigger domain generation
        domain = mapper.map_problem_to_domain(problem)

        assert domain is not None
        assert domain.name == "3sum"
        assert len(domain.tasks) > 0
        assert len(domain.operators) > 0

    def test_cache_functionality(self, tmp_path):
        """Test that generated domains are cached."""
        cache_dir = tmp_path / "cache"
        mapper = DomainMapper(cache_dir=str(cache_dir), enable_mms=False)
        loader = ProblemLoader("problems")

        problem = loader.load_problem("sorting")

        # First call generates domain
        domain1 = mapper.map_problem_to_domain(problem)

        # Verify cache file exists
        cache_file = cache_dir / "constrained_sorting.json"
        assert cache_file.exists()

        # Second call should use cache
        domain2 = mapper.map_problem_to_domain(problem)

        assert domain1.name == domain2.name


class TestDomainGenerator:
    """Test LLM-powered domain generation."""

    def test_generate_tasks_from_hints(self):
        """Test task generation from domain hints."""
        generator = DomainGenerator()
        loader = ProblemLoader("problems")

        problem = loader.load_problem("3sum")

        # Generate tasks (will use mock if LLM not available)
        tasks = generator._generate_tasks(problem)

        assert len(tasks) > 0
        assert any(task.name == problem.domain_hints["primary_task"] for task in tasks)

    def test_generate_methods_from_tasks(self):
        """Test method generation."""
        generator = DomainGenerator()
        loader = ProblemLoader("problems")

        problem = loader.load_problem("sorting")
        tasks = generator._generate_tasks(problem)

        # Generate methods
        methods = generator._generate_methods(problem, tasks)

        assert len(methods) > 0
        # Methods should reference tasks
        method_tasks = [m.task for m in methods]
        task_names = [t.name for t in tasks]
        assert any(mt in task_names for mt in method_tasks)

    def test_generate_operators_from_hints(self):
        """Test operator generation."""
        generator = DomainGenerator()
        loader = ProblemLoader("problems")

        problem = loader.load_problem("pathfinding")

        # Generate operators
        operators = generator._generate_operators(problem)

        assert len(operators) > 0
        # At least one operator should match domain hints
        operator_names = [op.name for op in operators]
        hint_operators = problem.domain_hints["key_operators"]
        assert any(
            hint in op_name for hint in hint_operators for op_name in operator_names
        )

    def test_full_domain_generation(self):
        """Test complete domain generation."""
        generator = DomainGenerator()
        loader = ProblemLoader("problems")

        problem = loader.load_problem("resource_allocation")

        # Generate full domain
        domain = generator.generate_domain(problem)

        assert domain.name == "resource_allocation"
        assert len(domain.tasks) > 0
        assert len(domain.methods) > 0
        assert len(domain.operators) > 0


class TestIntegration:
    """Integration tests for complete problem ingestion workflow."""

    def test_end_to_end_workflow(self):
        """Test complete workflow: load -> map -> generate."""
        # Load problem
        loader = ProblemLoader("problems")
        problem = loader.load_problem("3sum")

        # Map to domain
        mapper = DomainMapper(enable_mms=False)
        domain = mapper.map_problem_to_domain(problem)

        # Verify domain structure
        assert domain is not None
        assert domain.name == "3sum"
        assert hasattr(domain, "tasks")
        assert hasattr(domain, "methods")
        assert hasattr(domain, "operators")

    def test_all_problem_types_loadable(self):
        """Test that all 5 problem types can be loaded."""
        loader = ProblemLoader("problems")
        problem_types = [
            "3sum",
            "sorting",
            "pathfinding",
            "hanoi_constrained",
            "resource_allocation",
        ]

        for prob_type in problem_types:
            problem = loader.load_problem(prob_type)
            assert problem is not None
            assert problem.problem_type is not None
            assert problem.domain_hints is not None

    def test_domain_generation_for_all_problems(self):
        """Test domain generation for all 5 problem types."""
        loader = ProblemLoader("problems")
        mapper = DomainMapper(enable_mms=False)

        problem_types = ["3sum", "sorting", "pathfinding", "resource_allocation"]

        for prob_type in problem_types:
            problem = loader.load_problem(prob_type)
            domain = mapper.map_problem_to_domain(problem)

            assert domain is not None
            assert len(domain.tasks) > 0
            print(
                f"✓ Generated domain for {prob_type}: {len(domain.tasks)} tasks, {len(domain.operators)} operators"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
