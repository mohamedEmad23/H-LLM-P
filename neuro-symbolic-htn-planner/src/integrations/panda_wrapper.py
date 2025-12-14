"""
PANDA HTN Planner Integration
Python wrapper for PANDA binaries (parser, grounder, engine)
"""

import subprocess
import os
from pathlib import Path
from typing import Tuple, Optional, List
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class PlannerResult:
    """Result of PANDA planning operation"""
    success: bool
    plan_file: Optional[str]
    logs: str
    error: Optional[str] = None
    
    @property
    def actions(self) -> List[dict]:
        """Parse actions from plan file (filtering out PANDA internal operators)"""
        if not self.success or not self.plan_file:
            return []
        
        try:
            with open(self.plan_file, 'r') as f:
                lines = f.readlines()
            
            actions = []
            in_plan = False
            for line in lines:
                line = line.strip()
                if line == "==>":
                    in_plan = True
                    continue
                elif line == "<==":
                    break
                elif in_plan and line and not line.startswith("root"):
                    # Parse action lines like "1 traverse[A,C]"
                    parts = line.split(maxsplit=1)
                    if len(parts) == 2:
                        action_str = parts[1]
                        
                        # FILTER OUT PANDA INTERNAL OPERATORS
                        # Skip: __top, __noop, and decomposition lines (contain "->")
                        if action_str.startswith("__") or "->" in action_str:
                            continue
                        
                        # Extract name and parameters
                        if '[' in action_str:
                            name = action_str.split('[')[0]
                            params_str = action_str.split('[')[1].rstrip(']')
                            params = [p.strip() for p in params_str.split(',')]
                        else:
                            name = action_str
                            params = []
                        
                        actions.append({
                            "name": name,
                            "parameters": params
                        })
            
            return actions
        except Exception as e:
            logger.warning(f"Failed to parse plan file {self.plan_file}: {e}")
            return []
    
    @property
    def plan_length(self) -> int:
        """Number of actions in plan"""
        return len(self.actions)
    
    @property
    def search_time_ms(self) -> float:
        """Extract search time from logs"""
        try:
            for line in self.logs.split('\n'):
                if 'Search time' in line:
                    # Extract "Search time 0 seconds"
                    parts = line.split()
                    if 'seconds' in parts:
                        idx = parts.index('seconds')
                        return float(parts[idx-1]) * 1000.0
            return 0.0
        except:
            return 0.0
    
    @property
    def nodes_expanded(self) -> int:
        """Extract nodes expanded from logs"""
        try:
            for line in self.logs.split('\n'):
                if 'Generated' in line and 'search nodes' in line:
                    # Extract "Generated 5 search nodes"
                    parts = line.split()
                    idx = parts.index('Generated')
                    return int(parts[idx+1])
            return 0
        except:
            return 0


@dataclass
class ValidationResult:
    """Result of HDDL validation"""
    is_valid: bool
    syntax_errors: List[str] = field(default_factory=list)
    semantic_errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    validation_output: str = ""
    

class PANDAWrapper:
    """
    Python interface to PANDA HTN planner binaries
    
    Provides methods to:
    - Parse HDDL domains/problems to internal format
    - Ground lifted problems to SAS+ format
    - Run HTN planning engine
    - Verify plan correctness
    - Convert plans back to HDDL format
    """
    
    def __init__(
        self, 
        panda_root: str,
        timeout: int = 120,
        work_dir: str = None,
        results_dir: str = "./results/panda-results"
    ):
        """
        Initialize PANDA wrapper
        
        Args:
            panda_root: Path to PANDA-HTN directory
            timeout: Maximum seconds for planning (default 120)
            work_dir: Working directory for intermediate files (default: results_dir/panda-temp)
            results_dir: Base directory for all PANDA outputs
        """
        self.panda_root = Path(panda_root)
        self.timeout = timeout
        self.results_dir = Path(results_dir)
        
        # Use consolidated work directory under results
        if work_dir is None:
            self.work_dir = self.results_dir / "panda-temp"
        else:
            self.work_dir = Path(work_dir)
        
        # Binary paths
        self.parser_bin = self.panda_root / "pandaPIparser" / "pandaPIparser"
        self.grounder_bin = self.panda_root / "pandaPIgrounder" / "pandaPIgrounder"
        self.engine_bin = self.panda_root / "pandaPIengine" / "build" / "pandaPIengine"
        
        # Validate binaries exist
        self._validate_binaries()
        
        # Create output directories
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for organized output
        (self.results_dir / "solutions").mkdir(parents=True, exist_ok=True)
        (self.results_dir / "parsed").mkdir(parents=True, exist_ok=True)
        (self.results_dir / "grounded").mkdir(parents=True, exist_ok=True)
        
        logger.info(f"PANDA wrapper initialized with root: {panda_root}")
        logger.info(f"PANDA outputs will be saved to: {self.results_dir}")
    
    def _validate_binaries(self):
        """Ensure all PANDA binaries exist and are executable"""
        binaries = {
            "parser": self.parser_bin,
            "grounder": self.grounder_bin,
            "engine": self.engine_bin
        }
        
        for name, binary in binaries.items():
            if not binary.exists():
                raise FileNotFoundError(
                    f"PANDA {name} binary not found: {binary}\n"
                    f"Please compile PANDA components first."
                )
            if not os.access(binary, os.X_OK):
                raise PermissionError(
                    f"PANDA {name} binary not executable: {binary}\n"
                    f"Run: chmod +x {binary}"
                )
    
    def plan(
        self, 
        domain_file: str, 
        problem_file: str,
        output_name: Optional[str] = None
    ) -> PlannerResult:
        """
        Run complete PANDA pipeline: parse → ground → plan
        
        Args:
            domain_file: Path to HDDL domain file
            problem_file: Path to HDDL problem file
            output_name: Optional name for output files (default: problem filename)
        
        Returns:
            PlannerResult with success status, plan file path, and logs
        """
        domain_path = Path(domain_file)
        problem_path = Path(problem_file)
        
        if not domain_path.exists():
            return PlannerResult(
                success=False,
                plan_file=None,
                logs="",
                error=f"Domain file not found: {domain_file}"
            )
        
        if not problem_path.exists():
            return PlannerResult(
                success=False,
                plan_file=None,
                logs="",
                error=f"Problem file not found: {problem_file}"
            )
        
        # Generate unique filename
        if output_name is None:
            output_name = problem_path.stem
        
        # Use organized subdirectories for different file types
        parsed_file = self.results_dir / "parsed" / f"{output_name}.parsed"
        sas_file = self.results_dir / "grounded" / f"{output_name}.sas"
        plan_file = self.results_dir / "solutions" / f"{output_name}.solution"
        hddl_plan_file = self.results_dir / "solutions" / f"{output_name}.plan"
        
        logs = []
        
        try:
            # Step 1: Parse HDDL → Internal Format
            logger.info(f"[1/4] Parsing {domain_path.name} and {problem_path.name}...")
            logs.append("=== PARSING ===")
            
            result = subprocess.run(
                [
                    str(self.parser_bin),
                    str(domain_path),
                    str(problem_path),
                    str(parsed_file)
                ],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            logs.append(result.stdout)
            if result.stderr:
                logs.append(f"STDERR: {result.stderr}")
            
            if result.returncode != 0 or not parsed_file.exists():
                error_msg = f"Parser failed (exit code {result.returncode})"
                logs.append(f"ERROR: {error_msg}")
                return PlannerResult(
                    success=False,
                    plan_file=None,
                    logs="\n".join(logs),
                    error=error_msg
                )
            
            # Step 2: Ground Lifted → SAS+
            logger.info("[2/4] Grounding problem...")
            logs.append("\n=== GROUNDING ===")
            
            result = subprocess.run(
                [
                    str(self.grounder_bin),
                    str(parsed_file),
                    str(sas_file)
                ],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            logs.append(result.stdout)
            if result.stderr:
                logs.append(f"STDERR: {result.stderr}")
            
            if result.returncode != 0 or not sas_file.exists():
                error_msg = f"Grounder failed (exit code {result.returncode})"
                logs.append(f"ERROR: {error_msg}")
                return PlannerResult(
                    success=False,
                    plan_file=None,
                    logs="\n".join(logs),
                    error=error_msg
                )
            
            # Step 3: Plan with HTN Engine
            logger.info("[3/4] Running HTN planner...")
            logs.append("\n=== PLANNING ===")
            
            result = subprocess.run(
                [
                    str(self.engine_bin),
                    str(sas_file),
                    "-H", "rc2(h=add)",  # RC-FF heuristic
                    "-g", "none"          # No goal ordering
                ],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            # Save plan output
            with open(plan_file, 'w') as f:
                f.write(result.stdout)
            
            logs.append(result.stdout)
            if result.stderr:
                logs.append(f"STDERR: {result.stderr}")
            
            # Check for solution
            if "No solution found" in result.stdout or result.returncode != 0:
                error_msg = "No solution found by planner"
                logs.append(f"ERROR: {error_msg}")
                return PlannerResult(
                    success=False,
                    plan_file=None,
                    logs="\n".join(logs),
                    error=error_msg
                )
            
            # Step 4: Convert Plan to HDDL Format
            logger.info("[4/4] Converting plan to HDDL format...")
            logs.append("\n=== PLAN CONVERSION ===")
            
            result = subprocess.run(
                [
                    str(self.parser_bin),
                    str(domain_path),
                    str(problem_path),
                    "-c", str(plan_file),
                    str(hddl_plan_file)
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            logs.append(result.stdout)
            if result.stderr:
                logs.append(f"STDERR: {result.stderr}")
            
            if result.returncode != 0:
                logger.warning("Plan conversion failed, using raw plan")
            
            # Return HDDL plan if conversion succeeded, else raw plan
            final_plan = hddl_plan_file if hddl_plan_file.exists() else plan_file
            
            logger.info(f"Planning successful! Plan: {final_plan}")
            return PlannerResult(
                success=True,
                plan_file=str(final_plan),
                logs="\n".join(logs)
            )
            
        except subprocess.TimeoutExpired:
            error_msg = f"Planning timeout after {self.timeout} seconds"
            logs.append(f"ERROR: {error_msg}")
            logger.error(error_msg)
            return PlannerResult(
                success=False,
                plan_file=None,
                logs="\n".join(logs),
                error=error_msg
            )
        
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logs.append(f"ERROR: {error_msg}")
            logger.exception("Planning failed with exception")
            return PlannerResult(
                success=False,
                plan_file=None,
                logs="\n".join(logs),
                error=error_msg
            )
    
    def verify_plan(
        self, 
        domain_file: str, 
        problem_file: str,
        plan_file: str
    ) -> Tuple[bool, str]:
        """
        Verify plan correctness using PANDA parser
        
        Args:
            domain_file: Path to HDDL domain
            problem_file: Path to HDDL problem
            plan_file: Path to plan to verify
        
        Returns:
            (is_valid, verification_output)
        """
        try:
            result = subprocess.run(
                [
                    str(self.parser_bin),
                    domain_file,
                    problem_file,
                    "--verify", plan_file
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            output = result.stdout + "\n" + result.stderr
            is_valid = "Plan is valid" in result.stdout
            
            return is_valid, output
            
        except Exception as e:
            return False, f"Verification error: {str(e)}"
    
    def parse_only(
        self,
        domain_file: str,
        problem_file: str,
        output_file: str
    ) -> Tuple[bool, str]:
        """
        Parse HDDL to internal format only (no planning)
        
        Args:
            domain_file: HDDL domain file
            problem_file: HDDL problem file  
            output_file: Output file for parsed format
        
        Returns:
            (success, output_text)
        """
        try:
            result = subprocess.run(
                [
                    str(self.parser_bin),
                    domain_file,
                    problem_file,
                    output_file
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            success = result.returncode == 0
            output = result.stdout + "\n" + result.stderr
            
            return success, output
            
        except Exception as e:
            return False, f"Parse error: {str(e)}"
    
    def validate_hddl(
        self,
        domain_file: str,
        problem_file: str
    ) -> ValidationResult:
        """
        Validate HDDL domain and problem files using PANDA parser
        
        Args:
            domain_file: Path to HDDL domain file
            problem_file: Path to HDDL problem file
        
        Returns:
            ValidationResult with validation status and any errors/warnings
        """
        try:
            # Use parser to validate syntax
            result = subprocess.run(
                [
                    str(self.parser_bin),
                    domain_file,
                    problem_file,
                    "/dev/null"  # We don't need the output file for validation
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            output = result.stdout + "\n" + result.stderr
            is_valid = result.returncode == 0
            
            # Parse errors from output
            syntax_errors = []
            semantic_errors = []
            warnings = []
            
            for line in output.split('\n'):
                line_lower = line.lower()
                if 'error' in line_lower or 'fail' in line_lower:
                    if 'syntax' in line_lower or 'parse' in line_lower:
                        syntax_errors.append(line.strip())
                    else:
                        semantic_errors.append(line.strip())
                elif 'warning' in line_lower:
                    warnings.append(line.strip())
            
            return ValidationResult(
                is_valid=is_valid,
                syntax_errors=syntax_errors,
                semantic_errors=semantic_errors,
                warnings=warnings,
                validation_output=output
            )
            
        except subprocess.TimeoutExpired:
            return ValidationResult(
                is_valid=False,
                syntax_errors=["Validation timeout - file may be too large or parser hung"],
                validation_output="Timeout"
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                syntax_errors=[f"Validation error: {str(e)}"],
                validation_output=str(e)
            )

