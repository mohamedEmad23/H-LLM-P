"""Unit tests for PlanningAgent"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from src.agents.planning_agent import PlanningAgent


class TestPlanningAgent:
    """Test suite for PlanningAgent"""
    
    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM client"""
        client = Mock()
        client.generate = Mock(return_value="""{
            "strategies": [
                {
                    "name": "optimal_path",
                    "approach": "Find optimal solution path",
                    "advantages": ["Optimal result", "Efficient"],
                    "disadvantages": ["May take longer"],
                    "estimated_complexity": "medium",
                    "estimated_optimality": "optimal"
                },
                {
                    "name": "greedy_fast",
                    "approach": "Fast greedy approach",
                    "advantages": ["Very fast"],
                    "disadvantages": ["Suboptimal"],
                    "estimated_complexity": "low",
                    "estimated_optimality": "suboptimal"
                }
            ],
            "recommended_strategy": "optimal_path",
            "reasoning": "Best for this problem complexity",
            "confidence": 0.85,
            "key_insights": ["Problem is medium complexity", "Optimality important"]
        }""")
        return client
    
    @pytest.fixture
    def planning_agent(self, mock_llm_client):
        """Create PlanningAgent instance"""
        config = {
            "max_strategies": 3,
            "temperature": 0.8,
            "max_tokens": 1500
        }
        return PlanningAgent(
            llm_client=mock_llm_client,
            config=config
        )
    
    @pytest.mark.asyncio
    async def test_planning_agent_initialization(self, planning_agent):
        """Test agent initialization"""
        assert planning_agent.name == "PlanningAgent"
        assert planning_agent.max_strategies == 3
        assert planning_agent.temperature == 0.8
        assert planning_agent.stats["plans_generated"] == 0
    
    @pytest.mark.asyncio
    async def test_process_valid_input(self, planning_agent):
        """Test processing valid input"""
        input_data = {
            "task": "solve_hanoi(3, A, C, B)",
            "domain": "tower_of_hanoi",
            "initial_state": {"disks": [1, 2, 3], "on": "A"},
            "goal": {"on": "C"},
            "constraints": ["no_larger_on_smaller"]
        }
        
        result = await planning_agent.process(input_data)
        
        assert result["success"] is True
        assert "strategies" in result
        assert len(result["strategies"]) == 2
        assert "recommended_strategy" in result
        assert result["recommended_strategy"]["name"] == "optimal_path"
        assert result["confidence"] == 0.85
        assert planning_agent.stats["plans_generated"] == 1
        assert planning_agent.stats["successful_plans"] == 1
    
    @pytest.mark.asyncio
    async def test_process_invalid_input(self, planning_agent):
        """Test processing invalid input (missing required fields)"""
        input_data = {"task": "solve_hanoi(3, A, C, B)"}  # Missing 'domain'
        
        result = await planning_agent.process(input_data)
        
        assert result["success"] is False
        assert "error" in result
        assert "Invalid input data" in result["error"]
    
    @pytest.mark.asyncio
    async def test_rule_based_fallback(self):
        """Test rule-based fallback when no LLM available"""
        agent = PlanningAgent(llm_client=None)
        
        input_data = {
            "task": "solve_hanoi(3, A, C, B)",
            "domain": "tower_of_hanoi",
            "initial_state": {},
            "goal": {}
        }
        
        result = await agent.process(input_data)
        
        assert result["success"] is True
        assert len(result["strategies"]) == 2
        assert result["strategies"][0]["name"] == "greedy_forward"
        assert result["strategies"][1]["name"] == "backward_chaining"
        assert result["confidence"] == 0.5
    
    @pytest.mark.asyncio
    async def test_fallback_llm_on_primary_failure(self, mock_llm_client):
        """Test fallback LLM when primary fails"""
        # Primary LLM fails
        mock_llm_client.generate = Mock(side_effect=Exception("API error"))
        
        # Fallback LLM succeeds
        fallback_client = Mock()
        fallback_client.generate = Mock(return_value="""{
            "strategies": [{"name": "fallback_strategy", "approach": "Fallback approach", 
                           "advantages": ["Works"], "disadvantages": ["Slower"],
                           "estimated_complexity": "low", "estimated_optimality": "suboptimal"}],
            "recommended_strategy": "fallback_strategy",
            "reasoning": "Fallback used",
            "confidence": 0.6
        }""")
        
        agent = PlanningAgent(
            llm_client=mock_llm_client,
            fallback_client=fallback_client
        )
        
        input_data = {
            "task": "solve_hanoi(3, A, C, B)",
            "domain": "tower_of_hanoi"
        }
        
        result = await agent.process(input_data)
        
        assert result["success"] is True
        assert result["recommended_strategy"]["name"] == "fallback_strategy"
        assert agent.stats["fallback_used"] == 1
    
    @pytest.mark.asyncio
    async def test_statistics_tracking(self, planning_agent):
        """Test statistics tracking across multiple runs"""
        input_data = {
            "task": "solve_hanoi(3, A, C, B)",
            "domain": "tower_of_hanoi"
        }
        
        # Run multiple times
        for _ in range(3):
            await planning_agent.process(input_data)
        
        stats = planning_agent.get_statistics()
        
        assert stats["plans_generated"] == 3
        assert stats["successful_plans"] == 3
        assert stats["success_rate"] == 1.0
        assert stats["avg_strategies_per_plan"] == 2.0
        assert stats["avg_confidence"] == 0.85
    
    @pytest.mark.asyncio
    async def test_prompt_building(self, planning_agent):
        """Test prompt building with different inputs"""
        system_prompt, user_prompt = planning_agent._build_planning_prompt(
            task="solve_hanoi(3, A, C, B)",
            domain="tower_of_hanoi",
            initial_state={"disks": [1, 2, 3]},
            goal={"on": "C"},
            constraints=["no_larger_on_smaller"],
            context={"domain_description": "Tower of Hanoi puzzle"}
        )
        
        assert "strategic planning expert" in system_prompt
        assert "HTN" in system_prompt
        assert "solve_hanoi(3, A, C, B)" in user_prompt
        assert "tower_of_hanoi" in user_prompt
        assert "no_larger_on_smaller" in user_prompt
    
    @pytest.mark.asyncio
    async def test_response_parsing(self, planning_agent):
        """Test parsing of LLM responses"""
        # Test valid JSON response
        valid_response = """{
            "strategies": [
                {"name": "test", "approach": "test", "advantages": [], 
                 "disadvantages": [], "estimated_complexity": "low", "estimated_optimality": "suboptimal"}
            ],
            "recommended_strategy": "test",
            "reasoning": "Test reasoning",
            "confidence": 0.7
        }"""
        
        parsed = planning_agent._parse_planning_response(valid_response)
        assert parsed["success"] is True
        assert len(parsed["strategies"]) == 1
        
        # Test JSON in markdown code block
        markdown_response = f"```json\n{valid_response}\n```"
        parsed = planning_agent._parse_planning_response(markdown_response)
        assert parsed["success"] is True
        
        # Test invalid JSON
        invalid_response = "Not JSON at all"
        parsed = planning_agent._parse_planning_response(invalid_response)
        assert parsed["success"] is False
        assert "error" in parsed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
