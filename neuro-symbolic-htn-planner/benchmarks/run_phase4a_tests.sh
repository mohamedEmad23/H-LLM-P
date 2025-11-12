#!/bin/bash
#
# Master Test Suite for Phase 4A - Multi-Agent HTN System
#
# This script runs all unit and integration tests for the 3-agent
# architecture and generates a comprehensive test report.

echo "════════════════════════════════════════════════════════════════"
echo "  🧪 PHASE 4A TEST SUITE - Multi-Agent HTN System"
echo "════════════════════════════════════════════════════════════════"
echo ""

export PYTHONPATH=.

TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to run a test file
run_test() {
    local test_file=$1
    local test_name=$2

    echo "──────────────────────────────────────────────────────────────"
    echo "📋 Running: $test_name"
    echo "──────────────────────────────────────────────────────────────"

    if pytest "$test_file" -v; then
        echo -e "${GREEN}✅ PASSED${NC}: $test_name"
        ((PASSED_TESTS++))
    else
        echo -e "${RED}❌ FAILED${NC}: $test_name"
        ((FAILED_TESTS++))
    fi

    ((TOTAL_TESTS++))
    echo ""
}

# Run all tests
echo "🔬 Starting Test Execution..."
echo ""

run_test "tests/test_decomposition_agent.py" "DecompositionAgent Tests"
run_test "tests/test_execution_agent.py" "ExecutionAgent Tests"
run_test "tests/test_verification_agent.py" "VerificationAgent Tests"
run_test "tests/test_e2e_workflow.py" "End-to-End Workflow Tests"

# Generate summary
echo "════════════════════════════════════════════════════════════════"
echo "  📊 TEST SUMMARY"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Total Test Suites: $TOTAL_TESTS"
echo -e "Passed: ${GREEN}$PASSED_TESTS${NC}"
echo -e "Failed: ${RED}$FAILED_TESTS${NC}"
echo ""

SUCCESS_RATE=$((PASSED_TESTS * 100 / TOTAL_TESTS))
echo "Success Rate: ${SUCCESS_RATE}%"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}🎉 ALL TESTS PASSED!${NC}"
    echo ""
    echo "✅ Phase 4A Core Implementation: COMPLETE"
    echo "✅ DecompositionAgent: Fully Tested"
    echo "✅ ExecutionAgent: Fully Tested"
    echo "✅ VerificationAgent: Fully Tested"
    echo "✅ CoreWorkflow: Integration Verified"
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    exit 0
else
    echo -e "${RED}⚠️  SOME TESTS FAILED${NC}"
    echo "Please review the output above for details."
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    exit 1
fi
