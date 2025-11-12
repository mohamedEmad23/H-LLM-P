"""Unit tests for ContextAgent"""

import pytest
from unittest.mock import Mock
from src.agents.context_agent import ContextAgent


class TestContextAgent:
    """Test suite for ContextAgent"""

    @pytest.fixture
    def context_agent(self):
        """Create ContextAgent instance"""
        config = {"max_history": 50, "context_window": 10, "use_llm_threshold": 0.7}
        return ContextAgent(config=config)

    @pytest.mark.asyncio
    async def test_context_agent_initialization(self, context_agent):
        """Test agent initialization"""
        assert context_agent.name == "ContextAgent"
        assert context_agent.max_history == 50
        assert context_agent.context_window == 10
        assert len(context_agent.interaction_history) == 0
        assert len(context_agent.state_history) == 0
        assert context_agent.stats["contexts_retrieved"] == 0

    @pytest.mark.asyncio
    async def test_log_interaction(self, context_agent):
        """Test logging agent interactions"""
        input_data = {
            "operation": "log_interaction",
            "data": {
                "agent": "PlanningAgent",
                "action": "generate_strategies",
                "input": {"task": "solve_hanoi(3, A, C, B)"},
                "output": {"strategies": 3, "confidence": 0.85},
                "success": True,
            },
        }

        result = await context_agent.process(input_data)

        assert result["success"] is True
        assert "result" in result
        assert len(context_agent.interaction_history) == 1
        assert context_agent.stats["interactions_logged"] == 1

        interaction = context_agent.interaction_history[0]
        assert interaction["agent"] == "PlanningAgent"
        assert interaction["action"] == "generate_strategies"
        assert interaction["success"] is True

    @pytest.mark.asyncio
    async def test_track_state(self, context_agent):
        """Test tracking state changes"""
        input_data = {
            "operation": "track_state",
            "data": {
                "phase": "planning",
                "state": {"disks": [1, 2, 3], "location": "A"},
            },
        }

        result = await context_agent.process(input_data)

        assert result["success"] is True
        assert "result" in result
        assert len(context_agent.state_history) == 1
        assert context_agent.stats["states_tracked"] == 1

        state_record = context_agent.state_history[0]
        assert state_record["phase"] == "planning"
        assert "state" in state_record

    @pytest.mark.asyncio
    async def test_retrieve_context_rule_based(self, context_agent):
        """Test context retrieval (rule-based)"""
        # Log some interactions first
        for i in range(5):
            await context_agent.process(
                {
                    "operation": "log_interaction",
                    "data": {
                        "agent": "TestAgent",
                        "action": f"action_{i}",
                        "success": True,
                    },
                }
            )

        # Track some states
        for i in range(3):
            await context_agent.process(
                {
                    "operation": "track_state",
                    "data": {"phase": "planning", "state": {"step": i}},
                }
            )

        # Retrieve context (simple query - rule-based)
        input_data = {
            "operation": "retrieve_context",
            "data": {
                "query": "recent activity",  # Simple query, complexity < threshold
                "window": 10,
            },
        }

        result = await context_agent.process(input_data)

        assert result["success"] is True
        assert "result" in result
        assert result["method"] == "rule_based"
        assert len(result["result"]["recent_interactions"]) == 5
        assert len(result["result"]["recent_states"]) == 3
        assert context_agent.stats["rule_based_retrievals"] == 1

    @pytest.mark.asyncio
    async def test_retrieve_context_with_filters(self, context_agent):
        """Test context retrieval with phase/agent filters"""
        # Log interactions from different agents
        await context_agent.process(
            {
                "operation": "log_interaction",
                "data": {"agent": "PlanningAgent", "action": "plan", "success": True},
            }
        )
        await context_agent.process(
            {
                "operation": "log_interaction",
                "data": {
                    "agent": "ExecutionAgent",
                    "action": "execute",
                    "success": True,
                },
            }
        )

        # Track states in different phases
        await context_agent.process(
            {"operation": "track_state", "data": {"phase": "planning", "state": {}}}
        )
        await context_agent.process(
            {"operation": "track_state", "data": {"phase": "execution", "state": {}}}
        )

        # Retrieve context filtered by agent
        result = await context_agent.process(
            {
                "operation": "retrieve_context",
                "data": {"query": "activity", "agent": "PlanningAgent"},
            }
        )

        assert result["success"] is True
        interactions = result["result"]["recent_interactions"]
        assert len(interactions) == 1
        assert interactions[0]["agent"] == "PlanningAgent"

    @pytest.mark.asyncio
    async def test_get_history(self, context_agent):
        """Test getting interaction/state history"""
        # Log some data
        for i in range(5):
            await context_agent.process(
                {
                    "operation": "log_interaction",
                    "data": {
                        "agent": "TestAgent",
                        "action": f"action_{i}",
                        "success": True,
                    },
                }
            )

        # Get interaction history
        result = await context_agent.process(
            {"operation": "get_history", "data": {"type": "interaction", "limit": 3}}
        )

        assert result["success"] is True
        assert len(result["result"]["history"]) == 3
        assert result["result"]["total_count"] == 5

    @pytest.mark.asyncio
    async def test_query_complexity_assessment(self, context_agent):
        """Test query complexity assessment"""
        # Simple query
        simple_query = "recent activity"
        simple_complexity = context_agent._assess_query_complexity(simple_query)
        assert simple_complexity < 0.7

        # Complex query with analysis keywords
        complex_query = "Analyze patterns in agent behavior and explain trends"
        complex_complexity = context_agent._assess_query_complexity(complex_query)
        assert complex_complexity > 0.5

        # Empty query
        empty_complexity = context_agent._assess_query_complexity("")
        assert empty_complexity == 0.0

    @pytest.mark.asyncio
    async def test_llm_enhanced_retrieval(self):
        """Test LLM-enhanced context retrieval for complex queries"""
        mock_llm = Mock()
        mock_llm.generate = Mock(
            return_value="""{
            "insights": ["Pattern detected", "Success rate improving"],
            "relevant_interactions": [0, 1],
            "relevant_states": [0],
            "summary": "Overall positive trend",
            "recommendations": ["Continue strategy", "Monitor execution"]
        }"""
        )

        agent = ContextAgent(llm_client=mock_llm)

        # Log some data
        await agent.process(
            {
                "operation": "log_interaction",
                "data": {"agent": "TestAgent", "action": "test", "success": True},
            }
        )

        # Complex query triggering LLM
        result = await agent.process(
            {
                "operation": "retrieve_context",
                "data": {
                    "query": "Analyze patterns and explain why strategies succeeded"  # High complexity
                },
            }
        )

        assert result["success"] is True
        # LLM should be invoked for high complexity query
        assert agent.stats["contexts_retrieved"] == 1

    @pytest.mark.asyncio
    async def test_max_history_limit(self):
        """Test that history respects max_history limit"""
        agent = ContextAgent(config={"max_history": 5})

        # Log 10 interactions (exceeds max_history)
        for i in range(10):
            await agent.process(
                {
                    "operation": "log_interaction",
                    "data": {
                        "agent": "TestAgent",
                        "action": f"action_{i}",
                        "success": True,
                    },
                }
            )

        # Should only keep last 5
        assert len(agent.interaction_history) == 5
        # First interaction should be action_5 (0-4 dropped)
        assert agent.interaction_history[0]["action"] == "action_5"

    @pytest.mark.asyncio
    async def test_agent_activity_summary(self, context_agent):
        """Test agent activity summary generation"""
        # Log interactions from multiple agents
        for agent_name in ["PlanningAgent", "ExecutionAgent"]:
            for i in range(3):
                await context_agent.process(
                    {
                        "operation": "log_interaction",
                        "data": {
                            "agent": agent_name,
                            "action": f"action_{i}",
                            "success": True,
                        },
                    }
                )

        summary = context_agent._get_agent_summary()

        assert "PlanningAgent" in summary
        assert "ExecutionAgent" in summary
        assert summary["PlanningAgent"]["total_interactions"] == 3
        assert len(summary["PlanningAgent"]["recent_actions"]) == 3

    @pytest.mark.asyncio
    async def test_invalid_operation(self, context_agent):
        """Test handling of invalid operation"""
        input_data = {"operation": "invalid_operation", "data": {}}

        result = await context_agent.process(input_data)

        assert result["success"] is False
        assert "Unknown operation" in result["error"]

    @pytest.mark.asyncio
    async def test_statistics(self, context_agent):
        """Test statistics collection"""
        # Perform various operations
        await context_agent.process(
            {
                "operation": "log_interaction",
                "data": {"agent": "TestAgent", "action": "test", "success": True},
            }
        )

        await context_agent.process(
            {"operation": "track_state", "data": {"phase": "planning", "state": {}}}
        )

        await context_agent.process(
            {"operation": "retrieve_context", "data": {"query": "test"}}
        )

        stats = context_agent.get_statistics()

        assert stats["interactions_logged"] == 1
        assert stats["states_tracked"] == 1
        assert stats["contexts_retrieved"] == 1
        assert stats["history_size"] == 1
        assert stats["active_agents"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
