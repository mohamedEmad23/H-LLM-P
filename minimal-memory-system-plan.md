# FAISS Similarity Search for HTN Problem Reuse

## Objective

Add similarity-based problem matching to complement the existing exact-match `ProblemCache`. When a new problem doesn't match exactly, find similar solved problems and reuse their planning strategies.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   PANDAWorkflow                         │
│                                                         │
│  1. Check ProblemCache (exact match) ─────┐            │
│                                            │            │
│  2. If miss → Check SimilaritySearch ──────┤            │
│                                            │            │
│  3. If similar found → Reuse strategies ───┘            │
│                                                         │
│  4. After success → Store in both caches               │
└─────────────────────────────────────────────────────────┘
                         │
         ┌───────────────┴───────────────┐
         ▼                               ▼
┌─────────────────────┐      ┌─────────────────────┐
│   ProblemCache      │      │  SimilaritySearch   │
│   (Existing)        │      │  (NEW)              │
│                     │      │                     │
│  • Exact hash match │      │  • FAISS index      │
│  • Full solution    │      │  • Embeddings       │
│    reuse            │      │  • Strategy hints   │
└─────────────────────┘      └─────────────────────┘
```

## Files to Create/Modify

### New Files

| File | Purpose |

|------|---------|

| `src/memory/similarity_search.py` | FAISS index + embedding logic |

| `src/memory/__init__.py` | Module exports |

### Existing Files to Modify

| File | Changes |

|------|---------|

| `src/integrations/problem_cache.py` | Add similarity search integration |

| `src/agents/workflows/panda_workflow.py` | Use similarity hints in Phase 1 |

| `requirements.txt` | Add sentence-transformers, faiss-cpu |

## Implementation Details

### 1. SimilaritySearch Class (`src/memory/similarity_search.py`)

```python
class SimilaritySearch:
    """FAISS-based similarity search for HTN problems"""
    
    def __init__(self, 
                 model_name: str = "all-MiniLM-L6-v2",
                 index_path: str = "./results/panda-results/similarity_index"):
        self.model = SentenceTransformer(model_name)
        self.dimension = 384  # MiniLM embedding size
        self.index = faiss.IndexFlatIP(self.dimension)
        self.metadata = []  # Parallel array with problem info
        
    def embed_problem(self, domain: str, init_state: str, 
                      goal: str) -> np.ndarray:
        """Create embedding from problem components"""
        text = f"Domain: {domain}\nState: {init_state}\nGoal: {goal}"
        return self.model.encode(text, normalize_embeddings=True)
    
    def add_solved_problem(self, problem_id: str, domain: str,
                           init_state: str, goal: str,
                           strategies: List[Dict], 
                           plan_length: int):
        """Store solved problem for future similarity matching"""
        
    def find_similar(self, domain: str, init_state: str, goal: str,
                     top_k: int = 3, 
                     threshold: float = 0.75) -> List[SimilarProblem]:
        """Find similar solved problems above threshold"""
        
    def save(self) / def load(self):
        """Persist/restore index and metadata"""
```

### 2. Integration with ProblemCache

```python
# In problem_cache.py - Add method:
def check_similar(self, domain: str, initial_state: Dict, 
                  goal_description: str) -> Optional[List[SimilarProblem]]:
    """Check for similar (not exact) problems"""
    if self.similarity_search is None:
        return None
    return self.similarity_search.find_similar(
        domain=domain,
        init_state=json.dumps(initial_state),
        goal=goal_description
    )
```

### 3. Integration with PANDAWorkflow

```python
# In panda_workflow.py - Modify Phase 1:
async def _phase1_planning(self, ...):
    # Check for similar problems if exact cache miss
    similar = self.problem_cache.check_similar(domain, state, goal)
    
    if similar:
        logger.info(f"Found {len(similar)} similar problems")
        # Pass strategy hints to PlanningAgent
        planning_input["strategy_hints"] = [
            s.strategies for s in similar[:2]
        ]
    
    result = await self.planning_agent.process(planning_input)
```

## Data Flow

```
New Problem Arrives
        │
        ▼
┌───────────────────┐
│ 1. Exact Match?   │──── YES ──→ Return cached solution
│    (ProblemCache) │
└───────────────────┘
        │ NO
        ▼
┌───────────────────┐
│ 2. Similar Match? │──── YES ──→ Return strategy hints
│    (Similarity)   │            (still run planning, but guided)
└───────────────────┘
        │ NO
        ▼
┌───────────────────┐
│ 3. Full Planning  │ ← No hints, plan from scratch
│    (Cold start)   │
└───────────────────┘
        │
        ▼ (On success)
┌───────────────────┐
│ 4. Store in Both  │
│    Caches         │
└───────────────────┘
```

## SimilarProblem Data Structure

```python
@dataclass
class SimilarProblem:
    problem_id: str
    domain: str
    similarity_score: float  # 0.0 - 1.0
    strategies: List[Dict]   # From PlanningAgent Phase 1
    plan_length: int
    success_rate: float      # Historical success with this strategy
```

## Dependencies

Add to `requirements.txt`:

```
sentence-transformers>=2.2.0  # ~90MB model download
faiss-cpu>=1.7.0              # Vector search (CPU version)
```

## Testing Strategy

### Unit Tests

- `test_similarity_search.py`: Embedding, indexing, retrieval

### Integration Tests

1. Create problem variants:

   - `incomplete-graph-p01.hddl` (baseline)
   - `incomplete-graph-p02.hddl` (different unknown edge)
   - `incomplete-graph-p03.hddl` (5 nodes instead of 4)

2. Test similarity matching:

   - Solve p01, store in index
   - Query with p02 → should find p01 as similar
   - Query with p03 → should find p01 with lower similarity

3. Test strategy reuse:

   - Measure planning time WITH strategy hints vs WITHOUT
   - Compare LLM calls count

## Success Metrics

| Metric | Target |

|--------|--------|

| Similarity threshold | 0.75 (tunable) |

| Query latency | <100ms |

| Model loading | <3s (one-time) |

| Index size | <10MB for 1000 problems |

| Strategy reuse benefit | >20% fewer LLM tokens |

## Research Contribution

**Thesis section**: "Similarity-Based Strategy Transfer in Neuro-Symbolic HTN Planning"

**Experiment design**:

1. Create 20 problem variants across 2 domains
2. Baseline: Solve each problem independently (no similarity)
3. With similarity: Solve with strategy hints from similar problems
4. Measure: Time, LLM calls, plan quality, success rate

**Expected findings**:

- Similar problems benefit from strategy reuse
- Diminishing returns as similarity drops below threshold
- Domain-specific vs cross-domain transfer analysis

---
---

