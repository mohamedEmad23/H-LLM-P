"""
Quick test script to verify core components are working.
Run this before moving to the next phase.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core import State, PrimitiveTask, CompoundTask, Operator, OperatorLibrary
from loguru import logger

# Configure logger
logger.remove()  # Remove default handler
logger.add(sys.stdout, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")

def test_state():
    """Test State representation"""
    logger.info("Testing State...")
    
    state = State(predicates={
        "at(robot, kitchen)",
        "empty(robot_hand)",
        "at(cup, table)"
    })
    
    assert state.holds("at(robot, kitchen)")
    assert not state.holds("holding(robot, cup)")
    
    # Test state transition
    new_state = state.apply_effects(
        add_list={"holding(robot, cup)"},
        delete_list={"at(cup, table)", "empty(robot_hand)"}
    )
    
    assert new_state.holds("holding(robot, cup)")
    assert not new_state.holds("empty(robot_hand)")
    
    logger.info("✓ State tests passed!")

def test_tasks():
    """Test Task classes"""
    logger.info("Testing Tasks...")
    
    primitive = PrimitiveTask(name="pick_up", parameters={"object": "cup"})
    compound = CompoundTask(name="prepare_coffee", parameters={"type": "espresso"})
    
    assert primitive.is_primitive()
    assert not compound.is_primitive()
    
    sig = primitive.get_signature()
    assert "pick_up" in sig
    assert "cup" in sig
    
    logger.info("✓ Task tests passed!")

def test_operators():
    """Test Operator class"""
    logger.info("Testing Operators...")
    
    # Create a simple operator (using concrete predicates for now)
    pick_up_op = Operator(
        name="pick_up",
        preconditions={"at(robot, kitchen)", "at(cup, kitchen)", "empty(robot_hand)"},
        add_effects={"holding(robot, cup)"},
        delete_effects={"at(cup, kitchen)", "empty(robot_hand)"}
    )
    
    # Test applicability
    state = State(predicates={
        "at(robot, kitchen)",
        "at(cup, kitchen)",
        "empty(robot_hand)"
    })
    
    assert pick_up_op.is_applicable(state)
    
    # Test application
    new_state = pick_up_op.apply(state)
    assert new_state.holds("holding(robot, cup)")
    assert not new_state.holds("empty(robot_hand)")
    
    logger.info("✓ Operator tests passed!")

def test_operator_library():
    """Test OperatorLibrary"""
    logger.info("Testing OperatorLibrary...")
    
    library = OperatorLibrary()
    
    op1 = Operator(name="move", preconditions=set(), add_effects={"moved"}, delete_effects=set())
    op2 = Operator(name="pick", preconditions={"nearby"}, add_effects={"holding"}, delete_effects=set())
    
    library.register(op1)
    library.register(op2)
    
    assert len(library) == 2
    assert "move" in library
    assert library.get("move") is not None
    
    logger.info("✓ OperatorLibrary tests passed!")

if __name__ == "__main__":
    try:
        test_state()
        test_tasks()
        test_operators()
        test_operator_library()
        
        logger.info("\n🎉 All core component tests passed!")
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
