"""
Test script for PANDA integration
Runs complete pipeline: parse → ground → plan → parse plan
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from integrations.panda_wrapper import PANDAWrapper
from integrations.panda_plan_parser import PANDAPlanParser
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_panda_integration():
    """Test complete PANDA integration"""
    
    print("=" * 70)
    print("PANDA HTN Planner Integration Test")
    print("=" * 70)
    print()
    
    # Initialize wrapper
    panda_root = Path(__file__).parent.parent.parent / "PANDA-HTN"
    
    print(f"PANDA Root: {panda_root}")
    print()
    
    try:
        panda = PANDAWrapper(
            panda_root=str(panda_root),
            timeout=60
        )
        print("✓ PANDA wrapper initialized")
        print()
    except Exception as e:
        print(f"✗ Failed to initialize PANDA: {e}")
        return False
    
    # Test domains
    test_cases = [
        {
            "name": "Incomplete Graph Traversal",
            "domain": "../panda-tests/domains/incomplete-graph-domain.hddl",
            "problem": "../panda-tests/problems/incomplete-graph-p01.hddl"
        },
        {
            "name": "Constrained Tower of Hanoi",
            "domain": "../panda-tests/domains/constrained-hanoi-domain.hddl",
            "problem": "../panda-tests/problems/constrained-hanoi-p01.hddl"
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"Test {i}: {test['name']}")
        print("-" * 70)
        
        domain_path = Path(__file__).parent / test['domain']
        problem_path = Path(__file__).parent / test['problem']
        
        # Run planner
        print(f"Domain:  {domain_path.name}")
        print(f"Problem: {problem_path.name}")
        print()
        
        result = panda.plan(
            domain_file=str(domain_path),
            problem_file=str(problem_path)
        )
        
        if result.success:
            print("✓ Planning successful!")
            print(f"✓ Plan file: {result.plan_file}")
            print()
            
            # Parse plan
            parser = PANDAPlanParser()
            try:
                plan = parser.parse_file(result.plan_file)
                print("✓ Plan parsed successfully")
                print()
                print(plan)
                print()
                print(f"Total steps: {len(plan.steps)}")
                print(f"Primitive actions: {len(plan.primitive_actions)}")
                print()
                
                if plan.primitive_actions:
                    print("Action sequence:")
                    for j, action in enumerate(plan.primitive_actions, 1):
                        params = f"({', '.join(action.parameters)})" if action.parameters else ""
                        print(f"  {j}. {action.name}{params}")
                print()
                
            except Exception as e:
                print(f"✗ Plan parsing failed: {e}")
        else:
            print(f"✗ Planning failed: {result.error}")
            print()
            print("Logs:")
            print(result.logs)
        
        print()
        print("=" * 70)
        print()
    
    return True


if __name__ == "__main__":
    success = test_panda_integration()
    sys.exit(0 if success else 1)
