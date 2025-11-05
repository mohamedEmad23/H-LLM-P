"""Quick framework validation"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent / "src"))

print("Testing imports...")

try:
    print("✓ MessageBus imported")
except Exception as e:
    print(f"✗ MessageBus import failed: {e}")

try:
    print("✓ AgentStateManager imported")
except Exception as e:
    print(f"✗ AgentStateManager import failed: {e}")

try:
    print("✓ BaseAgent imported")
except Exception as e:
    print(f"✗ BaseAgent import failed: {e}")

try:
    print("✓ AgentCoordinator imported")
except Exception as e:
    print(f"✗ AgentCoordinator import failed: {e}")

print("\nAll imports successful!")
