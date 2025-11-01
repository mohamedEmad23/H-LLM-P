"""
Comprehensive Benchmark Logger for HTN Planner Architectures

This module provides detailed logging and tracking for cross-architecture benchmarking.
Tracks all 7 KPIs defined in KPI_FRAMEWORK.md with timestamped measurements.

Author: H-LLM-P Project
Purpose: Thesis validation and MMS baseline benchmarking
Date: November 1, 2025
"""

import json
import time
import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field, asdict
from contextlib import contextmanager
import threading
from loguru import logger


@dataclass
class ExecutionMetrics:
    """Metrics for a single problem execution"""
    problem_id: str
    architecture: str  # 'phase1', 'phase4a', 'phase4b'
    start_timestamp: str
    end_timestamp: Optional[str] = None
    success: bool = False
    
    # KPI 1: Success Rate
    goal_achieved: bool = False
    constraint_violations: int = 0
    
    # KPI 2: Mean Time to Solution
    time_to_solution_ms: Optional[float] = None
    time_breakdown: Dict[str, float] = field(default_factory=dict)
    
    # KPI 3: Failure Recovery Rate
    failures: List[Dict[str, Any]] = field(default_factory=list)
    recovered_failures: int = 0
    total_failures: int = 0
    
    # KPI 4: Agent Communication Overhead
    messages: List[Dict[str, Any]] = field(default_factory=list)
    total_messages: int = 0
    total_payload_kb: float = 0.0
    
    # KPI 5: Plan Optimality Score
    optimal_steps: Optional[int] = None
    generated_steps: Optional[int] = None
    plan_optimality_score: Optional[float] = None
    
    # KPI 6: LLM Resource Utilization
    llm_calls: List[Dict[str, Any]] = field(default_factory=list)
    total_tokens: int = 0
    cost_estimate_usd: float = 0.0
    
    # KPI 7: Context Coherence Score
    state_consistency_score: int = 100
    goal_alignment_score: int = 100
    constraint_adherence_score: int = 100
    context_coherence_score: int = 100
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


class BenchmarkLogger:
    """
    Comprehensive logger for cross-architecture benchmarking
    
    Features:
    - Real-time KPI tracking
    - JSON + SQLite dual storage
    - Thread-safe operation
    - Automatic aggregation
    - Export utilities
    """
    
    def __init__(self, output_dir: str = "results/kpis"):
        """
        Initialize benchmark logger
        
        Args:
            output_dir: Directory for results storage
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Database setup
        self.db_path = self.output_dir / "benchmarks.db"
        self._init_database()
        
        # Thread-local storage for current execution
        self._local = threading.local()
        
        logger.info(f"BenchmarkLogger initialized: {self.output_dir}")
    
    def _init_database(self):
        """Initialize SQLite database schema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Executions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    problem_id TEXT NOT NULL,
                    architecture TEXT NOT NULL,
                    start_timestamp TEXT NOT NULL,
                    end_timestamp TEXT,
                    success BOOLEAN NOT NULL,
                    goal_achieved BOOLEAN,
                    constraint_violations INTEGER,
                    time_to_solution_ms REAL,
                    total_messages INTEGER,
                    total_tokens INTEGER,
                    plan_optimality_score REAL,
                    context_coherence_score INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # LLM calls table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS llm_calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_id INTEGER,
                    agent TEXT,
                    llm TEXT,
                    attempt TEXT,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    total_tokens INTEGER,
                    timestamp TEXT,
                    FOREIGN KEY (execution_id) REFERENCES executions(id)
                )
            """)
            
            # Messages table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_id INTEGER,
                    timestamp TEXT,
                    sender TEXT,
                    recipient TEXT,
                    message_type TEXT,
                    payload_bytes INTEGER,
                    FOREIGN KEY (execution_id) REFERENCES executions(id)
                )
            """)
            
            # Failures table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS failures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_id INTEGER,
                    component TEXT,
                    failure_type TEXT,
                    recovery_attempted BOOLEAN,
                    recovery_method TEXT,
                    recovery_successful BOOLEAN,
                    timestamp TEXT,
                    FOREIGN KEY (execution_id) REFERENCES executions(id)
                )
            """)
            
            conn.commit()
            logger.info("Database schema initialized")
    
    @contextmanager
    def track_execution(self, problem_id: str, architecture: str, 
                       optimal_steps: Optional[int] = None):
        """
        Context manager for tracking a problem execution
        
        Usage:
            with logger.track_execution('hanoi_3disk', 'phase4b', optimal_steps=7):
                result = solve_problem(...)
                logger.log_success(result)
        
        Args:
            problem_id: Unique problem identifier
            architecture: 'phase1', 'phase4a', or 'phase4b'
            optimal_steps: Theoretical minimum steps for optimality calculation
        """
        # Initialize metrics
        metrics = ExecutionMetrics(
            problem_id=problem_id,
            architecture=architecture,
            start_timestamp=datetime.now().isoformat(),
            optimal_steps=optimal_steps
        )
        self._local.metrics = metrics
        self._local.start_time = time.time()
        
        logger.info(f"[BENCHMARK] Starting: {problem_id} on {architecture}")
        
        try:
            yield metrics
        finally:
            # Finalize metrics
            metrics.end_timestamp = datetime.now().isoformat()
            metrics.time_to_solution_ms = (
                (time.time() - self._local.start_time) * 1000
            )
            
            # Calculate derived KPIs
            self._calculate_derived_kpis(metrics)
            
            # Save results
            self._save_execution(metrics)
            
            logger.info(
                f"[BENCHMARK] Completed: {problem_id} | "
                f"Success: {metrics.success} | "
                f"Time: {metrics.time_to_solution_ms:.1f}ms"
            )
    
    def log_timing(self, component: str, duration_ms: float):
        """
        Log timing for a specific component
        
        Args:
            component: Component name (e.g., 'decomposition_agent', 'llm_call')
            duration_ms: Duration in milliseconds
        """
        if hasattr(self._local, 'metrics'):
            self._local.metrics.time_breakdown[component] = duration_ms
            logger.debug(f"[TIMING] {component}: {duration_ms:.2f}ms")
    
    def log_llm_call(self, agent: str, llm: str, attempt: str,
                    input_tokens: int, output_tokens: int):
        """
        Log an LLM API call (KPI 6: LLM Resource Utilization)
        
        Args:
            agent: Agent making the call (e.g., 'decomposition_agent')
            llm: LLM identifier (e.g., 'deepseek_v3', 'groq_llama33_70b')
            attempt: 'primary' or 'fallback'
            input_tokens: Input token count
            output_tokens: Output token count
        """
        if not hasattr(self._local, 'metrics'):
            return
        
        total_tokens = input_tokens + output_tokens
        
        call_data = {
            "agent": agent,
            "llm": llm,
            "attempt": attempt,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "timestamp": datetime.now().isoformat()
        }
        
        self._local.metrics.llm_calls.append(call_data)
        self._local.metrics.total_tokens += total_tokens
        
        # Cost estimation (approximate rates)
        cost_per_1k = 0.003 if "gpt" in llm else 0.001
        self._local.metrics.cost_estimate_usd += (total_tokens / 1000) * cost_per_1k
        
        logger.debug(
            f"[LLM] {agent}/{llm} ({attempt}): "
            f"{input_tokens}+{output_tokens}={total_tokens} tokens"
        )
    
    def log_message(self, sender: str, recipient: str, 
                   message_type: str, payload_bytes: int):
        """
        Log agent communication message (KPI 4: Agent Communication Overhead)
        
        Args:
            sender: Sending agent
            recipient: Receiving agent(s)
            message_type: Type of message (task, status, context, coordination)
            payload_bytes: Message size in bytes
        """
        if not hasattr(self._local, 'metrics'):
            return
        
        message_data = {
            "timestamp": datetime.now().isoformat(),
            "sender": sender,
            "recipient": recipient,
            "type": message_type,
            "payload_bytes": payload_bytes
        }
        
        self._local.metrics.messages.append(message_data)
        self._local.metrics.total_messages += 1
        self._local.metrics.total_payload_kb += payload_bytes / 1024
        
        logger.debug(f"[MSG] {sender} → {recipient}: {message_type} ({payload_bytes}B)")
    
    def log_failure(self, component: str, failure_type: str,
                   recovery_attempted: bool = False,
                   recovery_method: Optional[str] = None,
                   recovery_successful: bool = False):
        """
        Log a component failure (KPI 3: Failure Recovery Rate)
        
        Args:
            component: Component that failed (e.g., 'decomposition_agent')
            failure_type: Type of failure (e.g., 'primary_llm_timeout')
            recovery_attempted: Whether recovery was attempted
            recovery_method: Method used for recovery (e.g., 'fallback_llm_groq')
            recovery_successful: Whether recovery succeeded
        """
        if not hasattr(self._local, 'metrics'):
            return
        
        failure_data = {
            "component": component,
            "failure_type": failure_type,
            "recovery_attempted": recovery_attempted,
            "recovery_method": recovery_method,
            "recovery_successful": recovery_successful,
            "timestamp": datetime.now().isoformat()
        }
        
        self._local.metrics.failures.append(failure_data)
        self._local.metrics.total_failures += 1
        
        if recovery_successful:
            self._local.metrics.recovered_failures += 1
        
        logger.warning(
            f"[FAILURE] {component}: {failure_type} | "
            f"Recovery: {recovery_method if recovery_attempted else 'None'} | "
            f"Success: {recovery_successful}"
        )
    
    def log_success(self, goal_achieved: bool = True,
                   constraint_violations: int = 0,
                   generated_steps: Optional[int] = None):
        """
        Log successful completion (KPI 1: Success Rate, KPI 5: Plan Optimality)
        
        Args:
            goal_achieved: Whether goal state was achieved
            constraint_violations: Number of constraint violations
            generated_steps: Number of steps in generated plan
        """
        if not hasattr(self._local, 'metrics'):
            return
        
        metrics = self._local.metrics
        metrics.success = goal_achieved and constraint_violations == 0
        metrics.goal_achieved = goal_achieved
        metrics.constraint_violations = constraint_violations
        metrics.generated_steps = generated_steps
        
        logger.info(
            f"[SUCCESS] Goal: {goal_achieved} | "
            f"Violations: {constraint_violations} | "
            f"Steps: {generated_steps}"
        )
    
    def log_context_coherence(self, state_contradictions: int = 0,
                             relevant_actions: int = 0,
                             total_actions: int = 0,
                             soft_violations: int = 0,
                             hard_violations: int = 0):
        """
        Log context coherence metrics (KPI 7: Context Coherence Score)
        
        Args:
            state_contradictions: Number of contradictory state assertions
            relevant_actions: Actions moving toward goal
            total_actions: Total actions taken
            soft_violations: Soft constraint violations
            hard_violations: Hard constraint violations
        """
        if not hasattr(self._local, 'metrics'):
            return
        
        metrics = self._local.metrics
        
        # State consistency (40%)
        state_score = max(0, 100 - (10 * state_contradictions))
        metrics.state_consistency_score = state_score
        
        # Goal alignment (30%)
        goal_score = (relevant_actions / max(total_actions, 1)) * 100
        metrics.goal_alignment_score = int(goal_score)
        
        # Constraint adherence (30%)
        constraint_score = max(0, 100 - (5 * soft_violations) - (20 * hard_violations))
        metrics.constraint_adherence_score = constraint_score
        
        # Weighted average
        ccs = (0.4 * state_score) + (0.3 * goal_score) + (0.3 * constraint_score)
        metrics.context_coherence_score = int(ccs)
        
        logger.debug(
            f"[COHERENCE] State: {state_score} | "
            f"Goal: {goal_score:.0f} | "
            f"Constraint: {constraint_score} | "
            f"CCS: {ccs:.0f}"
        )
    
    def _calculate_derived_kpis(self, metrics: ExecutionMetrics):
        """Calculate derived KPI values"""
        
        # KPI 5: Plan Optimality Score
        if metrics.optimal_steps and metrics.generated_steps:
            pos = (metrics.optimal_steps / metrics.generated_steps) * 100
            metrics.plan_optimality_score = min(100.0, pos)
        
        logger.debug(f"[KPIs] Derived metrics calculated")
    
    def _save_execution(self, metrics: ExecutionMetrics):
        """Save execution metrics to database and JSON"""
        
        # Save to database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Insert execution
            cursor.execute("""
                INSERT INTO executions (
                    problem_id, architecture, start_timestamp, end_timestamp,
                    success, goal_achieved, constraint_violations,
                    time_to_solution_ms, total_messages, total_tokens,
                    plan_optimality_score, context_coherence_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metrics.problem_id, metrics.architecture,
                metrics.start_timestamp, metrics.end_timestamp,
                metrics.success, metrics.goal_achieved,
                metrics.constraint_violations, metrics.time_to_solution_ms,
                metrics.total_messages, metrics.total_tokens,
                metrics.plan_optimality_score, metrics.context_coherence_score
            ))
            
            execution_id = cursor.lastrowid
            
            # Insert LLM calls
            for call in metrics.llm_calls:
                cursor.execute("""
                    INSERT INTO llm_calls (
                        execution_id, agent, llm, attempt,
                        input_tokens, output_tokens, total_tokens, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    execution_id, call['agent'], call['llm'], call['attempt'],
                    call['input_tokens'], call['output_tokens'],
                    call['total_tokens'], call['timestamp']
                ))
            
            # Insert messages
            for msg in metrics.messages:
                cursor.execute("""
                    INSERT INTO messages (
                        execution_id, timestamp, sender, recipient,
                        message_type, payload_bytes
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    execution_id, msg['timestamp'], msg['sender'],
                    msg['recipient'], msg['type'], msg['payload_bytes']
                ))
            
            # Insert failures
            for failure in metrics.failures:
                cursor.execute("""
                    INSERT INTO failures (
                        execution_id, component, failure_type,
                        recovery_attempted, recovery_method, recovery_successful,
                        timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    execution_id, failure['component'], failure['failure_type'],
                    failure['recovery_attempted'], failure['recovery_method'],
                    failure['recovery_successful'], failure['timestamp']
                ))
            
            conn.commit()
        
        # Save JSON file
        arch_dir = self.output_dir / metrics.architecture / metrics.problem_id
        arch_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = arch_dir / f"run_{timestamp}.json"
        
        with open(json_path, 'w') as f:
            json.dump(asdict(metrics), f, indent=2)
        
        logger.info(f"[SAVED] {json_path}")
    
    def export_comparative_analysis(self, output_file: str = "comparative_analysis.json"):
        """
        Export aggregated KPIs for cross-architecture comparison
        
        Args:
            output_file: Output filename (in output_dir)
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Aggregate by architecture
            cursor.execute("""
                SELECT 
                    architecture,
                    COUNT(*) as total_runs,
                    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful_runs,
                    AVG(time_to_solution_ms) as avg_time_ms,
                    AVG(total_messages) as avg_messages,
                    AVG(total_tokens) as avg_tokens,
                    AVG(plan_optimality_score) as avg_optimality,
                    AVG(context_coherence_score) as avg_coherence
                FROM executions
                GROUP BY architecture
            """)
            
            architectures = {}
            for row in cursor.fetchall():
                arch, total, success, time_ms, msgs, tokens, opt, coh = row
                
                # Calculate FRR
                cursor.execute("""
                    SELECT 
                        COUNT(CASE WHEN recovery_successful THEN 1 END) as recovered,
                        COUNT(*) as total
                    FROM failures
                    WHERE execution_id IN (
                        SELECT id FROM executions WHERE architecture = ?
                    )
                """, (arch,))
                recovered, total_failures = cursor.fetchone()
                frr = (recovered / max(total_failures, 1)) * 100
                
                architectures[arch] = {
                    "total_runs": total,
                    "success_rate": (success / max(total, 1)) * 100,
                    "mean_time_to_solution_ms": time_ms,
                    "failure_recovery_rate": frr,
                    "avg_agent_communication": msgs or 0,
                    "avg_plan_optimality": opt,
                    "avg_llm_tokens": tokens,
                    "avg_context_coherence": coh
                }
            
            output_path = self.output_dir / output_file
            with open(output_path, 'w') as f:
                json.dump(architectures, f, indent=2)
            
            logger.success(f"[EXPORTED] Comparative analysis: {output_path}")
            return architectures


# Global singleton instance
_benchmark_logger: Optional[BenchmarkLogger] = None


def get_benchmark_logger(output_dir: str = "results/kpis") -> BenchmarkLogger:
    """Get or create global benchmark logger instance"""
    global _benchmark_logger
    if _benchmark_logger is None:
        _benchmark_logger = BenchmarkLogger(output_dir)
    return _benchmark_logger
