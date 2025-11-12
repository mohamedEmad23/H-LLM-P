"""Problem CLI for loading and validating YAML problem definitions.

This module provides the interface for users to submit arbitrary problems
to the HTN planning system via YAML configuration files.
"""

import yaml
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class Problem:
    """Represents a problem instance loaded from YAML."""

    problem_type: str
    description: str
    initial_state: Dict[str, Any]
    constraints: Dict[str, Any]
    expected_output: Dict[str, Any]
    metadata: Dict[str, Any]
    domain_hints: Dict[str, Any]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Problem":
        """Create Problem instance from dictionary.

        Args:
            data: Dictionary containing problem data

        Returns:
            Problem instance

        Raises:
            ValueError: If required fields are missing
        """
        required_fields = [
            "problem_type",
            "description",
            "initial_state",
            "constraints",
            "expected_output",
            "metadata",
            "domain_hints",
        ]

        missing = [f for f in required_fields if f not in data]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")

        return cls(
            problem_type=data["problem_type"],
            description=data["description"],
            initial_state=data["initial_state"],
            constraints=data["constraints"],
            expected_output=data["expected_output"],
            metadata=data["metadata"],
            domain_hints=data["domain_hints"],
        )


class ProblemLoader:
    """Loads and validates YAML problem definitions."""

    def __init__(self, problems_dir: str = "problems"):
        """Initialize the problem loader.

        Args:
            problems_dir: Directory containing YAML problem files
        """
        self.problems_dir = Path(problems_dir)
        if not self.problems_dir.exists():
            raise FileNotFoundError(f"Problems directory not found: {problems_dir}")

    def load_problem(self, filename: str) -> Problem:
        """Load a problem from a YAML file.

        Args:
            filename: Name of the YAML file (with or without .yaml extension)

        Returns:
            Problem instance

        Raises:
            FileNotFoundError: If YAML file doesn't exist
            yaml.YAMLError: If YAML is malformed
            ValueError: If required fields are missing
        """
        # Add .yaml extension if not present
        if not filename.endswith(".yaml"):
            filename = f"{filename}.yaml"

        filepath = self.problems_dir / filename

        if not filepath.exists():
            raise FileNotFoundError(f"Problem file not found: {filepath}")

        try:
            with open(filepath, "r") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Invalid YAML in {filename}: {e}")

        # Validate and create Problem instance
        problem = Problem.from_dict(data)

        # Additional validation
        self._validate_problem(problem)

        return problem

    def _validate_problem(self, problem: Problem) -> None:
        """Validate problem fields.

        Args:
            problem: Problem instance to validate

        Raises:
            ValueError: If validation fails
        """
        # Validate metadata
        if "difficulty" not in problem.metadata:
            raise ValueError("metadata.difficulty is required")

        valid_difficulties = ["easy", "medium", "hard", "very hard"]
        if problem.metadata["difficulty"].lower() not in valid_difficulties:
            raise ValueError(
                f"Invalid difficulty: {problem.metadata['difficulty']}. "
                f"Must be one of {valid_difficulties}"
            )

        # Validate domain_hints
        required_hints = ["primary_task", "subtasks", "key_operators"]
        missing_hints = [h for h in required_hints if h not in problem.domain_hints]
        if missing_hints:
            raise ValueError(f"Missing domain_hints: {missing_hints}")

        # Validate subtasks and operators are lists
        if not isinstance(problem.domain_hints["subtasks"], list):
            raise ValueError("domain_hints.subtasks must be a list")
        if not isinstance(problem.domain_hints["key_operators"], list):
            raise ValueError("domain_hints.key_operators must be a list")

    def list_problems(self) -> List[str]:
        """List all available problem files.

        Returns:
            List of problem filenames (without .yaml extension)
        """
        return [f.stem for f in self.problems_dir.glob("*.yaml")]

    def load_all_problems(self) -> Dict[str, Problem]:
        """Load all problems from the problems directory.

        Returns:
            Dictionary mapping problem names to Problem instances
        """
        problems = {}
        for filename in self.list_problems():
            try:
                problems[filename] = self.load_problem(filename)
            except Exception as e:
                print(f"Warning: Failed to load {filename}: {e}", file=sys.stderr)

        return problems


class ProblemCLI:
    """Command-line interface for problem submission."""

    def __init__(self, problems_dir: str = "problems"):
        """Initialize the CLI.

        Args:
            problems_dir: Directory containing YAML problem files
        """
        self.loader = ProblemLoader(problems_dir)

    def run_interactive(self) -> None:
        """Run interactive REPL mode for problem submission."""
        print("=" * 60)
        print("HTN Planning System - Problem CLI")
        print("=" * 60)
        print("\nAvailable commands:")
        print("  list               - List all available problems")
        print("  load <problem>     - Load and validate a problem")
        print("  solve <problem>    - Load and solve a problem")
        print("  help               - Show this help message")
        print("  exit               - Exit the CLI")
        print()

        while True:
            try:
                command = input(">>> ").strip()

                if not command:
                    continue

                parts = command.split(maxsplit=1)
                cmd = parts[0].lower()
                args = parts[1] if len(parts) > 1 else ""

                if cmd == "exit":
                    print("Goodbye!")
                    break
                elif cmd == "help":
                    self._show_help()
                elif cmd == "list":
                    self._list_problems()
                elif cmd == "load":
                    if not args:
                        print("Error: Please specify a problem name")
                        continue
                    self._load_problem(args)
                elif cmd == "solve":
                    if not args:
                        print("Error: Please specify a problem name")
                        continue
                    self._solve_problem(args)
                else:
                    print(
                        f"Unknown command: {cmd}. Type 'help' for available commands."
                    )

            except KeyboardInterrupt:
                print("\nUse 'exit' to quit")
            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)

    def _show_help(self) -> None:
        """Show help message."""
        print("\nCommands:")
        print("  list               - List all available problems")
        print("  load <problem>     - Load and validate a problem")
        print("  solve <problem>    - Load and solve a problem")
        print("  help               - Show this help message")
        print("  exit               - Exit the CLI")

    def _list_problems(self) -> None:
        """List all available problems."""
        problems = self.loader.list_problems()

        if not problems:
            print("No problems found in the problems directory.")
            return

        print(f"\nAvailable problems ({len(problems)}):")
        for i, name in enumerate(problems, 1):
            print(f"  {i}. {name}")

    def _load_problem(self, problem_name: str) -> Optional[Problem]:
        """Load and display a problem.

        Args:
            problem_name: Name of the problem to load

        Returns:
            Problem instance if successful, None otherwise
        """
        try:
            problem = self.loader.load_problem(problem_name)

            print("\n" + "=" * 60)
            print(f"Problem: {problem.problem_type}")
            print("=" * 60)
            print(f"\nDescription:\n{problem.description}")
            print(f"\nDifficulty: {problem.metadata['difficulty']}")
            print(f"Category: {problem.metadata.get('category', 'N/A')}")

            if "tags" in problem.metadata:
                print(f"Tags: {', '.join(problem.metadata['tags'])}")

            print("\nInitial State:")
            self._print_yaml(problem.initial_state, indent=2)

            print("\nConstraints:")
            self._print_yaml(problem.constraints, indent=2)

            print("\nExpected Output:")
            self._print_yaml(problem.expected_output, indent=2)

            print("\nDomain Hints:")
            print(f"  Primary Task: {problem.domain_hints['primary_task']}")
            print(f"  Subtasks: {', '.join(problem.domain_hints['subtasks'])}")
            print(
                f"  Key Operators: {', '.join(problem.domain_hints['key_operators'])}"
            )

            print("\n✓ Problem loaded and validated successfully!")

            return problem

        except Exception as e:
            print(f"Error loading problem: {e}", file=sys.stderr)
            return None

    def _solve_problem(self, problem_name: str) -> None:
        """Load and solve a problem.

        Args:
            problem_name: Name of the problem to solve
        """
        problem = self._load_problem(problem_name)

        if problem is None:
            return

        print("\n" + "-" * 60)
        print("Initiating HTN planning...")
        print("-" * 60)

        # Import orchestrator here to avoid circular imports
        try:
            from ..planning.domain_mapper import DomainMapper
            from ..core.orchestrator import Orchestrator

            print("\n[1/3] Mapping problem to HTN domain...")
            mapper = DomainMapper()
            domain = mapper.map_problem_to_domain(problem)

            print(f"✓ Domain: {domain.name}")

            print("\n[2/3] Initializing HTN planner...")
            orchestrator = Orchestrator()

            print("\n[3/3] Executing plan...")
            result = orchestrator.solve_problem(problem, domain)

            print("\n" + "=" * 60)
            print("Solution:")
            print("=" * 60)
            self._print_yaml(result, indent=2)

        except ImportError as e:
            print(f"\nError: Required modules not found: {e}", file=sys.stderr)
            print("The planning system may not be fully implemented yet.")
        except Exception as e:
            print(f"\nError during planning: {e}", file=sys.stderr)

    @staticmethod
    def _print_yaml(data: Any, indent: int = 0) -> None:
        """Pretty print YAML data.

        Args:
            data: Data to print
            indent: Indentation level
        """
        yaml_str = yaml.dump(data, default_flow_style=False, sort_keys=False)
        for line in yaml_str.splitlines():
            print(" " * indent + line)


def main() -> None:
    """Main entry point for the CLI."""
    import argparse

    parser = argparse.ArgumentParser(description="HTN Planning System - Problem CLI")
    parser.add_argument(
        "--problems-dir",
        default="problems",
        help="Directory containing YAML problem files (default: problems)",
    )
    parser.add_argument(
        "--interactive", "-i", action="store_true", help="Run in interactive REPL mode"
    )
    parser.add_argument(
        "--list", "-l", action="store_true", help="List all available problems"
    )
    parser.add_argument(
        "--load", metavar="PROBLEM", help="Load and validate a specific problem"
    )
    parser.add_argument(
        "--solve", metavar="PROBLEM", help="Load and solve a specific problem"
    )

    args = parser.parse_args()

    try:
        cli = ProblemCLI(args.problems_dir)

        if args.interactive:
            cli.run_interactive()
        elif args.list:
            cli._list_problems()
        elif args.load:
            cli._load_problem(args.load)
        elif args.solve:
            cli._solve_problem(args.solve)
        else:
            # Default to interactive mode
            cli.run_interactive()

    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
