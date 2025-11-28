"""
PANDA Plan Parser
Parses hierarchical plan output from PANDA into executable format
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from pathlib import Path
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class PlanStep:
    """Single action or task in hierarchical plan"""
    name: str
    parameters: List[str]
    depth: int
    parent_task: Optional[str] = None
    is_primitive: bool = False
    line_number: int = 0


@dataclass
class ExecutionPlan:
    """Parsed hierarchical plan ready for execution"""
    steps: List[PlanStep]
    hierarchy: Dict[str, List[str]]  # task -> subtasks mapping
    primitive_actions: List[PlanStep]
    
    def __str__(self) -> str:
        output = ["=== Hierarchical Plan ==="]
        for step in self.steps:
            indent = "  " * step.depth
            params = ", ".join(step.parameters)
            prim_marker = " [PRIMITIVE]" if step.is_primitive else ""
            output.append(f"{indent}{step.name}({params}){prim_marker}")
        return "\n".join(output)


class PANDAPlanParser:
    """
    Parse PANDA's hierarchical plan output format
    
    PANDA plan format example:
    ```
    root
    -> deliver-package(package1, cityB)
       -> transport-by-truck(package1, truck1, cityA, cityB)
          -> load(package1, truck1, cityA)
          -> drive(truck1, cityA, cityB)
          -> unload(package1, truck1, cityB)
    ```
    """
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset parser state"""
        self.steps: List[PlanStep] = []
        self.hierarchy: Dict[str, List[str]] = {}
        self.parent_stack: List[str] = []
    
    def parse_file(self, plan_file: str) -> ExecutionPlan:
        """
        Parse PANDA plan from file
        
        Args:
            plan_file: Path to plan file
        
        Returns:
            ExecutionPlan object with hierarchical structure
        """
        plan_path = Path(plan_file)
        
        if not plan_path.exists():
            raise FileNotFoundError(f"Plan file not found: {plan_file}")
        
        with open(plan_path, 'r') as f:
            content = f.read()
        
        return self.parse_text(content)
    
    def parse_text(self, plan_text: str) -> ExecutionPlan:
        """
        Parse PANDA plan from text
        
        Args:
            plan_text: Plan as string
        
        Returns:
            ExecutionPlan object
        """
        self.reset()
        lines = plan_text.split('\n')
        
        for line_num, line in enumerate(lines, start=1):
            # Skip empty lines and separator lines
            if not line.strip() or line.startswith("==") or line.startswith("--"):
                continue
            
            # Skip status messages
            if any(x in line for x in ["Found solution", "Search", "Time", "Expanded"]):
                continue
            
            # Parse plan step
            step = self._parse_line(line, line_num)
            if step:
                self.steps.append(step)
                self._update_hierarchy(step)
        
        # Identify primitive actions (leaves of hierarchy tree)
        primitive_actions = self._extract_primitives()
        
        logger.info(f"Parsed plan: {len(self.steps)} total steps, {len(primitive_actions)} primitives")
        
        return ExecutionPlan(
            steps=self.steps,
            hierarchy=self.hierarchy,
            primitive_actions=primitive_actions
        )
    
    def _parse_line(self, line: str, line_num: int) -> Optional[PlanStep]:
        """
        Parse single line of plan
        
        Format: "  -> action-name(param1, param2, ...)"
        Depth determined by indentation
        """
        # Calculate depth from indentation
        # PANDA uses "-> " prefix, each level indented by 3 spaces
        stripped = line.lstrip()
        indent_len = len(line) - len(stripped)
        
        # Handle "root" task (depth 0)
        if stripped == "root":
            step = PlanStep(
                name="root",
                parameters=[],
                depth=0,
                parent_task=None,
                line_number=line_num
            )
            self.parent_stack = ["root"]
            return step
        
        # Calculate depth (3 spaces per level)
        depth = indent_len // 3
        
        # Remove "-> " prefix
        if stripped.startswith("-> "):
            stripped = stripped[3:]
        
        # Parse task/action name and parameters
        # Format: "name(param1, param2, ...)"
        match = re.match(r'([a-zA-Z0-9_-]+)\((.*?)\)', stripped)
        
        if not match:
            # No parameters
            match = re.match(r'([a-zA-Z0-9_-]+)', stripped)
            if match:
                name = match.group(1)
                params = []
            else:
                logger.warning(f"Could not parse line {line_num}: {line}")
                return None
        else:
            name = match.group(1)
            params_str = match.group(2)
            params = [p.strip() for p in params_str.split(',')] if params_str else []
        
        # Determine parent task
        # Parent is the last task at depth-1
        while len(self.parent_stack) > depth:
            self.parent_stack.pop()
        
        parent = self.parent_stack[-1] if self.parent_stack else None
        
        # Create step
        step = PlanStep(
            name=name,
            parameters=params,
            depth=depth,
            parent_task=parent,
            line_number=line_num
        )
        
        # Update parent stack
        if len(self.parent_stack) == depth:
            self.parent_stack.append(name)
        else:
            self.parent_stack[depth] = name
        
        return step
    
    def _update_hierarchy(self, step: PlanStep):
        """Update hierarchy mapping"""
        if step.parent_task:
            if step.parent_task not in self.hierarchy:
                self.hierarchy[step.parent_task] = []
            self.hierarchy[step.parent_task].append(step.name)
    
    def _extract_primitives(self) -> List[PlanStep]:
        """
        Extract primitive actions (leaf nodes in hierarchy)
        
        Primitive actions are tasks that are NOT decomposed further
        """
        all_parents = set(self.hierarchy.keys())
        primitives = []
        
        for step in self.steps:
            # If step name is not in hierarchy keys, it's a leaf (primitive)
            if step.name not in all_parents and step.name != "root":
                step.is_primitive = True
                primitives.append(step)
        
        return primitives
    
    def extract_action_sequence(self, plan: ExecutionPlan) -> List[str]:
        """
        Extract linear action sequence from hierarchical plan
        
        Args:
            plan: ExecutionPlan object
        
        Returns:
            List of action strings in execution order
        """
        actions = []
        for step in plan.primitive_actions:
            if step.parameters:
                action_str = f"{step.name}({', '.join(step.parameters)})"
            else:
                action_str = step.name
            actions.append(action_str)
        
        return actions
    
    def to_dict(self, plan: ExecutionPlan) -> Dict:
        """Convert plan to dictionary format for JSON serialization"""
        return {
            "total_steps": len(plan.steps),
            "primitive_actions": len(plan.primitive_actions),
            "hierarchy": plan.hierarchy,
            "steps": [
                {
                    "name": step.name,
                    "parameters": step.parameters,
                    "depth": step.depth,
                    "parent": step.parent_task,
                    "is_primitive": step.is_primitive,
                    "line": step.line_number
                }
                for step in plan.steps
            ],
            "action_sequence": self.extract_action_sequence(plan)
        }
