"""
PANDA HTN Planner Integration
Python wrapper for PANDA binaries (parser, grounder, engine)
"""

import subprocess
import os
from pathlib import Path
from typing import Tuple, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class PlannerResult:
    """Result of PANDA planning operation"""
    success: bool
    plan_file: Optional[str]
    logs: str
    error: Optional[str] = None
    

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
        work_dir: str = "/tmp/panda"
    ):
        """
        Initialize PANDA wrapper
        
        Args:
            panda_root: Path to PANDA-HTN directory
            timeout: Maximum seconds for planning (default 120)
            work_dir: Working directory for intermediate files
        """
        self.panda_root = Path(panda_root)
        self.timeout = timeout
        self.work_dir = Path(work_dir)
        
        # Binary paths
        self.parser_bin = self.panda_root / "pandaPIparser" / "pandaPIparser"
        self.grounder_bin = self.panda_root / "pandaPIgrounder" / "build" / "pandaPIgrounder"
        self.engine_bin = self.panda_root / "pandaPIengine" / "build" / "pandaPIengine"
        
        # Validate binaries exist
        self._validate_binaries()
        
        # Create work directory
        self.work_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"PANDA wrapper initialized with root: {panda_root}")
    
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
        
        parsed_file = self.work_dir / f"{output_name}.parsed"
        sas_file = self.work_dir / f"{output_name}.sas"
        plan_file = self.work_dir / f"{output_name}.solution"
        hddl_plan_file = self.work_dir / f"{output_name}.plan"
        
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
