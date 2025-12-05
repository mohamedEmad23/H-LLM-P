#!/bin/bash

# PANDA HTN Planner - Complete Build Script
# Compiles all PANDA components and tests installation

set -e  # Exit on error

echo "======================================================================"
echo "PANDA HTN Planner - Build Script"
echo "======================================================================"
echo ""

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PANDA_ROOT="$SCRIPT_DIR/PANDA-HTN"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Check dependencies
echo "[Step 1/6] Checking build dependencies..."
echo ""

check_command() {
    if command -v $1 &> /dev/null; then
        version=$($1 --version 2>&1 | head -n1)
        echo -e "${GREEN}✓${NC} $1: $version"
        return 0
    else
        echo -e "${RED}✗${NC} $1: NOT FOUND"
        return 1
    fi
}

all_deps_ok=true

check_command g++ || all_deps_ok=false
check_command make || all_deps_ok=false
check_command cmake || all_deps_ok=false
check_command flex || all_deps_ok=false
check_command bison || all_deps_ok=false
check_command gengetopt || all_deps_ok=false

echo ""

if [ "$all_deps_ok" = false ]; then
    echo -e "${RED}Missing dependencies!${NC}"
    echo ""
    echo "Install with:"
    echo "  sudo apt update"
    echo "  sudo apt install -y g++ make cmake flex bison gengetopt"
    echo ""
    exit 1
fi

echo -e "${GREEN}All dependencies found!${NC}"
echo ""

# Step 2: Download pandaPIgrounder if missing
echo "[Step 2/6] Checking for pandaPIgrounder..."
echo ""

if [ ! -d "$PANDA_ROOT/pandaPIgrounder" ]; then
    echo -e "${YELLOW}pandaPIgrounder not found. Downloading...${NC}"
    cd "$PANDA_ROOT"
    git clone https://github.com/panda-planner-dev/pandaPIgrounder.git
    echo -e "${GREEN}✓ Downloaded pandaPIgrounder${NC}"
else
    echo -e "${GREEN}✓ pandaPIgrounder found${NC}"
fi

echo ""

# Step 3: Compile pandaPIparser
echo "[Step 3/6] Compiling pandaPIparser..."
echo ""

cd "$PANDA_ROOT/pandaPIparser"

# Clean previous build
make clean 2>/dev/null || true

# Compile
if make -j$(nproc); then
    if [ -f "pandaPIparser" ] && [ -x "pandaPIparser" ]; then
        echo -e "${GREEN}✓ pandaPIparser compiled successfully${NC}"
        ls -lh pandaPIparser
    else
        echo -e "${RED}✗ pandaPIparser binary not created${NC}"
        exit 1
    fi
else
    echo -e "${RED}✗ pandaPIparser compilation failed${NC}"
    exit 1
fi

echo ""

# Step 4: Compile pandaPIgrounder
echo "[Step 4/6] Compiling pandaPIgrounder..."
echo ""

cd "$PANDA_ROOT/pandaPIgrounder"

# Create build directory
mkdir -p build
cd build

# Clean previous build
rm -f CMakeCache.txt
rm -rf CMakeFiles

# Configure and compile
if cmake ../src && make -j$(nproc); then
    if [ -f "pandaPIgrounder" ] && [ -x "pandaPIgrounder" ]; then
        echo -e "${GREEN}✓ pandaPIgrounder compiled successfully${NC}"
        ls -lh pandaPIgrounder
    else
        echo -e "${RED}✗ pandaPIgrounder binary not created${NC}"
        exit 1
    fi
else
    echo -e "${RED}✗ pandaPIgrounder compilation failed${NC}"
    exit 1
fi

echo ""

# Step 5: Compile pandaPIengine
echo "[Step 5/6] Compiling pandaPIengine..."
echo ""

cd "$PANDA_ROOT/pandaPIengine"

# Create build directory
mkdir -p build
cd build

# Clean previous build
rm -f CMakeCache.txt
rm -rf CMakeFiles

# Configure and compile
if cmake ../src && make -j$(nproc); then
    if [ -f "pandaPIengine" ] && [ -x "pandaPIengine" ]; then
        echo -e "${GREEN}✓ pandaPIengine compiled successfully${NC}"
        ls -lh pandaPIengine
    else
        echo -e "${RED}✗ pandaPIengine binary not created${NC}"
        exit 1
    fi
else
    echo -e "${RED}✗ pandaPIengine compilation failed${NC}"
    exit 1
fi

echo ""

# Step 6: Test with simple domain
echo "[Step 6/6] Testing PANDA pipeline..."
echo ""

cd "$SCRIPT_DIR"

# Check if test files exist
TEST_DOMAIN="$PANDA_ROOT/pandaPIparser/tests/empty-d.hddl"
TEST_PROBLEM="$PANDA_ROOT/pandaPIparser/tests/empty-p.hddl"

if [ ! -f "$TEST_DOMAIN" ] || [ ! -f "$TEST_PROBLEM" ]; then
    echo -e "${YELLOW}Test files not found, skipping pipeline test${NC}"
else
    echo "Running test: empty domain"
    echo ""
    
    PARSER="$PANDA_ROOT/pandaPIparser/pandaPIparser"
    GROUNDER="$PANDA_ROOT/pandaPIgrounder/build/pandaPIgrounder"
    ENGINE="$PANDA_ROOT/pandaPIengine/build/pandaPIengine"
    
    TEMP_DIR=$(mktemp -d)
    
    # Parse
    if $PARSER "$TEST_DOMAIN" "$TEST_PROBLEM" "$TEMP_DIR/test.parsed" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Parser works${NC}"
    else
        echo -e "${RED}✗ Parser test failed${NC}"
        rm -rf "$TEMP_DIR"
        exit 1
    fi
    
    # Ground
    if $GROUNDER "$TEMP_DIR/test.parsed" "$TEMP_DIR/test.sas" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Grounder works${NC}"
    else
        echo -e "${RED}✗ Grounder test failed${NC}"
        rm -rf "$TEMP_DIR"
        exit 1
    fi
    
    # Plan
    if $ENGINE "$TEMP_DIR/test.sas" > "$TEMP_DIR/test.solution" 2>&1; then
        echo -e "${GREEN}✓ Engine works${NC}"
    else
        echo -e "${YELLOW}⚠ Engine test completed (may have no solution for empty domain)${NC}"
    fi
    
    # Cleanup
    rm -rf "$TEMP_DIR"
fi

echo ""
echo "======================================================================"
echo -e "${GREEN}PANDA BUILD COMPLETE!${NC}"
echo "======================================================================"
echo ""
echo "Binaries:"
echo "  Parser:   $PANDA_ROOT/pandaPIparser/pandaPIparser"
echo "  Grounder: $PANDA_ROOT/pandaPIgrounder/build/pandaPIgrounder"
echo "  Engine:   $PANDA_ROOT/pandaPIengine/build/pandaPIengine"
echo ""
echo "Next steps:"
echo "  1. Test Python integration: python src/test_panda.py"
echo "  2. Run custom domains in: panda-tests/"
echo ""
