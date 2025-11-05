"""
Agent State Manager

Manages world state for the multi-agent system.
Extends the core StateManager with agent-specific functionality.

Author: H-LLM-P Project
Phase: 4A - Multi-Agent Core
"""

import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from copy import deepcopy
from loguru import logger

# Import core state manager
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from core.state_manager import State


@dataclass
class SessionState:
    """
    Session state tracking for multi-agent planning.

    Attributes:
        session_id: Unique session identifier
        initial_state: The starting world state
        current_state: The current world state
        goal_state: The desired goal state
        state_history: History of state transitions
        plan_trace: Execution trace of the current plan
        metadata: Additional session information
    """

    session_id: str
    initial_state: State
    current_state: State
    goal_state: State
    state_history: List[Dict[str, Any]] = field(default_factory=list)
    plan_trace: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def add_state_transition(self, operator: str, old_state: State, new_state: State):
        """
        Record a state transition.

        Args:
            operator: The operator that caused the transition
            old_state: State before transition
            new_state: State after transition
        """
        self.state_history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "operator": operator,
                "old_state": list(old_state.predicates),
                "new_state": list(new_state.predicates),
                "changes": {
                    "added": list(new_state.predicates - old_state.predicates),
                    "removed": list(old_state.predicates - new_state.predicates),
                },
            }
        )
        self.current_state = deepcopy(new_state)
        self.updated_at = datetime.now()

    def add_plan_step(self, step: Dict[str, Any]):
        """
        Add a step to the plan trace.

        Args:
            step: Plan step information
        """
        self.plan_trace.append({**step, "timestamp": datetime.now().isoformat()})
        self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert session state to dictionary"""
        return {
            "session_id": self.session_id,
            "initial_state": list(self.initial_state.predicates),
            "current_state": list(self.current_state.predicates),
            "goal_state": list(self.goal_state.predicates),
            "state_history": self.state_history,
            "plan_trace": self.plan_trace,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class AgentStateManager:
    """
    Manages state for the multi-agent HTN planning system.

    Responsibilities:
    - Track current world state
    - Monitor goal progress
    - Detect state changes
    - Provide context to agents
    - Manage session persistence
    """

    def __init__(self):
        """Initialize the agent state manager"""
        self.sessions: Dict[str, SessionState] = {}
        self.active_session: Optional[str] = None
        logger.info("AgentStateManager initialized")

    def create_session(
        self,
        session_id: str,
        initial_state: State,
        goal_state: State,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SessionState:
        """
        Create a new planning session.

        Args:
            session_id: Unique session identifier
            initial_state: Starting world state
            goal_state: Desired goal state
            metadata: Optional session metadata

        Returns:
            Created session state
        """
        session = SessionState(
            session_id=session_id,
            initial_state=deepcopy(initial_state),
            current_state=deepcopy(initial_state),
            goal_state=deepcopy(goal_state),
            metadata=metadata or {},
        )

        self.sessions[session_id] = session
        self.active_session = session_id

        logger.success(f"Created session: {session_id}")
        return session

    def get_session(self, session_id: str) -> Optional[SessionState]:
        """
        Get a session by ID.

        Args:
            session_id: Session identifier

        Returns:
            Session state or None if not found
        """
        return self.sessions.get(session_id)

    def get_active_session(self) -> Optional[SessionState]:
        """Get the currently active session"""
        if self.active_session:
            return self.sessions.get(self.active_session)
        return None

    def set_active_session(self, session_id: str):
        """
        Set the active session.

        Args:
            session_id: Session to activate

        Raises:
            ValueError: If session not found
        """
        if session_id not in self.sessions:
            raise ValueError(f"Session not found: {session_id}")

        self.active_session = session_id
        logger.info(f"Active session set to: {session_id}")

    def update_state(self, session_id: str, operator: str, new_state: State):
        """
        Update the state for a session.

        Args:
            session_id: Session to update
            operator: Operator that caused the change
            new_state: New world state
        """
        session = self.get_session(session_id)
        if not session:
            logger.error(f"Session not found: {session_id}")
            return

        old_state = session.current_state
        session.add_state_transition(operator, old_state, new_state)

        logger.debug(f"Updated state for session {session_id} via operator: {operator}")

    def get_current_state(self, session_id: Optional[str] = None) -> Optional[State]:
        """
        Get current state for a session.

        Args:
            session_id: Session ID (uses active session if None)

        Returns:
            Current state or None
        """
        if session_id is None:
            session_id = self.active_session

        session = self.get_session(session_id)
        return session.current_state if session else None

    def get_goal_state(self, session_id: Optional[str] = None) -> Optional[State]:
        """
        Get goal state for a session.

        Args:
            session_id: Session ID (uses active session if None)

        Returns:
            Goal state or None
        """
        if session_id is None:
            session_id = self.active_session

        session = self.get_session(session_id)
        return session.goal_state if session else None

    def check_goal_achieved(self, session_id: Optional[str] = None) -> bool:
        """
        Check if goal is achieved in a session.

        Args:
            session_id: Session ID (uses active session if None)

        Returns:
            True if goal achieved, False otherwise
        """
        if session_id is None:
            session_id = self.active_session

        session = self.get_session(session_id)
        if not session:
            return False

        # Goal is achieved if all goal predicates are in current state
        return session.goal_state.predicates.issubset(session.current_state.predicates)

    def get_progress(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get progress statistics for a session.

        Args:
            session_id: Session ID (uses active session if None)

        Returns:
            Progress statistics
        """
        if session_id is None:
            session_id = self.active_session

        session = self.get_session(session_id)
        if not session:
            return {}

        goal_predicates = session.goal_state.predicates
        current_predicates = session.current_state.predicates

        achieved = goal_predicates & current_predicates
        remaining = goal_predicates - current_predicates

        return {
            "session_id": session_id,
            "goal_predicates_total": len(goal_predicates),
            "goal_predicates_achieved": len(achieved),
            "goal_predicates_remaining": len(remaining),
            "progress_percentage": len(achieved) / len(goal_predicates) * 100
            if goal_predicates
            else 100,
            "achieved": list(achieved),
            "remaining": list(remaining),
            "state_transitions": len(session.state_history),
            "plan_steps": len(session.plan_trace),
        }

    def add_plan_step(self, session_id: str, step_info: Dict[str, Any]):
        """
        Add a plan step to session trace.

        Args:
            session_id: Session ID
            step_info: Information about the plan step
        """
        session = self.get_session(session_id)
        if session:
            session.add_plan_step(step_info)

    def get_context(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get complete context for a session.

        Args:
            session_id: Session ID (uses active session if None)

        Returns:
            Complete session context
        """
        if session_id is None:
            session_id = self.active_session

        session = self.get_session(session_id)
        if not session:
            return {}

        return {
            "session_id": session_id,
            "initial_state": list(session.initial_state.predicates),
            "current_state": list(session.current_state.predicates),
            "goal_state": list(session.goal_state.predicates),
            "progress": self.get_progress(session_id),
            "recent_transitions": session.state_history[-5:]
            if session.state_history
            else [],
            "metadata": session.metadata,
        }

    def save_session(self, session_id: str, filepath: str):
        """
        Save session to file.

        Args:
            session_id: Session to save
            filepath: Path to save to
        """
        session = self.get_session(session_id)
        if not session:
            logger.error(f"Session not found: {session_id}")
            return

        with open(filepath, "w") as f:
            json.dump(session.to_dict(), f, indent=2)

        logger.success(f"Session {session_id} saved to {filepath}")

    def load_session(self, filepath: str) -> Optional[SessionState]:
        """
        Load session from file.

        Args:
            filepath: Path to load from

        Returns:
            Loaded session state
        """
        try:
            with open(filepath, "r") as f:
                data = json.load(f)

            session = SessionState(
                session_id=data["session_id"],
                initial_state=State(predicates=set(data["initial_state"])),
                current_state=State(predicates=set(data["current_state"])),
                goal_state=State(predicates=set(data["goal_state"])),
                state_history=data.get("state_history", []),
                plan_trace=data.get("plan_trace", []),
                metadata=data.get("metadata", {}),
                created_at=datetime.fromisoformat(data["created_at"]),
                updated_at=datetime.fromisoformat(data["updated_at"]),
            )

            self.sessions[session.session_id] = session
            logger.success(f"Session {session.session_id} loaded from {filepath}")
            return session

        except Exception as e:
            logger.error(f"Failed to load session from {filepath}: {e}")
            return None

    def clear_sessions(self):
        """Clear all sessions"""
        self.sessions.clear()
        self.active_session = None
        logger.info("All sessions cleared")
