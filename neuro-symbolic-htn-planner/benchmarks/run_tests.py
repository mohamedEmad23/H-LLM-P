#!/usr/bin/env python3
"""
Simple test runner for Phase 4A
Runs all tests and displays results
"""

import subprocess
import sys


def run_test(test_file):
    """Run a single test file"""
    print(f"\n{'=' * 60}")
    print(f"Running: {test_file}")
    print("=" * 60)

    result = subprocess.run(
        ["python", "-m", "pytest", test_file, "-v", "--tb=short"],
        env={"PYTHONPATH": "."},
        capture_output=False,
    )

    return result.returncode == 0


def main():
    tests = [
        "tests/test_decomposition_agent.py",
        "tests/test_execution_agent.py",
        "tests/test_verification_agent.py",
        "tests/test_e2e_workflow.py",
    ]

    print("\n🧪 Running Phase 4A Test Suite\n")

    results = {}
    for test in tests:
        results[test] = run_test(test)

    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status}: {test}")

    print(f"\nTotal: {passed}/{total} test suites passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print("\n⚠️  SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
