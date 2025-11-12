#!/bin/bash
echo "================================================================================"
echo "Phase 3: Strategic Decomposition Engine - Test Runner"
echo "================================================================================"
echo ""

# Activate virtual environment
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif [ -f "../.venv/bin/activate" ]; then
    source ../.venv/bin/activate
fi

echo "Running Household Tasks Test Suite..."
echo ""
python tests/test_household_tasks.py

echo ""
echo "Results saved to:"
echo "  - results/household_tasks_summary.md"
echo "  - results/household_tasks_results.json"
