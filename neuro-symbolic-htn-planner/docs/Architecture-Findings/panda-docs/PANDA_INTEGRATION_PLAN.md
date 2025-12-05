# PANDA Framework Integration Plan
**Date**: January 2025  
**Target**: Integrate PANDA HTN planner with multi-agent LLM system  
**Timeline**: 2-3 weeks implementation  

---

## Executive Summary

**Decision**: Use PANDA HTN framework as symbolic planning core, enhanced by multi-agent LLM system for method generation, heuristic guidance, and precondition inference.

**Integration Strategy**: PANDA provides true HTN decomposition (task stack, method library, recursive seek-plans). Multi-agent system wraps PANDA to add:
1. **LLM-Generated Methods**: DecompositionAgent creates HDDL methods from natural language
2. **Heuristic Guidance**: Custom heuristics using LLM state evaluation
3. **Execution & Verification**: ExecutionAgent and VerificationAgent handle plan execution

**Key Advantage**: Avoids 3-4 weeks building SHOP2 from scratch. PANDA is production-ready, supports HDDL standard, provides plan verification.

---

## PANDA Architecture Overview

### Component Pipeline

```
┌──────────────────────────────────────────────────────────────────┐
│                       PANDA WORKFLOW                              │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  domain.hddl + problem.hddl                                       │
│         │                                                         │
│         ▼                                                         │
│  [pandaPIparser]  ──► domain-problem.parsed (internal HTN)       │
│         │                                                         │
│         ▼                                                         │
│  [pandaPIgrounder] ──► domain-problem.sas (grounded SAS+)        │
│         │                                                         │
│         ▼                                                         │
│  [pandaPIengine]   ──► plan.solution (action sequence)           │
│         │                                                         │
│         ▼                                                         │
│  [pandaPIparser --convert] ──► plan.hddl (HDDL-compliant)        │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

### Key Components

1. **pandaPIparser**: 
   - Input: HDDL domain + problem files
   - Output: Internal HTN format (`.parsed` file)
   - Capabilities: HDDL→SHOP2, HDDL→HPDL, plan verification
   - Build: C++17, flex 2.6+, bison 3.5+

2. **pandaPIgrounder**:
   - Input: `.parsed` file from parser
   - Output: Grounded SAS+ file (`.sas`)
   - Purpose: Converts lifted planning problem to ground representation
   - Format: SAS+ with state variables, actions, methods

3. **pandaPIengine**:
   - Input: `.sas` file from grounder
   - Output: Plan solution (action sequence)
   - Algorithm: Greedy best-first search with RC-FF heuristic
   - Capabilities: Visited lists, optional ILP/SAT/BDD backends

4. **Plan Converter**:
   - Input: Raw plan + original domain/problem
   - Output: HDDL-compliant plan with hierarchical structure
   - Usage: `pandaPIparser domain.hddl problem.hddl --panda-converter plan.solution`

### File Formats

#### HDDL Input (Domain)
```lisp
(define (domain logistics)
  (:requirements :typing :hierarchy)
  (:types truck package location)
  
  (:predicates 
    (at-truck ?t - truck ?l - location)
    (at-package ?p - package ?l - location)
    (in-truck ?p - package ?t - truck))
  
  (:task deliver-package :parameters (?p - package ?dest - location))
  
  (:method transport-by-truck
    :parameters (?p - package ?t - truck ?from ?to - location)
    :task (deliver-package ?p ?to)
    :precondition (and (at-truck ?t ?from) (at-package ?p ?from))
    :subtasks (and
      (task1 (load ?p ?t ?from))
      (task2 (drive ?t ?from ?to))
      (task3 (unload ?p ?t ?to))))
  
  (:action load
    :parameters (?p - package ?t - truck ?l - location)
    :precondition (and (at-truck ?t ?l) (at-package ?p ?l))
    :effect (and (in-truck ?p ?t) (not (at-package ?p ?l)))))
)
```

#### SAS+ Intermediate (Grounder Output)
```
# Grounded SAS+ format
begin_logic
  <constants>
  <sorts>
  <predicates>
  <functions>
end_logic

begin_tasks
  <primitive_tasks>
  <abstract_tasks>
end_tasks

begin_methods
  <method_id> <abstract_task_id> <method_name>
  <variables>
  <preconditions>
  <subtasks>
  <ordering_constraints>
end_methods

begin_initial
  <initial_state_facts>
end_initial

begin_goal
  <goal_specification>
end_goal
```

#### Plan Output
```
root
-> deliver-package(package1, cityB)
   -> transport-by-truck(package1, truck1, cityA, cityB)
      -> load(package1, truck1, cityA)
      -> drive(truck1, cityA, cityB)
      -> unload(package1, truck1, cityB)
```

---

## Integration Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│               NEURO-SYMBOLIC HTN PLANNING SYSTEM                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  User Task (Natural Language)                                    │
│       │                                                          │
│       ▼                                                          │
│  ┌──────────────────────────────────────────┐                   │
│  │     DecompositionAgent (LLM)             │                   │
│  │  - Generate HDDL methods from NL         │                   │
│  │  - Create domain file dynamically        │                   │
│  │  - Validate method preconditions         │                   │
│  └──────────────────────────────────────────┘                   │
│       │                                                          │
│       │ (domain.hddl, problem.hddl)                             │
│       ▼                                                          │
│  ┌──────────────────────────────────────────┐                   │
│  │     PANDA Planner (Subprocess)           │                   │
│  │  - Run parser → grounder → engine        │                   │
│  │  - Use RC-FF heuristic                   │                   │
│  │  - Return hierarchical plan              │                   │
│  └──────────────────────────────────────────┘                   │
│       │                                                          │
│       │ (plan.solution)                                         │
│       ▼                                                          │
│  ┌──────────────────────────────────────────┐                   │
│  │     PlanParserAgent                      │                   │
│  │  - Parse PANDA output format             │                   │
│  │  - Extract action sequence               │                   │
│  │  - Build execution graph                 │                   │
│  └──────────────────────────────────────────┘                   │
│       │                                                          │
│       │ (ExecutionPlan object)                                  │
│       ▼                                                          │
│  ┌──────────────────────────────────────────┐                   │
│  │     ExecutionAgent                       │                   │
│  │  - Execute primitive actions             │                   │
│  │  - Update state after each action        │                   │
│  │  - Handle execution failures             │                   │
│  └──────────────────────────────────────────┘                   │
│       │                                                          │
│       ▼                                                          │
│  ┌──────────────────────────────────────────┐                   │
│  │     VerificationAgent                    │                   │
│  │  - Verify goal achievement               │                   │
│  │  - Check state consistency               │                   │
│  │  - Trigger replanning if needed          │                   │
│  └──────────────────────────────────────────┘                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

#### 1. DecompositionAgent (Enhanced)
**Current State**: Generates flat task lists via LLM  
**New Role**: HDDL domain/method generator

**Responsibilities**:
- Convert user's natural language task to HDDL problem specification
- Generate domain methods using LLM (or retrieve from library)
- Create HDDL files (domain.hddl, problem.hddl)
- Validate generated HDDL syntax

**Implementation**:
```python
class DecompositionAgent:
    def __init__(self, panda_wrapper: PANDAWrapper):
        self.panda = panda_wrapper
        self.domain_generator = HDDLDomainGenerator()
        self.method_library = MethodLibrary()
    
    async def process(self, task: Task) -> HDDLProblem:
        # 1. Check if domain exists for this task type
        domain = self.method_library.get_domain(task.domain_name)
        
        if not domain:
            # 2. Generate domain using LLM
            domain = await self._generate_domain_with_llm(task)
            self.method_library.store_domain(domain)
        
        # 3. Generate problem specification
        problem = await self._generate_problem(task, domain)
        
        # 4. Write HDDL files
        domain_file = self.domain_generator.write_hddl(domain)
        problem_file = self.domain_generator.write_problem(problem)
        
        return HDDLProblem(domain_file, problem_file)
    
    async def _generate_domain_with_llm(self, task: Task) -> Domain:
        prompt = f"""
        Generate an HDDL domain for the following task:
        {task.description}
        
        Include:
        1. Types and predicates
        2. Abstract tasks (compound tasks)
        3. Methods for decomposing abstract tasks
        4. Primitive actions with preconditions and effects
        
        Follow HDDL syntax strictly.
        """
        
        hddl_text = await self.llm_client.generate(prompt)
        return self.domain_generator.parse_llm_output(hddl_text)
```

#### 2. PANDA Wrapper (New Component)
**Purpose**: Python interface to PANDA C++ binaries

**Implementation**:
```python
import subprocess
import os
from pathlib import Path
from typing import Tuple, Optional

class PANDAWrapper:
    """Wrapper for PANDA HTN planner binaries"""
    
    def __init__(self, panda_root: str, timeout: int = 120):
        self.panda_root = Path(panda_root)
        self.parser_bin = self.panda_root / "pandaPIparser"
        self.grounder_bin = self.panda_root / "pandaPIgrounder"
        self.engine_bin = self.panda_root / "pandaPIengine"
        self.timeout = timeout
        
        self._validate_binaries()
    
    def _validate_binaries(self):
        """Ensure PANDA binaries exist and are executable"""
        for binary in [self.parser_bin, self.grounder_bin, self.engine_bin]:
            if not binary.exists():
                raise FileNotFoundError(f"PANDA binary not found: {binary}")
            if not os.access(binary, os.X_OK):
                raise PermissionError(f"PANDA binary not executable: {binary}")
    
    def plan(self, domain_file: str, problem_file: str, 
             work_dir: str = "/tmp/panda") -> Tuple[bool, Optional[str], str]:
        """
        Run PANDA planner pipeline: parse → ground → plan
        
        Returns:
            (success, plan_file_path, log_output)
        """
        work_path = Path(work_dir)
        work_path.mkdir(parents=True, exist_ok=True)
        
        unique_id = f"{Path(domain_file).stem}-{Path(problem_file).stem}"
        parsed_file = work_path / f"{unique_id}.parsed"
        sas_file = work_path / f"{unique_id}.sas"
        plan_file = work_path / f"{unique_id}.solution"
        
        logs = []
        
        try:
            # Step 1: Parse
            logs.append("=== PARSING ===")
            result = subprocess.run(
                [str(self.parser_bin), domain_file, problem_file, str(parsed_file)],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            logs.append(result.stdout)
            if result.returncode != 0:
                logs.append(f"Parser error: {result.stderr}")
                return False, None, "\n".join(logs)
            
            # Step 2: Ground
            logs.append("=== GROUNDING ===")
            result = subprocess.run(
                [str(self.grounder_bin), str(parsed_file), str(sas_file)],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            logs.append(result.stdout)
            if result.returncode != 0:
                logs.append(f"Grounder error: {result.stderr}")
                return False, None, "\n".join(logs)
            
            # Step 3: Plan
            logs.append("=== PLANNING ===")
            result = subprocess.run(
                [str(self.engine_bin), str(sas_file), "-H", "rc2(h=add)", "-g", "none"],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            # Write output to plan file
            with open(plan_file, 'w') as f:
                f.write(result.stdout)
            
            logs.append(result.stdout)
            
            # Check for solution
            if "No solution found" in result.stdout or result.returncode != 0:
                logs.append("No solution found")
                return False, None, "\n".join(logs)
            
            return True, str(plan_file), "\n".join(logs)
            
        except subprocess.TimeoutExpired:
            logs.append(f"Timeout after {self.timeout} seconds")
            return False, None, "\n".join(logs)
        except Exception as e:
            logs.append(f"Unexpected error: {str(e)}")
            return False, None, "\n".join(logs)
    
    def verify_plan(self, domain_file: str, problem_file: str, 
                    plan_file: str) -> Tuple[bool, str]:
        """Verify plan correctness using PANDA parser"""
        try:
            result = subprocess.run(
                [str(self.parser_bin), domain_file, problem_file, 
                 "--verify", plan_file],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            valid = "Plan is valid" in result.stdout
            return valid, result.stdout
            
        except Exception as e:
            return False, f"Verification error: {str(e)}"
```

#### 3. Plan Parser (New Component)
**Purpose**: Convert PANDA's plan output to executable format

**Implementation**:
```python
from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class PlanStep:
    """Single action in plan"""
    action_name: str
    parameters: List[str]
    depth: int  # Hierarchical depth (0 = root task)
    parent_task: Optional[str]

@dataclass
class ExecutionPlan:
    """Parsed plan ready for execution"""
    steps: List[PlanStep]
    hierarchy: Dict[str, List[str]]  # task -> subtasks mapping

class PANDAPlanParser:
    """Parse PANDA's hierarchical plan output"""
    
    def parse(self, plan_file: str) -> ExecutionPlan:
        """
        Parse PANDA plan format:
        
        root
        -> deliver-package(package1, cityB)
           -> transport-by-truck(package1, truck1, cityA, cityB)
              -> load(package1, truck1, cityA)
              -> drive(truck1, cityA, cityB)
              -> unload(package1, truck1, cityB)
        """
        with open(plan_file, 'r') as f:
            lines = f.readlines()
        
        steps = []
        hierarchy = {}
        parent_stack = []
        
        for line in lines:
            if not line.strip() or line.startswith("=="):
                continue
            
            # Calculate depth from indentation
            depth = (len(line) - len(line.lstrip())) // 3
            
            # Extract task/action
            task_str = line.strip().lstrip("-> ")
            
            # Parse task name and parameters
            if "(" in task_str:
                name = task_str[:task_str.index("(")]
                params_str = task_str[task_str.index("(")+1:task_str.rindex(")")]
                params = [p.strip() for p in params_str.split(",")]
            else:
                name = task_str
                params = []
            
            # Determine parent task
            while len(parent_stack) > depth:
                parent_stack.pop()
            
            parent = parent_stack[-1] if parent_stack else None
            
            # Create step
            step = PlanStep(
                action_name=name,
                parameters=params,
                depth=depth,
                parent_task=parent
            )
            steps.append(step)
            
            # Update hierarchy
            if parent:
                if parent not in hierarchy:
                    hierarchy[parent] = []
                hierarchy[parent].append(name)
            
            # Update parent stack
            if len(parent_stack) == depth:
                parent_stack.append(name)
            else:
                parent_stack[depth] = name
        
        return ExecutionPlan(steps=steps, hierarchy=hierarchy)
    
    def extract_primitive_actions(self, plan: ExecutionPlan) -> List[PlanStep]:
        """Extract only primitive actions (leaves in hierarchy)"""
        primitives = []
        all_parents = set(plan.hierarchy.keys())
        
        for step in plan.steps:
            if step.action_name not in all_parents:
                primitives.append(step)
        
        return primitives
```

#### 4. HDDL Domain Generator (New Component)
**Purpose**: Convert LLM output or YAML to HDDL format

**Implementation**:
```python
class HDDLDomainGenerator:
    """Generate HDDL domain files from various sources"""
    
    def from_yaml(self, yaml_file: str) -> str:
        """
        Convert existing YAML domain to HDDL
        
        YAML Format:
        domain:
          name: logistics
          types:
            - truck
            - package
          predicates:
            - at-truck: [truck, location]
          tasks:
            - deliver-package: [package, location]
          methods:
            - name: transport-by-truck
              task: deliver-package
              parameters: [package, truck, location, location]
              precondition: ...
              subtasks: ...
        """
        import yaml
        
        with open(yaml_file, 'r') as f:
            data = yaml.safe_load(f)
        
        domain = data['domain']
        
        hddl = f"(define (domain {domain['name']})\n"
        hddl += "  (:requirements :typing :hierarchy)\n\n"
        
        # Types
        if 'types' in domain:
            hddl += "  (:types\n"
            for t in domain['types']:
                hddl += f"    {t}\n"
            hddl += "  )\n\n"
        
        # Predicates
        if 'predicates' in domain:
            hddl += "  (:predicates\n"
            for pred in domain['predicates']:
                if isinstance(pred, dict):
                    name = list(pred.keys())[0]
                    params = pred[name]
                    param_str = " ".join([f"?{p}" for p in params])
                    hddl += f"    ({name} {param_str})\n"
            hddl += "  )\n\n"
        
        # Tasks
        if 'tasks' in domain:
            for task in domain['tasks']:
                if isinstance(task, dict):
                    name = list(task.keys())[0]
                    params = task[name]
                    param_str = " ".join([f"?{p}" for p in params])
                    hddl += f"  (:task {name} :parameters ({param_str}))\n\n"
        
        # Methods
        if 'methods' in domain:
            for method in domain['methods']:
                hddl += self._write_method(method)
        
        # Actions
        if 'actions' in domain:
            for action in domain['actions']:
                hddl += self._write_action(action)
        
        hddl += ")\n"
        return hddl
    
    def _write_method(self, method: dict) -> str:
        """Generate HDDL method definition"""
        m = f"  (:method {method['name']}\n"
        m += f"    :parameters ({' '.join(method['parameters'])})\n"
        m += f"    :task ({method['task']} {' '.join(method.get('task_params', []))})\n"
        
        if 'precondition' in method:
            m += f"    :precondition {method['precondition']}\n"
        
        if 'subtasks' in method:
            m += f"    :subtasks (and\n"
            for i, subtask in enumerate(method['subtasks']):
                m += f"      (task{i} {subtask})\n"
            m += "    )\n"
        
        if 'ordering' in method:
            m += f"    :ordering (and\n"
            for constraint in method['ordering']:
                m += f"      {constraint}\n"
            m += "    )\n"
        
        m += "  )\n\n"
        return m
    
    def _write_action(self, action: dict) -> str:
        """Generate HDDL action (primitive task)"""
        a = f"  (:action {action['name']}\n"
        a += f"    :parameters ({' '.join(action['parameters'])})\n"
        
        if 'precondition' in action:
            a += f"    :precondition {action['precondition']}\n"
        
        if 'effect' in action:
            a += f"    :effect {action['effect']}\n"
        
        a += "  )\n\n"
        return a
    
    def write_hddl(self, domain_text: str, output_file: str):
        """Write HDDL text to file"""
        with open(output_file, 'w') as f:
            f.write(domain_text)
        return output_file
```

#### 5. Enhanced Core Workflow
**Purpose**: Orchestrate neuro-symbolic planning pipeline

**Implementation**:
```python
class NeurosymbolicWorkflow:
    """
    Enhanced workflow using PANDA + LLM agents
    """
    
    def __init__(self):
        self.panda = PANDAWrapper(panda_root="/path/to/PANDA-HTN")
        self.decomposition_agent = DecompositionAgent(self.panda)
        self.plan_parser = PANDAPlanParser()
        self.execution_agent = ExecutionAgent()
        self.verification_agent = VerificationAgent()
    
    async def process_task(self, task: Task) -> ExecutionResult:
        """
        Complete neuro-symbolic HTN planning workflow
        
        1. LLM generates HDDL domain/problem
        2. PANDA plans hierarchically
        3. Parse plan to execution format
        4. Execute primitive actions
        5. Verify goal achievement
        """
        
        # Phase 1: Domain Generation (Neuro)
        logger.info("Generating HDDL domain with LLM...")
        hddl_problem = await self.decomposition_agent.process(task)
        
        # Phase 2: HTN Planning (Symbolic)
        logger.info("Running PANDA HTN planner...")
        success, plan_file, logs = self.panda.plan(
            domain_file=hddl_problem.domain_file,
            problem_file=hddl_problem.problem_file
        )
        
        if not success:
            logger.error(f"Planning failed: {logs}")
            return ExecutionResult(success=False, error="Planning failed")
        
        # Phase 3: Plan Parsing
        logger.info("Parsing hierarchical plan...")
        execution_plan = self.plan_parser.parse(plan_file)
        primitive_actions = self.plan_parser.extract_primitive_actions(execution_plan)
        
        # Phase 4: Execution
        logger.info(f"Executing {len(primitive_actions)} primitive actions...")
        exec_result = await self.execution_agent.execute_plan(primitive_actions)
        
        # Phase 5: Verification
        logger.info("Verifying goal achievement...")
        verification = await self.verification_agent.verify(
            task.goal,
            exec_result.final_state
        )
        
        return ExecutionResult(
            success=verification.passed,
            plan=execution_plan,
            execution_trace=exec_result.trace,
            final_state=exec_result.final_state
        )
```

---

## LLM Enhancement Strategy

### Where LLMs Add Value

PANDA provides **symbolic HTN planning**. LLMs enhance it in 3 key areas:

#### 1. Method Generation (Primary Contribution)
**Problem**: Hand-coding HDDL methods is time-consuming  
**Solution**: LLM generates methods from natural language task descriptions

**Example**:
```
User: "Book a flight from NYC to Paris"

LLM generates HDDL method:
(:method book-international-flight
  :parameters (?from - city ?to - city)
  :task (book-flight ?from ?to)
  :precondition (and
    (international ?from ?to)
    (has-passport))
  :subtasks (and
    (task1 (search-flights ?from ?to))
    (task2 (select-cheapest-flight))
    (task3 (enter-payment-info))
    (task4 (confirm-booking))))
```

#### 2. Precondition Inference
**Problem**: Users don't specify all preconditions explicitly  
**Solution**: LLM infers missing preconditions from world knowledge

**Example**:
```
Task: "Microwave leftovers"

LLM infers preconditions:
- (food-in-container)
- (container-is-microwave-safe)  <- NOT specified by user
- (microwave-available)
- (electricity-on)               <- Common sense
```

#### 3. Heuristic Guidance
**Problem**: PANDA uses domain-independent heuristic (RC-FF)  
**Solution**: LLM evaluates states for task-specific heuristic

**Example**:
```python
class LLMHeuristic:
    async def evaluate_state(self, state: State, goal: Goal) -> float:
        """
        Use LLM to estimate distance to goal
        """
        prompt = f"""
        Current state: {state}
        Goal: {goal}
        
        Rate how close we are to the goal (0.0 = very far, 1.0 = achieved).
        Consider:
        - Which preconditions are satisfied
        - Which actions still need to be performed
        - Complexity of remaining tasks
        
        Return only a number between 0.0 and 1.0.
        """
        
        score = await self.llm_client.generate(prompt)
        return float(score.strip())
```

### What PANDA Provides (Don't Rebuild)

✅ **Recursive Decomposition**: Task stack, seek-plans algorithm  
✅ **Method Selection**: Unification, precondition checking  
✅ **State Progression**: Forward-chaining state updates  
✅ **Plan Verification**: Correctness checking  
✅ **Grounding**: Lifted → ground translation  
✅ **Search Algorithm**: Greedy best-first with RC-FF heuristic  

**Don't waste time reimplementing these**. Focus LLM effort on areas where symbolic planning is weak: natural language understanding, world knowledge, and method generation.

---

## Implementation Phases

### Phase 1: PANDA Integration (Week 1)
**Goal**: Get PANDA running end-to-end with simple hand-coded domains

**Tasks**:
1. Build PANDA binaries (parser, grounder, engine)
   - Install dependencies: g++, cmake, flex, bison, gengetopt
   - Compile all three components
   - Test with existing PANDA examples

2. Implement `PANDAWrapper` class
   - Subprocess execution for each component
   - Error handling and logging
   - Timeout management

3. Implement `PANDAPlanParser` class
   - Parse hierarchical plan output
   - Extract primitive actions
   - Build execution graph

4. Create simple HDDL domain manually
   - Test with logistics or blocksworld
   - Verify PANDA finds correct plan
   - Confirm plan executes successfully

**Deliverable**: Python script that calls PANDA and executes resulting plan

**Validation**:
```bash
python test_panda_integration.py \
  --domain examples/logistics.hddl \
  --problem examples/logistics-p01.hddl
```
Expected output: Successful plan found and executed

---

### Phase 2: Domain Generation (Week 2)
**Goal**: LLM generates HDDL domains from natural language

**Tasks**:
1. Implement `HDDLDomainGenerator` class
   - YAML → HDDL converter
   - LLM output → HDDL parser
   - Syntax validation

2. Create domain generation prompts
   - Template for types/predicates
   - Template for methods
   - Template for actions
   - Few-shot examples

3. Implement `MethodLibrary` class
   - Store generated domains
   - Retrieve by domain name
   - Version control for domains

4. Enhance `DecompositionAgent`
   - Call LLM for domain generation
   - Parse LLM output to HDDL
   - Validate syntax before passing to PANDA

**Deliverable**: Natural language → HDDL → plan pipeline

**Validation**:
```python
task = Task(
    description="Deliver package from warehouse to customer",
    domain_name="logistics"
)

result = await workflow.process_task(task)
assert result.success
```

---

### Phase 3: Execution & Verification (Week 3)
**Goal**: Complete end-to-end neuro-symbolic workflow

**Tasks**:
1. Integrate with existing `ExecutionAgent`
   - Convert PANDA actions to executable format
   - Handle state updates
   - Error recovery

2. Integrate with existing `VerificationAgent`
   - Check goal achievement
   - Validate state consistency
   - Trigger replanning if needed

3. Implement LLM heuristic (optional enhancement)
   - State evaluation prompts
   - Integration with PANDA search
   - Performance comparison vs. RC-FF

4. Add memory system integration
   - Store successful plans
   - Retrieve similar past plans
   - Learn from failures

**Deliverable**: Full neuro-symbolic HTN planning system

**Validation**:
- Run on 10 different task types
- Measure success rate (>80% target)
- Compare with baseline (flat LLM planning)
- Verify plans are hierarchically structured

---

## Timeline & Milestones

| Week | Phase | Key Deliverable | Success Criteria |
|------|-------|----------------|------------------|
| 1 | PANDA Integration | `PANDAWrapper` + `PANDAPlanParser` | Hand-coded HDDL → plan → execution works |
| 2 | Domain Generation | `HDDLDomainGenerator` + enhanced `DecompositionAgent` | NL task → HDDL → plan works |
| 3 | Full Integration | `NeurosymbolicWorkflow` with E&V agents | End-to-end system passes validation suite |

**Total Time**: 3 weeks  
**Risk Buffer**: 1 week for debugging and edge cases  
**Thesis Writing**: Concurrent with Phase 3

---

## Academic Contribution

### What Makes This Defensible?

**Not just using PANDA** - that's tool usage, not research contribution.

**Your contributions**:

1. **Neuro-Symbolic Integration Architecture**
   - Novel combination of LLM-based method generation with symbolic HTN planning
   - Design pattern for when to use neural vs. symbolic components
   - Performance comparison of hybrid approach vs. pure symbolic/neural

2. **Natural Language to HDDL Translation**
   - LLM prompt engineering for HDDL generation
   - Validation techniques for generated domains
   - Error recovery strategies when LLM produces invalid syntax

3. **Multi-Agent Enhancement Layer**
   - Execution agent for grounding PANDA plans
   - Verification agent for replanning triggers
   - Memory system for plan reuse and learning

4. **Empirical Evaluation**
   - Benchmark comparison: PANDA alone vs. PANDA+LLM
   - Ablation study: which LLM enhancements provide most value
   - Failure analysis: when does neuro-symbolic approach fail

### Thesis Structure

**Title**: *Neuro-Symbolic Hierarchical Task Network Planning: Integrating Large Language Models with Classical HTN Planners*

**Chapters**:
1. Introduction
   - Motivation: Gap between natural language tasks and formal planning
   - Research question: Can LLMs enhance HTN planning?

2. Background
   - HTN Planning (SHOP2, PANDA)
   - Large Language Models (prompting, limitations)
   - Neuro-symbolic AI

3. Related Work
   - LLM-based planning (limitations: no backtracking, hallucination)
   - Classical HTN planners (limitations: manual domain engineering)
   - Hybrid approaches

4. **System Architecture** (Your contribution)
   - PANDA integration
   - LLM enhancement points
   - Multi-agent coordination

5. **Implementation** (Your contribution)
   - Domain generation algorithm
   - Plan parsing and execution
   - Error handling and recovery

6. **Evaluation** (Your contribution)
   - Experimental setup
   - Benchmark results
   - Ablation studies
   - Failure analysis

7. Conclusion & Future Work

**Key Defense Points**:
- "PANDA provides symbolic planning core"
- "Our contribution is neuro-symbolic **integration**"
- "We show when LLMs add value vs. when classical planning is better"
- "System is more than sum of parts"

---

## Risk Mitigation

### Potential Issues & Solutions

#### 1. LLM generates invalid HDDL
**Risk**: Syntax errors, impossible preconditions, circular methods  
**Mitigation**:
- HDDL syntax validator before passing to PANDA
- Few-shot prompting with correct examples
- Iterative refinement: if PANDA parser fails, send error back to LLM
- Fallback to hand-coded domain library

**Implementation**:
```python
async def generate_domain_with_validation(self, task: Task, max_attempts: int = 3):
    for attempt in range(max_attempts):
        hddl = await self.llm_client.generate_domain(task)
        
        # Validate syntax
        valid, errors = self.hddl_validator.check(hddl)
        if valid:
            return hddl
        
        # Refine with error feedback
        task.context += f"\nPrevious attempt had errors: {errors}"
    
    # Fallback to library
    return self.method_library.get_default_domain(task.domain_name)
```

#### 2. PANDA planning timeout
**Risk**: Complex problems take too long (>2 minutes default)  
**Mitigation**:
- Increase timeout for complex tasks
- Decompose large tasks into smaller subproblems
- Use LLM to simplify problem before passing to PANDA
- Progressive planning: solve incrementally

#### 3. Execution failures
**Risk**: Plan is valid but action execution fails  
**Mitigation**:
- Execution monitoring with state checks
- Replanning on failure
- Partial plan execution with verification
- Fallback to LLM-based repair

#### 4. No contribution claim
**Risk**: Professor says "you just used PANDA"  
**Mitigation**:
- Emphasize neuro-symbolic **integration** as contribution
- Show empirical results: PANDA+LLM > PANDA alone
- Document design decisions and architecture
- Highlight method generation as novel component

---

## Evaluation Plan

### Experiments

#### Experiment 1: Method Generation Quality
**Question**: Can LLM generate valid HDDL methods?

**Setup**:
- 20 different task types (logistics, cooking, travel planning, etc.)
- LLM generates domain for each
- Measure: syntax validity, semantic correctness, PANDA acceptance rate

**Metrics**:
- Syntax validity: % of generated HDDL that parses correctly
- Semantic correctness: % of methods that produce valid plans
- Human evaluation: expert rating of method quality (1-5 scale)

**Target**: >80% syntax valid, >70% semantically correct

---

#### Experiment 2: Planning Performance
**Question**: Does LLM enhancement improve planning quality?

**Setup**:
- Benchmark suite: 50 planning problems
- Compare 3 conditions:
  1. PANDA with hand-coded domains
  2. PANDA with LLM-generated domains
  3. Pure LLM planning (baseline)

**Metrics**:
- Success rate: % of problems solved
- Plan quality: number of actions, optimality
- Planning time: seconds to solution
- Human preference: which plans are more natural

**Hypothesis**: PANDA+LLM achieves high success rate (like PANDA) with natural language input (like LLM)

---

#### Experiment 3: Ablation Study
**Question**: Which LLM enhancements provide most value?

**Setup**:
- Test 4 configurations:
  1. PANDA only (hand-coded domains)
  2. PANDA + LLM method generation
  3. PANDA + LLM method generation + precondition inference
  4. PANDA + LLM method generation + precondition inference + heuristic

**Metrics**:
- Success rate for each configuration
- Planning time for each configuration
- User satisfaction (for natural language input)

**Goal**: Identify which components are essential vs. optional

---

#### Experiment 4: Failure Analysis
**Question**: When does the system fail and why?

**Setup**:
- Collect all failures from Experiments 1-3
- Categorize failure modes:
  - LLM syntax errors
  - Invalid method semantics
  - PANDA timeout
  - Execution failures
  - Goal not achievable

**Metrics**:
- Failure mode distribution
- Root cause analysis
- Potential fixes for each category

**Goal**: Identify limitations and future work

---

## Next Steps (Immediate Actions)

### This Week
1. **Build PANDA binaries**
   ```bash
   cd PANDA-HTN/pandaPIparser
   make
   
   cd ../pandaPIgrounder
   cmake . && make
   
   cd ../pandaPIengine
   cmake . && make
   ```

2. **Test PANDA with example**
   ```bash
   cd PANDA-HTN
   ./problemSolver.sh pandaPIparser/tests/empty-d.hddl pandaPIparser/tests/empty-p.hddl
   ```

3. **Implement `PANDAWrapper` class**
   - Create `src/integrations/panda_wrapper.py`
   - Implement `plan()`, `verify_plan()` methods
   - Test with simple logistics domain

4. **Implement `PANDAPlanParser` class**
   - Create `src/integrations/panda_plan_parser.py`
   - Parse hierarchical plan format
   - Extract primitive actions

### Next Week
5. **Create `HDDLDomainGenerator`**
   - YAML → HDDL converter
   - Manual domain for testing

6. **Enhance `DecompositionAgent`**
   - Integrate domain generator
   - Create LLM prompts for HDDL generation

7. **End-to-end test**
   - Natural language task → HDDL → PANDA plan → execution
   - Validate complete pipeline

### Week 3
8. **Integrate with existing agents**
   - ExecutionAgent: handle PANDA actions
   - VerificationAgent: check goal achievement

9. **Run evaluation experiments**
   - Collect benchmark tasks
   - Measure success rate
   - Compare baselines

10. **Write methodology section**
    - Document architecture
    - Explain design decisions
    - Present preliminary results

---

## Conclusion

**Summary**: This integration plan provides a clear path to combining PANDA's symbolic HTN planning with LLM-based natural language understanding and method generation.

**Key Advantages**:
- ✅ **Time-efficient**: Reuses PANDA instead of 3-4 weeks building SHOP2
- ✅ **Academically defensible**: Clear contribution (neuro-symbolic integration)
- ✅ **Technically sound**: Leverages strengths of both symbolic and neural approaches
- ✅ **Thesis-ready**: Well-defined experiments and evaluation plan

**Timeline**: 3 weeks implementation + 1 week buffer = **4 weeks total**

**Next Action**: Build PANDA binaries and implement `PANDAWrapper` class (Week 1, Day 1)

---

**Questions for User**:
1. Do you have PANDA binaries already compiled, or need to build from source?
2. What benchmark domains do you want to test first (logistics, blocksworld, cooking)?
3. Should we prioritize method generation quality or full integration first?
4. Any specific thesis deadline we need to target?
