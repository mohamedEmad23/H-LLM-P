"""
ContextAgent - State Tracking & Context Management

Maintains execution history, tracks agent interactions, and provides
relevant context to other agents for improved decision-making.

Enhanced with PANDA method library integration for HTN planning.
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger
from collections import deque

from .base_agent import BaseAgent
from ..integrations.panda_method_library import PANDAMethodLibrary


class ContextAgent(BaseAgent):
    """
    Agent specialized in context management and state tracking

    Maintains history of agent interactions, tracks state changes,
    and provides relevant context retrieval for improved planning.

    Intelligence Type: Hybrid (20% LLM, 80% rules)
    Primary LLM: Gemini 2.0 - Complex reasoning (4-6s) - ONLY when needed
    Fallback LLM: Not required (rule-based fallback)
    """

    def __init__(
        self,
        name: str = "ContextAgent",
        llm_client=None,
        fallback_client=None,
        config: Optional[dict] = None,
    ):
        """
        Initialize ContextAgent

        Args:
            name: Agent name
            llm_client: Primary LLM client (should be Gemini 2.0)
            fallback_client: Fallback LLM client (optional)
            config: Configuration dict
        """
        super().__init__(name, llm_client, config or {})
        self.fallback_client = fallback_client

        # Agent-specific config
        self.max_history = config.get("max_history", 100) if config else 100
        self.context_window = config.get("context_window", 10) if config else 10
        self.use_llm_threshold = config.get("use_llm_threshold", 0.7) if config else 0.7

        # State tracking (rule-based)
        self.interaction_history: deque = deque(maxlen=self.max_history)
        self.state_history: deque = deque(maxlen=self.max_history)
        self.agent_activities: Dict[str, List] = {}

        # PANDA integration - Method library for HTN planning
        method_library_path = config.get("method_library_path", "./results/panda-results/method_library.json") if config else "./results/panda-results/method_library.json"
        self.panda_method_library = PANDAMethodLibrary(storage_path=method_library_path)

        # Statistics
        self.stats = {
            "contexts_retrieved": 0,
            "states_tracked": 0,
            "interactions_logged": 0,
            "llm_invocations": 0,
            "rule_based_retrievals": 0,
            "panda_methods_stored": 0,
            "panda_methods_retrieved": 0,
        }

    async def process(self, input_data: Dict) -> Dict:
        """
        Main processing method

        Supports multiple operations:
        - 'log_interaction': Log agent interaction
        - 'track_state': Track state change
        - 'retrieve_context': Get relevant context
        - 'get_history': Get interaction history

        Args:
            input_data: {
                "operation": "log_interaction|track_state|retrieve_context|get_history",
                "data": {...}  # Operation-specific data
            }

        Returns:
            {
                "success": bool,
                "result": Any,  # Operation-specific result
                "error": str (if failed)
            }
        """
        start_time = datetime.now()

        # Validate input
        if not self.validate_input(input_data):
            return {"success": False, "error": "Invalid input data", "agent": self.name}

        operation = input_data["operation"]
        data = input_data.get("data", {})

        logger.info(f"Processing operation: {operation}")

        # Route to appropriate handler
        if operation == "log_interaction":
            operation_result = self._log_interaction(data)
        elif operation == "track_state":
            operation_result = self._track_state(data)
        elif operation == "retrieve_context":
            operation_result = await self._retrieve_context(data)
        elif operation == "get_history":
            operation_result = self._get_history(data)
        elif operation == "store_method":
            operation_result = self._store_panda_method(data)
        elif operation == "retrieve_method":
            operation_result = self._retrieve_panda_method(data)
        elif operation == "update_method_success":
            operation_result = self._update_method_success(data)
        elif operation == "store_panda_trace":
            operation_result = self._store_panda_trace(data)
        else:
            operation_result = {
                "success": False,
                "error": f"Unknown operation: {operation}",
            }

        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        # Build result dict
        result = {
            "success": operation_result["success"],
            "result": operation_result.get("result", operation_result),
            "agent": self.name,
            "processing_time_ms": processing_time,
        }

        # Add any additional fields from operation result
        if "error" in operation_result:
            result["error"] = operation_result["error"]
        if "method" in operation_result:
            result["method"] = operation_result["method"]
        if "complexity" in operation_result:
            result["complexity"] = operation_result["complexity"]

        logger.info(f"Operation {operation} complete in {processing_time:.1f}ms")

        return result

    def _log_interaction(self, data: Dict) -> Dict:
        """
        Log agent interaction (rule-based)

        Args:
            data: {
                "agent": "PlanningAgent",
                "action": "generate_strategies",
                "input": {...},
                "output": {...},
                "timestamp": "..."
            }
        """
        try:
            timestamp = data.get("timestamp", datetime.now().isoformat())
            agent = data.get("agent", "unknown")

            # Create interaction record
            interaction = {
                "timestamp": timestamp,
                "agent": agent,
                "action": data.get("action", "unknown"),
                "input_summary": self._summarize_data(data.get("input", {})),
                "output_summary": self._summarize_data(data.get("output", {})),
                "success": data.get("success", True),
            }

            # Store in history
            self.interaction_history.append(interaction)

            # Track per-agent activity
            if agent not in self.agent_activities:
                self.agent_activities[agent] = []
            self.agent_activities[agent].append(interaction)

            self.stats["interactions_logged"] += 1

            logger.debug(f"Logged interaction: {agent} - {interaction['action']}")

            return {
                "success": True,
                "result": "Interaction logged successfully",
                "interaction_id": len(self.interaction_history) - 1,
            }

        except Exception as e:
            logger.error(f"Failed to log interaction: {e}")
            return {"success": False, "error": f"Logging failed: {str(e)}"}

    def _track_state(self, data: Dict) -> Dict:
        """
        Track state change (rule-based)

        Args:
            data: {
                "state": {...},
                "phase": "planning|decomposition|execution|verification",
                "timestamp": "..."
            }
        """
        try:
            timestamp = data.get("timestamp", datetime.now().isoformat())

            # Create state record
            state_record = {
                "timestamp": timestamp,
                "phase": data.get("phase", "unknown"),
                "state": data.get("state", {}),
                "state_summary": self._summarize_state(data.get("state", {})),
            }

            # Store in history
            self.state_history.append(state_record)

            self.stats["states_tracked"] += 1

            logger.debug(f"Tracked state: {state_record['phase']}")

            return {
                "success": True,
                "result": "State tracked successfully",
                "state_id": len(self.state_history) - 1,
            }

        except Exception as e:
            logger.error(f"Failed to track state: {e}")
            return {"success": False, "error": f"State tracking failed: {str(e)}"}

    async def _retrieve_context(self, data: Dict) -> Dict:
        """
        Retrieve relevant context (hybrid: rules + optional LLM)

        Args:
            data: {
                "query": "What strategies were tried?",
                "phase": "planning|decomposition|execution|verification",
                "agent": "PlanningAgent",
                "window": 10  # Number of recent items
            }
        """
        try:
            query = data.get("query", "")
            phase = data.get("phase")
            agent = data.get("agent")
            window = data.get("window", self.context_window)

            # Rule-based context retrieval
            context = self._rule_based_retrieval(phase, agent, window)

            # Determine if LLM is needed for complex reasoning
            complexity = self._assess_query_complexity(query)

            if complexity > self.use_llm_threshold and self.llm_client:
                logger.info(
                    f"Query complexity {complexity:.2f} > {self.use_llm_threshold}, using LLM"
                )
                # Use LLM for complex reasoning
                context = await self._llm_enhanced_retrieval(query, context)
                self.stats["llm_invocations"] += 1
            else:
                self.stats["rule_based_retrievals"] += 1

            self.stats["contexts_retrieved"] += 1

            return {
                "success": True,
                "result": context,
                "method": "llm"
                if complexity > self.use_llm_threshold
                else "rule_based",
                "complexity": complexity,
            }

        except Exception as e:
            logger.error(f"Context retrieval failed: {e}")
            return {"success": False, "error": f"Retrieval failed: {str(e)}"}

    def _rule_based_retrieval(
        self, phase: Optional[str], agent: Optional[str], window: int
    ) -> Dict:
        """Rule-based context retrieval (no LLM)"""

        # Get recent interactions
        recent_interactions = list(self.interaction_history)[-window:]

        # Filter by phase if specified
        if phase:
            recent_interactions = [
                i
                for i in recent_interactions
                if i.get("action", "").startswith(phase.lower())
            ]

        # Filter by agent if specified
        if agent:
            recent_interactions = [
                i for i in recent_interactions if i.get("agent") == agent
            ]

        # Get recent states
        recent_states = list(self.state_history)[-window:]
        if phase:
            recent_states = [s for s in recent_states if s.get("phase") == phase]

        # Compile context
        context = {
            "recent_interactions": recent_interactions,
            "recent_states": recent_states,
            "total_interactions": len(self.interaction_history),
            "total_states": len(self.state_history),
            "agent_activity_summary": self._get_agent_summary(),
        }

        return context

    async def _llm_enhanced_retrieval(self, query: str, base_context: Dict) -> Dict:
        """LLM-enhanced context retrieval for complex queries"""

        if not self.llm_client:
            logger.warning("LLM not available, falling back to rule-based")
            return base_context

        try:
            # Build prompt for Gemini
            system_prompt = """You are a context analysis expert for HTN planning systems.

Analyze the interaction history and state tracking data to answer complex queries about the planning process.

Provide insights about:
- Patterns in agent behavior
- Success/failure trends
- State evolution
- Strategic decisions

Respond in JSON format:
{
  "insights": ["insight1", "insight2"],
  "relevant_interactions": [0, 1, 5],  # Indices
  "relevant_states": [0, 2, 3],  # Indices
  "summary": "Brief summary of findings",
  "recommendations": ["recommendation1", "recommendation2"]
}"""

            user_prompt = f"""Query: {query}

Recent Interactions:
{self._format_interactions(base_context["recent_interactions"])}

Recent States:
{self._format_states(base_context["recent_states"])}

Analyze this data and provide insights."""

            # Generate response
            response = await asyncio.to_thread(
                self.llm_client.generate,
                user_prompt,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=800,
            )

            # Parse response - extract content from LLMResponse
            parsed = self._parse_llm_response(response.content)

            if parsed["success"]:
                # Merge LLM insights with base context
                base_context["llm_insights"] = parsed["data"]
                base_context["enhanced"] = True

            return base_context

        except Exception as e:
            logger.error(f"LLM enhancement failed: {e}")
            return base_context

    def _get_history(self, data: Dict) -> Dict:
        """Get interaction or state history"""

        history_type = data.get("type", "interaction")  # interaction|state
        limit = data.get("limit", 20)

        if history_type == "interaction":
            history = list(self.interaction_history)[-limit:]
        elif history_type == "state":
            history = list(self.state_history)[-limit:]
        else:
            return {"success": False, "error": f"Unknown history type: {history_type}"}

        return {
            "success": True,
            "result": {
                "history": history,
                "total_count": len(self.interaction_history)
                if history_type == "interaction"
                else len(self.state_history),
            },
        }

    def _summarize_data(self, data: Dict) -> str:
        """Create brief summary of data"""
        if not data:
            return "empty"

        keys = list(data.keys())[:3]
        return f"{len(data)} fields: {', '.join(keys)}"

    def _summarize_state(self, state: Dict) -> str:
        """Create brief summary of state"""
        if not state:
            return "empty"

        return f"{len(state)} state variables"

    def _assess_query_complexity(self, query: str) -> float:
        """Assess if query needs LLM (0.0-1.0)"""
        if not query:
            return 0.0

        # Simple heuristics for complexity
        complexity_keywords = [
            "why",
            "how",
            "analyze",
            "compare",
            "pattern",
            "trend",
            "insight",
            "explain",
            "recommend",
        ]

        query_lower = query.lower()
        matches = sum(1 for kw in complexity_keywords if kw in query_lower)

        # Normalize by number of words
        word_count = len(query.split())
        complexity = min(1.0, (matches / max(1, word_count)) * 3)

        return complexity

    def _get_agent_summary(self) -> Dict:
        """Get summary of agent activities"""
        summary = {}
        for agent, activities in self.agent_activities.items():
            summary[agent] = {
                "total_interactions": len(activities),
                "recent_actions": [a["action"] for a in activities[-3:]],
            }
        return summary

    def _format_interactions(self, interactions: List[Dict]) -> str:
        """Format interactions for LLM prompt"""
        lines = []
        for i, interaction in enumerate(interactions):
            lines.append(
                f"{i}. [{interaction['timestamp']}] {interaction['agent']}: "
                f"{interaction['action']} - {interaction['output_summary']}"
            )
        return "\n".join(lines) if lines else "No interactions"

    def _format_states(self, states: List[Dict]) -> str:
        """Format states for LLM prompt"""
        lines = []
        for i, state in enumerate(states):
            lines.append(
                f"{i}. [{state['timestamp']}] Phase: {state['phase']} - "
                f"{state['state_summary']}"
            )
        return "\n".join(lines) if lines else "No states"

    def _parse_llm_response(self, response: str) -> Dict:
        """Parse LLM response"""
        import json
        import re

        try:
            # Extract JSON
            json_match = re.search(
                r"```(?:json)?\s*(\{.*?\})\s*```", response, re.DOTALL
            )
            if json_match:
                response = json_match.group(1)

            data = json.loads(response)

            return {"success": True, "data": data}

        except Exception as e:
            logger.error(f"LLM response parsing failed: {e}")
            return {"success": False, "error": str(e)}

    def validate_input(self, input_data: Dict) -> bool:
        """Validate input data"""
        return "operation" in input_data

    def get_statistics(self) -> Dict:
        """Get agent statistics"""
        return {
            **self.stats,
            "llm_usage_rate": (
                self.stats["llm_invocations"] / self.stats["contexts_retrieved"]
                if self.stats["contexts_retrieved"] > 0
                else 0.0
            ),
            "history_size": len(self.interaction_history),
            "active_agents": len(self.agent_activities),
            "panda_method_library_stats": self.panda_method_library.get_statistics(),
        }
    
    # ========== PANDA Integration Methods ==========
    
    def _store_panda_method(self, data: Dict) -> Dict:
        """
        Store successful HDDL method in PANDA method library
        
        Args:
            data: {
                "domain": "graph_traversal",
                "task_name": "find_path",
                "method_name": "known_weight_method",
                "hddl_text": "(:method ...)",
                "parameters": {...},
                "preconditions": [...],
                "subtasks": [...],
                "ordering": [...]
            }
        """
        try:
            required_fields = ["domain", "task_name", "method_name", "hddl_text", 
                             "parameters", "preconditions", "subtasks", "ordering"]
            
            for field in required_fields:
                if field not in data:
                    return {
                        "success": False,
                        "error": f"Missing required field: {field}"
                    }
            
            # Store in PANDA method library
            self.panda_method_library.store_method(
                domain=data["domain"],
                task_name=data["task_name"],
                method_name=data["method_name"],
                hddl_text=data["hddl_text"],
                parameters=data["parameters"],
                preconditions=data["preconditions"],
                subtasks=data["subtasks"],
                ordering=data["ordering"]
            )
            
            self.stats["panda_methods_stored"] += 1
            
            logger.info(
                f"Stored PANDA method: {data['method_name']} "
                f"for task {data['task_name']} in domain {data['domain']}"
            )
            
            return {
                "success": True,
                "result": "PANDA method stored successfully",
                "method_name": data["method_name"]
            }
            
        except Exception as e:
            logger.error(f"Failed to store PANDA method: {e}")
            return {
                "success": False,
                "error": f"Method storage failed: {str(e)}"
            }
    
    def _retrieve_panda_method(self, data: Dict) -> Dict:
        """
        Retrieve proven HDDL method from library
        
        Args:
            data: {
                "domain": "graph_traversal",
                "task_name": "find_path",
                "context": {...}  # Optional context for matching
            }
        """
        try:
            if "domain" not in data or "task_name" not in data:
                return {
                    "success": False,
                    "error": "Missing required fields: domain and task_name"
                }
            
            domain = data["domain"]
            task_name = data["task_name"]
            context = data.get("context", None)
            
            # Retrieve from library
            method = self.panda_method_library.retrieve_method(
                domain=domain,
                task_name=task_name,
                context=context
            )
            
            if method:
                self.stats["panda_methods_retrieved"] += 1
                
                logger.info(
                    f"Retrieved PANDA method: {method.method_name} "
                    f"(success_rate={method.success_rate:.2f})"
                )
                
                return {
                    "success": True,
                    "result": {
                        "method_name": method.method_name,
                        "hddl_text": method.hddl_text,
                        "parameters": method.parameters,
                        "preconditions": method.preconditions,
                        "subtasks": method.subtasks,
                        "ordering": method.ordering,
                        "success_rate": method.success_rate,
                        "success_count": method.success_count,
                        "last_used": method.last_used
                    },
                    "method": "rule_based"
                }
            else:
                return {
                    "success": False,
                    "error": f"No method found for task {task_name} in domain {domain}",
                    "method": "rule_based"
                }
        
        except Exception as e:
            logger.error(f"Failed to retrieve PANDA method: {e}")
            return {
                "success": False,
                "error": f"Method retrieval failed: {str(e)}"
            }
    
    def _update_method_success(self, data: Dict) -> Dict:
        """
        Update success/failure statistics for a method
        
        Args:
            data: {
                "domain": "graph_traversal",
                "task_name": "find_path",
                "method_name": "known_weight_method",
                "success": true/false
            }
        """
        try:
            required_fields = ["domain", "task_name", "method_name", "success"]
            
            for field in required_fields:
                if field not in data:
                    return {
                        "success": False,
                        "error": f"Missing required field: {field}"
                    }
            
            self.panda_method_library.update_success(
                domain=data["domain"],
                task_name=data["task_name"],
                method_name=data["method_name"],
                success=data["success"]
            )
            
            logger.info(
                f"Updated method {data['method_name']} success: {data['success']}"
            )
            
            return {
                "success": True,
                "result": "Method statistics updated"
            }
            
        except Exception as e:
            logger.error(f"Failed to update method success: {e}")
            return {
                "success": False,
                "error": f"Update failed: {str(e)}"
            }
    
    def _store_panda_trace(self, data: Dict) -> Dict:
        """
        Store PANDA execution trace for later analysis
        
        Args:
            data: {
                "session_id": "...",
                "task_name": "...",
                "domain": "...",
                "plan": {...},
                "execution_time_ms": 1234.5,
                "result": "success/failure"
            }
        """
        try:
            timestamp = datetime.now().isoformat()
            
            trace = {
                "timestamp": timestamp,
                "session_id": data.get("session_id", "unknown"),
                "task_name": data.get("task_name", "unknown"),
                "domain": data.get("domain", "unknown"),
                "plan_length": data.get("plan", {}).get("plan_length", 0),
                "search_time_ms": data.get("plan", {}).get("search_time_ms", 0.0),
                "execution_time_ms": data.get("execution_time_ms", 0.0),
                "result": data.get("result", "unknown"),
                "nodes_expanded": data.get("plan", {}).get("nodes_expanded", 0)
            }
            
            # Add to state history
            self.state_history.append({
                "timestamp": timestamp,
                "phase": "panda_planning",
                "state_summary": f"PANDA planning: {trace['task_name']} - {trace['result']}",
                "trace": trace
            })
            
            self.stats["states_tracked"] += 1
            
            logger.info(
                f"Stored PANDA trace: {trace['task_name']} - {trace['result']} "
                f"(plan_length={trace['plan_length']}, time={trace['execution_time_ms']:.1f}ms)"
            )
            
            return {
                "success": True,
                "result": "PANDA trace stored successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to store PANDA trace: {e}")
            return {
                "success": False,
                "error": f"Trace storage failed: {str(e)}"
            }

