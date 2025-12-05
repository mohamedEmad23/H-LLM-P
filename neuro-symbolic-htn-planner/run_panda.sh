#!/bin/bash

# PANDA Pipeline Runner
# Usage: ./run_panda.sh domain.hddl problem.hddl
# This script runs the complete PANDA pipeline: parse → ground → plan

if [ $# -ne 2 ]; then
    echo "Usage: $0 domain.hddl problem.hddl"
    echo ""
    echo "Example:"
    echo "  mkdir -p panda-test-run && cd panda-test-run"
    echo "  cp ../../PANDA-HTN/pandaPIparser/tests/empty-d.hddl domain.hddl"
    echo "  cp ../../PANDA-HTN/pandaPIparser/tests/empty-p.hddl problem.hddl"
    echo "  ../run_panda.sh domain.hddl problem.hddl"
    exit 1
fi

DOMAIN="$1"
PROBLEM="$2"
BASE=$(basename "$PROBLEM" .hddl)

# Set absolute paths to binaries
PANDA_ROOT="/home/mohammed-emad/VS-CODE/B.Sc_Thesis/gpt-htn-thesis/PANDA-HTN"
PARSER="$PANDA_ROOT/pandaPIparser/pandaPIparser"
GROUNDER="$PANDA_ROOT/pandaPIgrounder/pandaPIgrounder"
ENGINE="$PANDA_ROOT/pandaPIengine/build/pandaPIengine"

echo "=========================================="
echo "PANDA Pipeline Runner"
echo "=========================================="
echo "Domain:  $DOMAIN"
echo "Problem: $PROBLEM"
echo "Base:    $BASE"
echo ""

# Verify domain and problem files exist
if [ ! -f "$DOMAIN" ]; then
    echo "ERROR: Domain file not found: $DOMAIN"
    exit 1
fi

if [ ! -f "$PROBLEM" ]; then
    echo "ERROR: Problem file not found: $PROBLEM"
    exit 1
fi

# Verify binaries exist
echo "Checking binaries..."
for binary in "$PARSER" "$GROUNDER" "$ENGINE"; do
    if [ ! -f "$binary" ]; then
        echo "ERROR: Binary not found: $binary"
        exit 1
    fi
    echo "  ✓ $(basename $binary)"
done
echo ""

# Step 1: Parse HDDL files
echo "[1/4] Parsing HDDL to internal format..."
$PARSER "$DOMAIN" "$PROBLEM" "${BASE}.parsed" > "${BASE}.parse.log" 2>&1

if [ ! -f "${BASE}.parsed" ]; then
    echo "  ✗ FAILED"
    echo ""
    echo "Parse Error Output:"
    cat "${BASE}.parse.log"
    exit 1
fi

PARSED_SIZE=$(stat -f%z "${BASE}.parsed" 2>/dev/null || stat -c%s "${BASE}.parsed" 2>/dev/null)
echo "  ✓ Success (parsed file: $PARSED_SIZE bytes)"
echo ""

# Step 2: Ground the problem
echo "[2/4] Grounding problem (lifted → ground)..."
$GROUNDER "${BASE}.parsed" "${BASE}.sas" > "${BASE}.ground.log" 2>&1

if [ ! -f "${BASE}.sas" ]; then
    echo "  ✗ FAILED"
    echo ""
    echo "Grounding Error Output:"
    cat "${BASE}.ground.log"
    exit 1
fi

SAS_SIZE=$(stat -f%z "${BASE}.sas" 2>/dev/null || stat -c%s "${BASE}.sas" 2>/dev/null)
echo "  ✓ Success (grounded file: $SAS_SIZE bytes)"
echo ""

# Step 3: Plan
echo "[3/4] Planning with HTN engine..."
$ENGINE "${BASE}.sas" > "${BASE}.solution" 2>&1

if [ ! -f "${BASE}.solution" ]; then
    echo "  ✗ FAILED"
    echo ""
    echo "Planning Error Output:"
    cat "${BASE}.solution"
    exit 1
fi

SOLUTION_SIZE=$(stat -f%z "${BASE}.solution" 2>/dev/null || stat -c%s "${BASE}.solution" 2>/dev/null)

if [ $SOLUTION_SIZE -eq 0 ]; then
    echo "  ⚠ No solution found (problem may be unsolvable)"
else
    echo "  ✓ Solution found (plan file: $SOLUTION_SIZE bytes)"
fi
echo ""

# Step 4: Convert plan back to HDDL (optional)
if [ -s "${BASE}.solution" ]; then
    echo "[4/4] Converting plan to HDDL format..."
    $PARSER "$DOMAIN" "$PROBLEM" -c "${BASE}.solution" "${BASE}.plan" > "${BASE}.convert.log" 2>&1
    
    if [ -f "${BASE}.plan" ]; then
        PLAN_SIZE=$(stat -f%z "${BASE}.plan" 2>/dev/null || stat -c%s "${BASE}.plan" 2>/dev/null)
        echo "  ✓ Success (HDDL plan: $PLAN_SIZE bytes)"
        echo ""
        echo "=========================================="
        echo "FINAL PLAN"
        echo "=========================================="
        cat "${BASE}.plan"
        echo ""
    else
        echo "  ⚠ Conversion skipped or failed"
    fi
else
    echo "[4/4] Skipping plan conversion (no solution)"
fi

echo ""
echo "=========================================="
echo "PIPELINE COMPLETE"
echo "=========================================="
echo "Output files created:"
ls -lh "${BASE}".* 2>/dev/null | awk '{printf "  %-30s %8s\n", $NF, $5}'
echo ""
