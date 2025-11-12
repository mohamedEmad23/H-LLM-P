"""Domain Generator for creating HTN domains using LLM.

This module uses LLMs to generate HTN task hierarchies, methods, and operators
for novel problem types based on problem descriptions and domain hints.
"""

import json
from typing import Dict, Any, List
import re

from ..interface.problem_cli import Problem
from .domain import Domain


class DomainGenerator:
    """Generates HTN domains using LLM for novel problem types."""

    def __init__(
        self,
        llm_provider: str = "huggingface",
        model: str = "meta-llama/Llama-3.3-70B-Instruct",
    ):
        """Initialize the domain generator.

        Args:
            llm_provider: LLM provider to use (huggingface, groq, google, etc.)
            model: Model name to use for generation
        """
        self.llm_provider = llm_provider
        self.model = model
        self._init_llm_client()

    def _init_llm_client(self) -> None:
        """Initialize the LLM client."""
        try:
            from ..llm.llm_factory import LLMFactory

            self.llm_client = LLMFactory.create_client(
                provider=self.llm_provider, model=self.model
            )
        except ImportError:
            print("Warning: LLM client not available, using mock generator")
            self.llm_client = None

    def generate_domain(self, problem: Problem) -> Domain:
        """Generate an HTN domain for a problem using LLM.

        This method uses the problem description and domain_hints to guide
        the LLM in generating appropriate HTN tasks, methods, and operators.

        Args:
            problem: Problem instance with domain_hints

        Returns:
            Generated Domain instance
        """
        # Create domain
        domain = Domain(name=problem.problem_type)
        domain.description = problem.description

        # Generate tasks
        tasks = self._generate_tasks(problem)
        for task in tasks:
            domain.add_task(task)

        # Generate methods
        methods = self._generate_methods(problem, tasks)
        for method in methods:
            domain.add_method(method)

        # Generate operators
        operators = self._generate_operators(problem)
        for operator in operators:
            domain.add_operator(operator)

        return domain

    def _generate_tasks(self, problem: Problem) -> List[Any]:
        """Generate HTN tasks using LLM.

        Args:
            problem: Problem instance with domain_hints

        Returns:
            List of Task instances
        """
        prompt = self._create_task_generation_prompt(problem)

        if self.llm_client:
            response = self.llm_client.generate(prompt, max_tokens=1500)
            tasks_data = self._parse_json_response(response)
        else:
            # Mock generation for testing
            tasks_data = self._mock_generate_tasks(problem)

        tasks = []
        for task_data in tasks_data:
            # Create simplified task (adapt to actual Task structure later)
            task = type(
                "SimpleTask",
                (),
                {
                    "name": task_data["name"],
                    "parameters": task_data.get("parameters", []),
                    "preconditions": task_data.get("preconditions", []),
                    "effects": task_data.get("effects", []),
                },
            )()
            tasks.append(task)

        return tasks

    def _generate_methods(self, problem: Problem, tasks: List[Any]) -> List[Any]:
        """Generate HTN methods (decomposition rules) using LLM.

        Args:
            problem: Problem instance with domain_hints
            tasks: List of tasks for which to generate methods

        Returns:
            List of Method instances
        """
        prompt = self._create_method_generation_prompt(problem, tasks)

        if self.llm_client:
            response = self.llm_client.generate(prompt, max_tokens=2000)
            methods_data = self._parse_json_response(response)
        else:
            # Mock generation for testing
            methods_data = self._mock_generate_methods(problem, tasks)

        methods = []
        for method_data in methods_data:
            # Create simplified method
            method = type(
                "SimpleMethod",
                (),
                {
                    "name": method_data["name"],
                    "task": method_data["task"],
                    "subtasks": method_data.get("subtasks", []),
                    "preconditions": method_data.get("preconditions", []),
                },
            )()
            methods.append(method)

        return methods

    def _generate_operators(self, problem: Problem) -> List[Any]:
        """Generate primitive operators using LLM.

        Args:
            problem: Problem instance with domain_hints

        Returns:
            List of Operator instances
        """
        prompt = self._create_operator_generation_prompt(problem)

        if self.llm_client:
            response = self.llm_client.generate(prompt, max_tokens=1500)
            operators_data = self._parse_json_response(response)
        else:
            # Mock generation for testing
            operators_data = self._mock_generate_operators(problem)

        operators = []
        for op_data in operators_data:
            # Create simplified operator
            operator = type(
                "SimpleOperator",
                (),
                {
                    "name": op_data["name"],
                    "parameters": op_data.get("parameters", []),
                    "preconditions": op_data.get("preconditions", []),
                    "effects": op_data.get("effects", []),
                },
            )()
            operators.append(operator)

        return operators

    def _create_task_generation_prompt(self, problem: Problem) -> str:
        """Create prompt for LLM to generate HTN tasks.

        Args:
            problem: Problem instance

        Returns:
            Prompt string
        """
        return f"""You are an expert in HTN (Hierarchical Task Network) planning. Generate a set of HTN tasks for the following problem.

Problem Type: {problem.problem_type}
Description: {problem.description}

Domain Hints:
- Primary Task: {problem.domain_hints["primary_task"]}
- Subtasks: {", ".join(problem.domain_hints["subtasks"])}
- Key Operators: {", ".join(problem.domain_hints["key_operators"])}

Initial State: {json.dumps(problem.initial_state, indent=2)}
Constraints: {json.dumps(problem.constraints, indent=2)}

Generate a JSON array of HTN tasks. Each task should have:
- name: descriptive name for the task
- parameters: list of parameter names (e.g., ["disk", "from_peg", "to_peg"])
- preconditions: list of conditions that must be true (e.g., ["clear(disk)", "on(disk, from_peg)"])
- effects: list of effects after task completion (e.g., ["on(disk, to_peg)", "not on(disk, from_peg)"])

Start with the primary task and include all subtasks. Return ONLY valid JSON, no explanations.

Example format:
[
  {{
    "name": "sort_array",
    "parameters": ["array", "start", "end"],
    "preconditions": ["valid_indices(start, end)"],
    "effects": ["sorted(array, start, end)"]
  }}
]

Generate the tasks now:"""

    def _create_method_generation_prompt(
        self, problem: Problem, tasks: List[Any]
    ) -> str:
        """Create prompt for LLM to generate HTN methods.

        Args:
            problem: Problem instance
            tasks: List of generated tasks

        Returns:
            Prompt string
        """
        task_names = [t.name for t in tasks]

        return f"""You are an expert in HTN planning. Generate decomposition methods for the following problem.

Problem Type: {problem.problem_type}
Available Tasks: {", ".join(task_names)}

Domain Hints:
- Primary Task: {problem.domain_hints["primary_task"]}
- Subtasks: {", ".join(problem.domain_hints["subtasks"])}

Generate a JSON array of HTN methods. Each method should decompose a task into subtasks.
Each method should have:
- name: descriptive name (e.g., "divide_and_conquer_sort")
- task: name of the task this method decomposes
- subtasks: list of subtask names to achieve the task
- preconditions: list of conditions when this decomposition applies

Methods provide alternative ways to achieve tasks. Return ONLY valid JSON.

Example format:
[
  {{
    "name": "quicksort_method",
    "task": "sort_array",
    "subtasks": ["partition_array", "sort_left_half", "sort_right_half"],
    "preconditions": ["length(array) > 1"]
  }}
]

Generate the methods now:"""

    def _create_operator_generation_prompt(self, problem: Problem) -> str:
        """Create prompt for LLM to generate primitive operators.

        Args:
            problem: Problem instance

        Returns:
            Prompt string
        """
        return f"""You are an expert in HTN planning. Generate primitive operators for the following problem.

Problem Type: {problem.problem_type}
Description: {problem.description}

Domain Hints - Key Operators: {", ".join(problem.domain_hints["key_operators"])}

Constraints: {json.dumps(problem.constraints, indent=2)}

Generate a JSON array of primitive operators. These are atomic actions that directly modify the state.
Each operator should have:
- name: descriptive action name (e.g., "swap_elements", "move_disk")
- parameters: list of parameter names
- preconditions: list of conditions that must be true to execute
- effects: list of state changes after execution (use "not X" for deletions)

Return ONLY valid JSON, no explanations.

Example format:
[
  {{
    "name": "swap",
    "parameters": ["array", "i", "j"],
    "preconditions": ["valid_index(i)", "valid_index(j)"],
    "effects": ["swapped(array, i, j)", "not in_order(array, i, j)"]
  }}
]

Generate the operators now:"""

    def _parse_json_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse JSON from LLM response.

        Args:
            response: LLM response text

        Returns:
            Parsed JSON data
        """
        # Try to extract JSON from markdown code blocks
        json_match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON array directly
            json_match = re.search(r"\[.*\]", response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                raise ValueError(f"No JSON found in response: {response[:200]}")

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON in response: {e}\nResponse: {response[:500]}"
            )

    # Mock generation methods for testing without LLM
    def _mock_generate_tasks(self, problem: Problem) -> List[Dict[str, Any]]:
        """Generate mock tasks for testing."""
        return [
            {
                "name": problem.domain_hints["primary_task"],
                "parameters": ["input", "output"],
                "preconditions": ["valid_input(input)"],
                "effects": ["completed(output)"],
            }
        ] + [
            {
                "name": subtask,
                "parameters": ["data"],
                "preconditions": [],
                "effects": [f"completed_{subtask}(data)"],
            }
            for subtask in problem.domain_hints["subtasks"][:3]  # Limit to 3 subtasks
        ]

    def _mock_generate_methods(
        self, problem: Problem, tasks: List[Any]
    ) -> List[Dict[str, Any]]:
        """Generate mock methods for testing."""
        if not tasks:
            return []

        # Create one method that decomposes primary task into subtasks
        primary_task = tasks[0].name
        subtask_names = [t.name for t in tasks[1:4]]  # Up to 3 subtasks

        return [
            {
                "name": f"decompose_{primary_task}",
                "task": primary_task,
                "subtasks": subtask_names,
                "preconditions": [],
            }
        ]

    def _mock_generate_operators(self, problem: Problem) -> List[Dict[str, Any]]:
        """Generate mock operators for testing."""
        return [
            {
                "name": op,
                "parameters": ["x", "y"],
                "preconditions": [f"can_execute_{op}(x, y)"],
                "effects": [f"executed_{op}(x, y)"],
            }
            for op in problem.domain_hints["key_operators"][:5]  # Limit to 5 operators
        ]
