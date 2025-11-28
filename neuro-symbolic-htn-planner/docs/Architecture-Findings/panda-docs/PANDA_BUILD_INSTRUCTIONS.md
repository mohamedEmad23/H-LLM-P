# PANDA Compilation & Setup Guide

**Date**: November 28, 2025  
**Deadline**: January 10, 2026 (43 days remaining)  
**System**: Ubuntu/Debian Linux

---

## Part 1: Install Build Dependencies

### Required Tools

PANDA requires the following tools to compile:

| Tool | Version | Purpose |
|------|---------|---------|
| **g++** | Any recent | C++ compiler |
| **make** | Any recent | Build automation |
| **cmake** | 3.10+ | Build system generator |
| **flex** | 2.6+ | Lexical analyzer generator (parser) |
| **bison** | 3.5+ | Parser generator (parser) |
| **gengetopt** | 2.23+ | Command-line parser generator (engine) |

### Installation Commands

Open terminal in your project directory and run:

```bash
# Update package list
sudo apt update

# Install all dependencies in one command
sudo apt install -y \
    g++ \
    make \
    cmake \
    flex \
    bison \
    gengetopt

# Verify installations
echo "=== Checking installed versions ==="
g++ --version | head -n1
make --version | head -n1
cmake --version | head -n1
flex --version | head -n1
bison --version | head -n1
gengetopt --version | head -n1
```

**Expected Output**:

```text
g++ (Ubuntu 11.4.0-1ubuntu1~22.04) 11.4.0
GNU Make 4.3
cmake version 3.22.1
flex 2.6.4
bison (GNU Bison) 3.8.2
gengetopt 2.23
```

**Note**: Exact versions may differ. As long as you have:
- flex >= 2.6
- bison >= 3.5
- gengetopt >= 2.23
- cmake >= 3.10

You're good to proceed.

---

## Part 2: Compile PANDA Components

PANDA has **2 components** to compile (grounder is missing from your repo):

1. **pandaPIparser**: Parses HDDL → internal format
2. **pandaPIengine**: Plans on grounded problems

### Component 1: Compile pandaPIparser

```bash
# Navigate to parser directory
cd "/home/mohammed-emad/VS-CODE/B.Sc Thesis/gpt-htn-thesis/PANDA-HTN/pandaPIparser"

# Clean any previous build artifacts
make clean

# Compile parser (this will take 1-2 minutes)
make -j$(nproc)

# Verify binary was created
ls -lh pandaPIparser

# Test parser binary
./pandaPIparser --help
```

**Expected Output**:

```text
-rwxr-xr-x 1 user user 2.3M Nov 28 10:30 pandaPIparser

Usage: pandaPIparser [OPTIONS] domain.hddl problem.hddl [output.htn]
...
```

**If compilation fails**, check:
- Flex/bison versions are correct
- You have gengetopt installed (needed for cmdline.h generation)
- Run `make clean` and try again

---

### Component 2: Compile pandaPIengine

```bash
# Navigate to engine directory
cd "/home/mohammed-emad/VS-CODE/B.Sc Thesis/gpt-htn-thesis/PANDA-HTN/pandaPIengine"

# Create build directory
mkdir -p build
cd build

# Generate build files with cmake
cmake ../src

# Compile engine (this will take 2-3 minutes)
make -j$(nproc)

# Verify binary was created
ls -lh pandaPIengine

# Test engine binary
./pandaPIengine --help
```

**Expected Output**:

```text
-rwxr-xr-x 1 user user 1.8M Nov 28 10:35 pandaPIengine

Usage: pandaPIengine [OPTIONS] problem.sas
...
```

**Important Notes**:
1. We're compiling **WITHOUT** optional features (ILP, SAT, BDD) - you don't need them
2. If cmake fails, ensure you're in `pandaPIengine/build` directory
3. The binary will be in `build/pandaPIengine`, not the root directory

---

### Missing Component: pandaPIgrounder

**CRITICAL ISSUE**: Your PANDA-HTN folder only has `pandaPIparser` and `pandaPIengine`. You're **missing pandaPIgrounder** which is required for the pipeline:

```text
parser → grounder → engine
  ❌ MISSING
```

**Two Options**:

#### Option A: Download pandaPIgrounder (Recommended)

```bash
cd "/home/mohammed-emad/VS-CODE/B.Sc Thesis/gpt-htn-thesis/PANDA-HTN"

# Clone grounder repository
git clone https://github.com/panda-planner-dev/pandaPIgrounder.git

# Compile grounder
cd pandaPIgrounder
mkdir -p build
cd build
cmake ../src
make -j$(nproc)

# Verify
ls -lh pandaPIgrounder
./pandaPIgrounder --help
```

#### Option B: Use Existing Test Files

The parser has test files that might already be grounded. We can check and potentially skip the grounder for initial testing.

**I recommend Option A** - you need the complete pipeline for your thesis.

---

## Part 3: Test PANDA Pipeline

### Create Test Directory

```bash
# Create workspace for testing
mkdir -p "/home/mohammed-emad/VS-CODE/B.Sc Thesis/gpt-htn-thesis/neuro-symbolic-htn-planner/src/panda-tests"
cd "/home/mohammed-emad/VS-CODE/B.Sc Thesis/gpt-htn-thesis/neuro-symbolic-htn-planner/src/panda-tests"
```

### Test 1: Simple Empty Domain

```bash
# Copy test files from parser
cp "../../../PANDA-HTN/pandaPIparser/tests/empty-d.hddl" ./domain.hddl
cp "../../../PANDA-HTN/pandaPIparser/tests/empty-p.hddl" ./problem.hddl

# Run parser
../../../PANDA-HTN/pandaPIparser/pandaPIparser domain.hddl problem.hddl output.parsed

# Check output
cat output.parsed
```

**Expected**: File `output.parsed` created with internal PANDA format.

### Test 2: Full Pipeline (After Installing Grounder)

```bash
# Parse HDDL to internal format
../../../PANDA-HTN/pandaPIparser/pandaPIparser domain.hddl problem.hddl problem.parsed

# Ground problem (convert lifted → ground)
../../../PANDA-HTN/pandaPIgrounder/build/pandaPIgrounder problem.parsed problem.sas

# Plan with engine
../../../PANDA-HTN/pandaPIengine/build/pandaPIengine problem.sas > solution.txt

# Convert plan back to HDDL
../../../PANDA-HTN/pandaPIparser/pandaPIparser domain.hddl problem.hddl -c solution.txt plan.hddl

# View final plan
cat plan.hddl
```

---

## Part 4: Build Convenience Script

Create a wrapper script for easy testing. The actual binary locations are:
- Parser: `pandaPIparser/pandaPIparser`
- Grounder: `pandaPIgrounder/pandaPIgrounder`
- Engine: `pandaPIengine/build/pandaPIengine`

```bash
cd "/home/mohammed-emad/VS-CODE/B.Sc_Thesis/gpt-htn-thesis/neuro-symbolic-htn-planner"

cat > run_panda.sh << 'EOF'
#!/bin/bash

# PANDA Pipeline Runner
# Usage: ./run_panda.sh domain.hddl problem.hddl

if [ $# -ne 2 ]; then
    echo "Usage: $0 domain.hddl problem.hddl"
    exit 1
fi

DOMAIN="$1"
PROBLEM="$2"
BASE=$(basename "$PROBLEM" .hddl)

PANDA_ROOT="/home/mohammed-emad/VS-CODE/B.Sc_Thesis/gpt-htn-thesis/PANDA-HTN"
PARSER="$PANDA_ROOT/pandaPIparser/pandaPIparser"
GROUNDER="$PANDA_ROOT/pandaPIgrounder/pandaPIgrounder"
ENGINE="$PANDA_ROOT/pandaPIengine/build/pandaPIengine"

echo "=== PANDA Pipeline ==="
echo "Domain:  $DOMAIN"
echo "Problem: $PROBLEM"
echo ""

# Verify binaries exist
for binary in "$PARSER" "$GROUNDER" "$ENGINE"; do
    if [ ! -f "$binary" ]; then
        echo "ERROR: Binary not found: $binary"
        exit 1
    fi
done

# Step 1: Parse
echo "[1/4] Parsing HDDL..."
$PARSER "$DOMAIN" "$PROBLEM" "${BASE}.parsed" 2>&1 | tee "${BASE}.parse.log"
if [ ! -f "${BASE}.parsed" ]; then
    echo "ERROR: Parsing failed"
    exit 1
fi
echo "✓ Parsing successful"

# Step 2: Ground
echo "[2/4] Grounding problem..."
$GROUNDER "${BASE}.parsed" "${BASE}.sas" 2>&1 | tee "${BASE}.ground.log"
if [ ! -f "${BASE}.sas" ]; then
    echo "ERROR: Grounding failed"
    exit 1
fi
echo "✓ Grounding successful"

# Step 3: Plan
echo "[3/4] Planning..."
$ENGINE "${BASE}.sas" 2>&1 | tee "${BASE}.solution"
if [ ! -s "${BASE}.solution" ]; then
    echo "WARNING: No solution found (problem may be unsolvable)"
else
    echo "✓ Planning successful"
fi

# Step 4: Convert plan (optional)
echo "[4/4] Converting plan to HDDL..."
if [ -s "${BASE}.solution" ]; then
    $PARSER "$DOMAIN" "$PROBLEM" -c "${BASE}.solution" "${BASE}.plan" 2>&1 | tee "${BASE}.convert.log"
    if [ -f "${BASE}.plan" ]; then
        echo "✓ Plan conversion successful"
        echo ""
        echo "=== FINAL PLAN ==="
        cat "${BASE}.plan"
    fi
else
    echo "⚠ Skipping conversion (no solution found)"
fi

echo ""
echo "=== COMPLETE ==="
echo "Output files:"
ls -lh "${BASE}".* 2>/dev/null | awk '{print "  " $NF " (" $5 ")"}'
EOF

chmod +x run_panda.sh
```

Test the script with an empty domain first:

```bash
cd "/home/mohammed-emad/VS-CODE/B.Sc_Thesis/gpt-htn-thesis/neuro-symbolic-htn-planner"
mkdir -p panda-test-run
cd panda-test-run
cp ../../PANDA-HTN/pandaPIparser/tests/empty-d.hddl domain.hddl
cp ../../PANDA-HTN/pandaPIparser/tests/empty-p.hddl problem.hddl
../run_panda.sh domain.hddl problem.hddl
```

---

## Part 5: Troubleshooting

### Issue 1: "flex: command not found"

```bash
sudo apt install flex
```

### Issue 2: "bison: command not found"

```bash
sudo apt install bison
```

### Issue 3: "gengetopt: command not found"

```bash
sudo apt install gengetopt
```

### Issue 4: "error: 'yylineno' undeclared"

This means flex version is too old. Install flex 2.6+:

```bash
flex --version  # Check version
sudo apt install flex=2.6.4-8  # Specific version
```

### Issue 5: Parser compiles but binary not executable

```bash
chmod +x pandaPIparser
```

### Issue 6: Engine cmake fails

```bash
# Make sure you're in build directory
cd pandaPIengine
rm -rf build
mkdir build
cd build
cmake ../src
```

### Issue 7: Missing grounder

See "Option A: Download pandaPIgrounder" above.

---

## Expected File Structure After Compilation

```text
PANDA-HTN/
├── pandaPIparser/
│   ├── src/
│   ├── tests/
│   ├── makefile
│   └── pandaPIparser  ← BINARY (2.3MB) - IN PARSER ROOT
├── pandaPIgrounder/
│   ├── src/
│   ├── cpddl/
│   ├── h2-fd-preprocessor/
│   ├── build.sh
│   └── pandaPIgrounder  ← BINARY (1.5MB) - IN GROUNDER ROOT
└── pandaPIengine/
    ├── src/
    └── build/
        └── pandaPIengine  ← BINARY (1.8MB) - IN BUILD SUBDIR
```

**Key Differences from Previous Documentation**:
- `pandaPIparser` binary is in the parser root, NOT in a build folder
- `pandaPIgrounder` binary is in the grounder root after running `build.sh`
- `pandaPIengine` binary is in `build/` subfolder

---

## Next Steps After Compilation

1. ✅ Install dependencies
2. ✅ Compile pandaPIparser
3. ✅ Compile pandaPIengine
4. ⚠️ Download & compile pandaPIgrounder
5. ✅ Create test directory
6. ✅ Create run_panda.sh script
7. 🔄 Test with simple domain
8. 🔄 Convert complex reasoning problem to HDDL
9. 🔄 Implement Python wrapper classes

**Time Estimate**:
- Dependencies installation: 5 minutes
- Compilation: 5-10 minutes
- Testing: 10 minutes
- **Total: ~20-30 minutes**

---

## Summary of Commands (Quick Reference)

```bash
# 1. Install dependencies
sudo apt update && sudo apt install -y g++ make cmake flex bison gengetopt

# 2. Compile parser (binary goes to pandaPIparser root)
cd /home/mohammed-emad/VS-CODE/B.Sc_Thesis/gpt-htn-thesis/PANDA-HTN/pandaPIparser
make clean && make -j$(nproc)
./pandaPIparser --help

# 3. Compile grounder using build.sh (binary goes to pandaPIgrounder root)
cd ../pandaPIgrounder
bash build.sh
./pandaPIgrounder --help

# 4. Compile engine (binary goes to pandaPIengine/build/)
cd ../pandaPIengine
mkdir -p build && cd build
cmake ../src && make -j$(nproc)
./pandaPIengine --help

# 5. Test pipeline
cd /home/mohammed-emad/VS-CODE/B.Sc_Thesis/gpt-htn-thesis/neuro-symbolic-htn-planner
mkdir -p panda-test-run && cd panda-test-run
cp ../../PANDA-HTN/pandaPIparser/tests/empty-d.hddl domain.hddl
cp ../../PANDA-HTN/pandaPIparser/tests/empty-p.hddl problem.hddl
../run_panda.sh domain.hddl problem.hddl
```

Ready to start!
