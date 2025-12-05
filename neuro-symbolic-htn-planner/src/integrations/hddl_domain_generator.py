"""
HDDL Domain Generator
Converts LLM-generated Method objects to valid HDDL syntax for PANDA framework
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple
import logging

from ..core.methods import Method, MethodLibrary
from ..core.operator import Operator
from ..core.state_manager import State

logger = logging.getLogger(__name__)


@dataclass
class HDDLDomain:
    """Complete HDDL domain specification"""
    domain_name: str
    predicates: List[str]
    compound_tasks: List[str]
    primitive_actions: List[str]
    methods: List[str]
    hddl_text: str


@dataclass
class HDDLProblem:
    """HDDL problem specification"""
    problem_name: str
    domain_name: str
    objects: Dict[str, str]  # object_name -> type
    init_state: List[str]
    goal_tasks: List[str]
    hddl_text: str


class HDDLDomainGenerator:
    """
    Generate HDDL domain and problem files from LLM-generated components
    
    Converts:
    - Method objects → HDDL method declarations
    - Operator objects → HDDL action declarations
    - State objects → HDDL init/goal specifications
    
    Ensures valid HDDL syntax for PANDA parser
    """
    
    def __init__(self):
        self.generated_predicates: Set[str] = set()
        self.generated_types: Set[str] = set()
    
    def generate_domain(
        self,
        domain_name: str,
        methods: MethodLibrary,
        operators: List[Operator],
        predicates: Optional[List[str]] = None
    ) -> HDDLDomain:
        """
        Generate complete HDDL domain file
        
        Args:
            domain_name: Name of the domain
            methods: MethodLibrary with LLM-generated methods
            operators: List of primitive operators
            predicates: Optional explicit predicates (inferred if not provided)
        
        Returns:
            HDDLDomain object with complete HDDL text
        """
        # Infer predicates from operators if not provided
        if predicates is None:
            predicates = self._infer_predicates(operators, methods)
        
        # Generate HDDL sections
        hddl_parts = []
        
        # Header
        hddl_parts.append(f"(define (domain {domain_name})")
        
        # Predicates section
        hddl_parts.append("\n  (:predicates")
        for pred in sorted(predicates):
            hddl_parts.append(f"    {pred}")
        hddl_parts.append("  )")
        
        # Compound tasks section
        compound_tasks = list(methods.get_all_task_names())
        if compound_tasks:
            hddl_parts.append("\n  (:task-definitions")
            for task in sorted(compound_tasks):
                # Get parameters from first method
                methods_for_task = methods.get_methods_for_task(task)
                if methods_for_task:
                    params = self._extract_task_parameters(methods_for_task[0])
                    hddl_parts.append(f"    (:task {task} :parameters ({params}))")
            hddl_parts.append("  )")
        
        # Actions (primitive operators)
        hddl_parts.append("\n  (:actions")
        for op in operators:
            action_hddl = self._operator_to_hddl(op)
            hddl_parts.append(f"    {action_hddl}")
        hddl_parts.append("  )")
        
        # Methods section
        hddl_parts.append("\n  (:methods")
        for task_name in sorted(methods.get_all_task_names()):
            for method in methods.get_methods_for_task(task_name):
                method_hddl = self._method_to_hddl(method)
                hddl_parts.append(f"    {method_hddl}")
        hddl_parts.append("  )")
        
        # Close domain
        hddl_parts.append(")")
        
        hddl_text = "\n".join(hddl_parts)
        
        return HDDLDomain(
            domain_name=domain_name,
            predicates=predicates,
            compound_tasks=compound_tasks,
            primitive_actions=[op.name for op in operators],
            methods=[m.name for m in methods._all_methods.values()],
            hddl_text=hddl_text
        )
    
    def generate_problem(
        self,
        problem_name: str,
        domain_name: str,
        init_state: State,
        goal_tasks: List[Tuple[str, List[str]]],
        objects: Optional[Dict[str, str]] = None
    ) -> HDDLProblem:
        """
        Generate HDDL problem file
        
        Args:
            problem_name: Name of the problem
            domain_name: Name of the domain
            init_state: Initial world state
            goal_tasks: List of (task_name, parameters) tuples
            objects: Optional object declarations {name: type}
        
        Returns:
            HDDLProblem object with complete HDDL text
        """
        hddl_parts = []
        
        # Header
        hddl_parts.append(f"(define (problem {problem_name})")
        hddl_parts.append(f"  (:domain {domain_name})")
        
        # Objects section
        if objects:
            hddl_parts.append("\n  (:objects")
            # Group by type
            objects_by_type: Dict[str, List[str]] = {}
            for obj_name, obj_type in objects.items():
                if obj_type not in objects_by_type:
                    objects_by_type[obj_type] = []
                objects_by_type[obj_type].append(obj_name)
            
            for obj_type, obj_names in sorted(objects_by_type.items()):
                names_str = " ".join(obj_names)
                hddl_parts.append(f"    {names_str} - {obj_type}")
            hddl_parts.append("  )")
        
        # Init state
        hddl_parts.append("\n  (:init")
        for fact in sorted(init_state.facts):
            hddl_parts.append(f"    {fact}")
        hddl_parts.append("  )")
        
        # HTN goal (top-level tasks)
        hddl_parts.append("\n  (:htn")
        hddl_parts.append("    :ordered-tasks (and")
        for i, (task_name, params) in enumerate(goal_tasks):
            task_num = i + 1
            params_str = " ".join(params)
            hddl_parts.append(f"      (task{task_num} ({task_name} {params_str}))")
        hddl_parts.append("    )")
        hddl_parts.append("  )")
        
        # Close problem
        hddl_parts.append(")")
        
        hddl_text = "\n".join(hddl_parts)
        
        return HDDLProblem(
            problem_name=problem_name,
            domain_name=domain_name,
            objects=objects or {},
            init_state=[str(f) for f in init_state.facts],
            goal_tasks=[f"({task} {' '.join(params)})" for task, params in goal_tasks],
            hddl_text=hddl_text
        )
    
    def _method_to_hddl(self, method: Method) -> str:
        """
        Convert Method object to HDDL method declaration
        
        Example output:
        (:method deliver-package
          :parameters (?pkg - package ?dest - location)
          :precondition (and (at ?pkg warehouse))
          :subtasks (and
            (task1 (load-package ?pkg truck1))
            (task2 (drive-truck truck1 warehouse ?dest))
            (task3 (unload-package ?pkg truck1))
          )
          :ordering (and
            (< task1 task2)
            (< task2 task3)
          )
        )
        """
        parts = []
        
        # Method header
        parts.append(f"(:method {method.name}")
        
        # Parameters
        params_str = self._format_parameters(method.parameters)
        parts.append(f"  :parameters ({params_str})")
        
        # Precondition
        if method.preconditions:
            precond_str = self._format_conditions(method.preconditions)
            parts.append(f"  :precondition {precond_str}")
        
        # Subtasks
        parts.append("  :subtasks (and")
        for i, subtask in enumerate(method.subtasks):
            task_num = i + 1
            subtask_str = self._format_subtask(subtask)
            parts.append(f"    (task{task_num} {subtask_str})")
        parts.append("  )")
        
        # Ordering constraints
        if method.ordering:
            parts.append("  :ordering (and")
            for before, after in method.ordering:
                # Convert subtask indices to task identifiers
                before_task = f"task{before + 1}"
                after_task = f"task{after + 1}"
                parts.append(f"    (< {before_task} {after_task})")
            parts.append("  )")
        
        parts.append(")")
        
        return "\n".join(parts)
    
    def _operator_to_hddl(self, operator: Operator) -> str:
        """
        Convert Operator to HDDL action declaration
        
        Example output:
        (:action move
          :parameters (?obj - object ?from ?to - location)
          :precondition (and (at ?obj ?from) (clear ?to))
          :effect (and (at ?obj ?to) (not (at ?obj ?from)))
        )
        """
        parts = []
        
        parts.append(f"(:action {operator.name}")
        
        # Parameters
        params_str = self._format_parameters(operator.parameters)
        parts.append(f"  :parameters ({params_str})")
        
        # Precondition
        if operator.preconditions:
            precond_str = self._format_conditions(operator.preconditions)
            parts.append(f"  :precondition {precond_str}")
        
        # Effects
        if operator.effects:
            effects_str = self._format_effects(operator.effects)
            parts.append(f"  :effect {effects_str}")
        
        parts.append(")")
        
        return "\n".join(parts)
    
    def _format_parameters(self, parameters: Dict[str, str]) -> str:
        """Format parameter list: ?var1 - type1 ?var2 - type2"""
        if not parameters:
            return ""
        
        param_parts = []
        for param_name, param_type in parameters.items():
            if not param_name.startswith("?"):
                param_name = f"?{param_name}"
            param_parts.append(f"{param_name} - {param_type}")
        
        return " ".join(param_parts)
    
    def _format_conditions(self, conditions: List[str]) -> str:
        """Format precondition list: (and (pred1 ?x) (pred2 ?y))"""
        if not conditions:
            return "()"
        
        if len(conditions) == 1:
            return conditions[0]
        
        return "(and " + " ".join(conditions) + ")"
    
    def _format_effects(self, effects: List[str]) -> str:
        """Format effect list with add/delete"""
        if not effects:
            return "()"
        
        if len(effects) == 1:
            return effects[0]
        
        return "(and " + " ".join(effects) + ")"
    
    def _format_subtask(self, subtask: Dict[str, any]) -> str:
        """
        Format subtask for HDDL
        
        Args:
            subtask: Dict with 'name' and 'parameters'
        
        Returns:
            Formatted string: (task-name ?param1 ?param2)
        """
        task_name = subtask.get("name", subtask.get("task_name", "unknown"))
        params = subtask.get("parameters", subtask.get("params", []))
        
        if params:
            params_str = " ".join(str(p) for p in params)
            return f"({task_name} {params_str})"
        else:
            return f"({task_name})"
    
    def _extract_task_parameters(self, method: Method) -> str:
        """Extract task parameters from method"""
        return self._format_parameters(method.parameters)
    
    def _infer_predicates(
        self,
        operators: List[Operator],
        methods: MethodLibrary
    ) -> List[str]:
        """
        Infer predicate declarations from operators and methods
        
        Scans preconditions and effects to find all predicates
        """
        predicates = set()
        
        # Extract from operators
        for op in operators:
            for cond in op.preconditions:
                pred = self._extract_predicate_signature(cond)
                if pred:
                    predicates.add(pred)
            
            for effect in op.effects:
                pred = self._extract_predicate_signature(effect)
                if pred:
                    predicates.add(pred)
        
        # Extract from methods
        for method in methods._all_methods.values():
            for cond in method.preconditions:
                pred = self._extract_predicate_signature(cond)
                if pred:
                    predicates.add(pred)
        
        return sorted(list(predicates))
    
    def _extract_predicate_signature(self, condition: str) -> Optional[str]:
        """
        Extract predicate signature from condition
        
        Example: (at ?x ?y) → (at ?x ?y)
                 (not (clear ?z)) → (clear ?z)
        """
        condition = condition.strip()
        
        # Remove outer 'not' if present
        if condition.startswith("(not "):
            condition = condition[5:-1].strip()
        
        # Remove outer 'and' if present
        if condition.startswith("(and "):
            # For compound conditions, extract first predicate
            # This is simplified - ideally parse all
            condition = condition[5:].strip()
            if condition.startswith("("):
                end = condition.find(")")
                if end != -1:
                    condition = condition[:end+1]
        
        # Extract predicate name and parameters
        if condition.startswith("(") and condition.endswith(")"):
            parts = condition[1:-1].split()
            if parts:
                pred_name = parts[0]
                # Create generic signature
                param_count = len(parts) - 1
                params = " ".join([f"?x{i}" for i in range(param_count)])
                return f"({pred_name} {params})".strip()
        
        return None
    
    def save_domain(self, domain: HDDLDomain, output_path: str) -> None:
        """Save HDDL domain to file"""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w') as f:
            f.write(domain.hddl_text)
        
        logger.info(f"Saved HDDL domain to {output_path}")
    
    def save_problem(self, problem: HDDLProblem, output_path: str) -> None:
        """Save HDDL problem to file"""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w') as f:
            f.write(problem.hddl_text)
        
        logger.info(f"Saved HDDL problem to {output_path}")
    
    def validate_syntax(self, hddl_text: str) -> Tuple[bool, List[str]]:
        """
        Basic HDDL syntax validation
        
        Returns:
            (is_valid, error_messages)
        """
        errors = []
        
        # Check balanced parentheses
        paren_count = 0
        for char in hddl_text:
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
            
            if paren_count < 0:
                errors.append("Unbalanced parentheses: ')' before '('")
                break
        
        if paren_count != 0:
            errors.append(f"Unbalanced parentheses: {paren_count} unclosed '('")
        
        # Check required sections
        required_sections = [':predicates', ':task-definitions', ':methods']
        for section in required_sections:
            if section not in hddl_text:
                errors.append(f"Missing required section: {section}")
        
        # Check for common syntax errors
        if '(define' not in hddl_text:
            errors.append("Missing '(define' declaration")
        
        if ':domain' not in hddl_text and ':problem' not in hddl_text:
            errors.append("Not a valid domain or problem file")
        
        is_valid = len(errors) == 0
        return is_valid, errors
