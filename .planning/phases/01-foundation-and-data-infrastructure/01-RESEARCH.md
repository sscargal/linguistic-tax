# Phase 1: Foundation and Data Infrastructure - Research

**Researched:** 2026-03-19
**Domain:** Python data infrastructure, noise generation, benchmark curation, SQLite schema design
**Confidence:** HIGH

## Summary

Phase 1 delivers the complete deterministic data foundation for the Linguistic Tax study: a configuration module, SQLite schema, noise generators (Type A character-level and Type B ESL syntactic), 200 curated benchmark prompts, and the materialized experiment matrix. No API calls are made in this phase -- everything is testable offline.

The technical domain is straightforward Python programming with no exotic dependencies. The key challenges are: (1) correctly implementing deterministic noise generation with isolated random instances, (2) designing linguistically accurate ESL patterns based on L1 transfer research, (3) correctly computing the experiment matrix dimensions (200 prompts x 8 noise conditions x 5 interventions x 2 models x 5 repetitions + baselines + compression), and (4) sourcing benchmark prompts from HumanEval (164 problems), MBPP (974 problems), and GSM8K (~1300 problems) via Hugging Face datasets.

**Primary recommendation:** Use the `datasets` library from Hugging Face to source all three benchmarks programmatically. Build the noise generator as a pure-function module with `random.Random(seed)` instances per mutation context. Use a flat SQLite schema matching the RDD Section 9.2 log entry format. Materialize the full experiment matrix eagerly as JSON.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Equal split across HumanEval, MBPP, and GSM8K (~67 prompts each) for balanced representation across code generation and math reasoning
- No difficulty filtering -- random sample from each benchmark to avoid selection bias
- Store prompts in `data/prompts.json` with canonical answers for grading validation
- Each prompt record includes: benchmark_source, problem_id, prompt_text, canonical_answer, answer_type (code/numeric)
- Protected tokens: function names, variable names, operators, and language keywords in code prompts; mathematical operators and numbers in GSM8K prompts
- Protection mechanism: regex-based token identification before mutation pass, identified tokens are skipped during noise injection
- Protection applies to Type A (character-level) noise only -- Type B (ESL) operates on syntactic structure, not character-level
- 5-8 patterns per L1 source language (Mandarin, Spanish, Japanese), covering: article/preposition errors, word order deviations, tense errors, pluralization errors
- Mixed ESL mode combines patterns from multiple L1 sources
- Apply uniformly -- one ESL transformation pass per prompt (consistent treatment for analysis)
- Patterns should be rule-based templates, not random -- each pattern is a deterministic transformation
- Each work item is a self-contained JSON object: prompt_id, noise_type, noise_level, intervention, model, repetition_num, status
- Eager generation -- materialize full matrix as `data/experiment_matrix.json` before any execution
- Matrix enables: progress tracking, cost estimation, and resumability before API calls begin
- Include clean (no-noise) baseline conditions in the matrix as explicit rows
- Independent `random.Random(seed)` instances per noise source -- no global `random.seed()` calls
- Seed registry in config module maps each randomness source to its seed value
- Seeds are deterministic functions of (base_seed, prompt_id, noise_type, noise_level) for reproducibility
- Noise generators must be CLI-invocable (e.g., `python src/noise_generator.py --input data/prompts.json --type char --rate 0.10 --seed 42`)

### Claude's Discretion
- Exact SQLite schema column names and types (must match RDD Section 9.2 intent but implementation details are flexible)
- Config module implementation pattern (dataclass, dict, or module-level constants)
- JSON file structure details beyond the specified fields
- Test fixture organization

### Deferred Ideas (OUT OF SCOPE)
- None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DATA-01 | Curate 200 clean benchmark prompts from HumanEval, MBPP, and GSM8K with canonical problem definitions | Benchmark sourcing via `datasets` library; prompt record schema defined |
| DATA-02 | Build experiment matrix covering all prompt x noise x intervention combinations as self-contained work items | Matrix dimensions computed from RDD; eager materialization pattern |
| DATA-03 | Store all experimental results in SQLite with schema matching RDD Section 9.2 | SQLite schema design from RDD log entry format |
| DATA-04 | Implement configuration module with pinned model versions, API settings, and seed registry | Config module pattern; seed derivation function |
| NOISE-01 | Generate Type A character-level noise at 5%, 10%, and 20% error rates with fixed random seeds | Mutation engine with weighted operations (40/25/20/15 split) |
| NOISE-02 | Protect technical keywords (function names, variable names, operators) from character mutation | Regex-based token protection before mutation pass |
| NOISE-03 | Generate Type B ESL syntactic noise patterns based on L1 transfer errors (Mandarin, Spanish, Japanese, mixed) | L1 transfer error patterns from SLA research |
| NOISE-04 | Verify noise generator determinism -- same seed produces identical output across runs | Determinism tests with isolated Random instances |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.11+ (3.13.3 available on system) | Runtime | Project requirement per CLAUDE.md |
| sqlite3 | stdlib | Results database | Built-in, no external dependency; project mandates SQLite |
| datasets | 3.x (Hugging Face) | Load HumanEval, MBPP, GSM8K benchmarks | Standard way to access ML benchmarks programmatically |
| pytest | 8.0+ (in pyproject.toml) | Testing | Already configured in pyproject.toml |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| json | stdlib | Prompt and matrix serialization | All JSON read/write |
| re | stdlib | Keyword protection regex | Type A noise token identification |
| hashlib | stdlib | Seed derivation | Deterministic seed = hash(base_seed, prompt_id, noise_type, level) |
| argparse | stdlib | CLI interface for noise generators | CLI-invocable per project spec |
| logging | stdlib | All output (NOT print) | CLAUDE.md mandates logging module |
| uuid | stdlib | Run ID generation | Unique identifiers for experiment runs |
| pathlib | stdlib | File path handling | Modern Python path operations |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `datasets` (HF) | Direct JSON download from GitHub repos | `datasets` handles caching, splits, and schema; direct download requires manual parsing |
| `hashlib` for seed derivation | Simple arithmetic on seed + prompt_id | hashlib provides uniform distribution and collision resistance |
| `dataclass` for config | Dict or module constants | Dataclass gives type checking and IDE support; recommended |

**Installation:**
```bash
uv add datasets
```

Note: `datasets` is a dev/build-time dependency for prompt curation only. It is NOT needed at experiment runtime. Consider adding it as an optional dependency or using it in a one-time curation script that writes `data/prompts.json`.

## Architecture Patterns

### Recommended Project Structure
```
src/
    __init__.py
    config.py              # Pinned models, seeds, paths, constants
    noise_generator.py     # Type A + Type B noise injection (CLI-invocable)
    db.py                  # SQLite schema creation and helper functions
data/
    prompts.json           # 200 curated benchmark prompts
    experiment_matrix.json # Materialized full matrix (~20K work items)
tests/
    __init__.py
    test_config.py
    test_noise_generator.py
    test_db.py
    test_prompts.py        # Validate prompt curation
    test_matrix.py         # Validate matrix generation
    conftest.py            # Shared fixtures
scripts/
    curate_prompts.py      # One-time script to download and curate from HF
    generate_matrix.py     # One-time script to materialize experiment matrix
```

### Pattern 1: Isolated Random Instances for Determinism
**What:** Each noise generation call creates its own `random.Random(derived_seed)` instance rather than using global `random.seed()`.
**When to use:** Every noise injection operation.
**Example:**
```python
import hashlib
import random

def derive_seed(base_seed: int, prompt_id: str, noise_type: str, noise_level: str) -> int:
    """Derive a deterministic seed from experimental parameters."""
    key = f"{base_seed}:{prompt_id}:{noise_type}:{noise_level}"
    return int(hashlib.sha256(key.encode()).hexdigest()[:8], 16)

def inject_type_a_noise(text: str, error_rate: float, seed: int) -> str:
    """Inject character-level noise at the given rate using a local RNG."""
    rng = random.Random(seed)
    # ... mutation logic using rng, not random module globals
```

### Pattern 2: QWERTY Adjacent Key Map for Type A Noise
**What:** A static dictionary mapping each character to its physically adjacent keys on a QWERTY keyboard.
**When to use:** The "adjacent key swap" mutation (40% weight per RDD).
**Example:**
```python
# QWERTY layout as 2D grid for computing adjacency
QWERTY_ROWS = [
    list("qwertyuiop"),
    list("asdfghjkl"),
    list("zxcvbnm"),
]

def build_adjacency_map() -> dict[str, list[str]]:
    """Build mapping from each key to its physical neighbors."""
    # For each key, find neighbors in the 2D grid (up, down, left, right, diagonals)
    adj: dict[str, list[str]] = {}
    # ... grid traversal logic
    return adj
```

### Pattern 3: Rule-Based ESL Templates for Type B Noise
**What:** Deterministic transformation rules organized by L1 source language. Each rule is a regex pattern + replacement.
**When to use:** Type B syntactic noise generation.
**Example:**
```python
from dataclasses import dataclass

@dataclass
class ESLPattern:
    name: str
    l1_source: str  # "mandarin", "spanish", "japanese"
    description: str
    pattern: str     # regex
    replacement: str

MANDARIN_PATTERNS = [
    ESLPattern(
        name="article_omission",
        l1_source="mandarin",
        description="Drop articles (a, an, the) - Mandarin has no article system",
        pattern=r"\b(a|an|the)\s+",
        replacement="",
    ),
    # ... 4-7 more patterns
]
```

### Pattern 4: Config as Frozen Dataclass
**What:** Central configuration module using frozen dataclasses for immutability.
**When to use:** All modules import config for seeds, model versions, paths.
**Example:**
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class ExperimentConfig:
    # Model versions (pinned)
    claude_model: str = "claude-sonnet-4-20250514"
    gemini_model: str = "gemini-1.5-pro"

    # Seeds
    base_seed: int = 42

    # Noise parameters
    type_a_rates: tuple[float, ...] = (0.05, 0.10, 0.20)
    type_a_weights: tuple[float, ...] = (0.40, 0.25, 0.20, 0.15)  # adj_swap, omission, doubling, transposition

    # Paths
    prompts_path: str = "data/prompts.json"
    matrix_path: str = "data/experiment_matrix.json"
    results_db_path: str = "results/results.db"

    # Experiment parameters
    repetitions: int = 5
    temperature: float = 0.0
```

### Anti-Patterns to Avoid
- **Global random.seed():** Causes cross-contamination between noise sources. Always use `random.Random(seed)` instances.
- **print() for logging:** CLAUDE.md explicitly forbids this. Use `logging` module.
- **Flat JSON for results:** CLAUDE.md mandates SQLite. JSON is only for prompts and matrix.
- **Hardcoded API keys:** Use environment variables via `os.environ`.
- **Modifying original benchmark prompts:** Only inject noise into copies. Store originals immutably in `data/prompts.json`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Benchmark prompt sourcing | Manual copy-paste from GitHub repos | `datasets` library (HuggingFace) | Handles versioning, caching, canonical splits; HumanEval has 164, MBPP has 974, GSM8K has ~8.5K |
| QWERTY adjacency computation | Hardcoded neighbor dict | 2D grid array + geometric neighbor lookup | Grid approach is extensible, verifiable, and handles edge keys correctly |
| UUID generation | Custom ID scheme | `uuid.uuid4()` | Standard, collision-free |
| SQLite migrations | Manual ALTER TABLE | Schema version table + migration on startup | Future phases may need schema changes |

**Key insight:** This phase has no exotic dependencies. The stdlib covers nearly everything. The only external library needed is `datasets` for one-time benchmark curation.

## Common Pitfalls

### Pitfall 1: Non-Deterministic Noise Generation
**What goes wrong:** Different runs produce different noisy prompts, invalidating reproducibility.
**Why it happens:** Using `random.seed()` globally, or not accounting for iteration order when processing prompts.
**How to avoid:** Each noise generation call derives its seed from `(base_seed, prompt_id, noise_type, noise_level)`. Use `random.Random(derived_seed)` instances. Process prompts in sorted order by prompt_id.
**Warning signs:** Tests comparing two runs of the same seed producing different output.

### Pitfall 2: Mutating Protected Tokens in Code Prompts
**What goes wrong:** Noise injection corrupts function names, keywords, or operators, making prompts syntactically invalid rather than just "noisy."
**Why it happens:** Applying character mutations uniformly across all tokens without protection.
**How to avoid:** Before mutation, identify protected tokens via regex (Python keywords, function/variable names in code, numbers/operators in math). Skip these during the mutation pass. Protection applies to Type A only.
**Warning signs:** Noisy code prompts that fail to parse at all, rather than containing "human typos."

### Pitfall 3: Wrong Experiment Matrix Dimensions
**What goes wrong:** Matrix has wrong number of rows, missing conditions, or duplicates.
**Why it happens:** Miscounting the noise conditions. Type A has 3 levels (5/10/20%), Type B has 4 L1 sources (Mandarin, Spanish, Japanese, Mixed). Plus clean baseline. Combined with 5 interventions and 2 models and 5 repetitions.
**How to avoid:** Enumerate explicitly:
- Noise conditions: Clean (1) + Type A at 3 levels (3) + Type B at 4 L1 sources (4) = 8 noise conditions
- Interventions: Raw, Self-Correct, Pre-Proc Sanitize, Pre-Proc Sanitize+Compress, Prompt Repetition = 5
- Models: 2 (Claude Sonnet, Gemini 1.5 Pro)
- Repetitions: 5
- Total per-prompt: 8 noise x 5 interventions x 2 models x 5 reps = 400 (but clean baselines don't need all interventions -- see RDD)
- Compression study: separate (200 prompts x 2 models x 5 reps = 2000)
**Warning signs:** Total work items not matching ~20,000 from RDD Section 4.3.

### Pitfall 4: ESL Patterns That Are Linguistically Inaccurate
**What goes wrong:** Patterns don't reflect actual L1 transfer errors, undermining the paper's claims about ESL users.
**Why it happens:** Guessing at error patterns rather than basing them on second-language acquisition (SLA) research.
**How to avoid:** Base each pattern on documented L1 transfer phenomena:
- Mandarin: article omission (no article system), topic-comment structure, aspect marker confusion
- Spanish: preposition confusion ("depend of" not "depend on"), double negatives, adjective placement
- Japanese: topic-comment ("As for X, ..."), article omission, L/R confusion in technical terms (less relevant for written prompts)
**Warning signs:** A linguist reviewer identifying patterns as stereotypes rather than documented transfer errors.

### Pitfall 5: SQLite Schema That Doesn't Match RDD
**What goes wrong:** Schema missing fields needed by later phases (grading, analysis).
**Why it happens:** Only implementing fields needed for Phase 1 without forward-looking design.
**How to avoid:** Implement the FULL schema from RDD Section 9.2 now, even though most fields will be NULL until later phases populate them. This prevents schema migrations.
**Warning signs:** Phase 3 (execution) or Phase 5 (analysis) needing ALTER TABLE.

### Pitfall 6: Prompt Curation Sampling Bias
**What goes wrong:** Selected prompts are non-representative (too easy, too hard, or skewed toward certain problem types).
**Why it happens:** Cherry-picking or using first-N instead of random sampling.
**How to avoid:** Use a fixed seed random sample from each benchmark. ~67 from HumanEval (out of 164), ~67 from MBPP (out of 974 total, use sanitized or test split), ~66 from GSM8K (out of ~1300 test). Record the sampling seed.
**Warning signs:** Benchmark difficulty distribution in sample not matching the full dataset.

## Code Examples

### Loading Benchmarks from Hugging Face
```python
# Source: HuggingFace datasets documentation
from datasets import load_dataset
import json
import random

def curate_prompts(seed: int = 42) -> list[dict]:
    """Download and sample 200 prompts from three benchmarks."""
    rng = random.Random(seed)
    prompts = []

    # HumanEval: 164 problems, sample ~67
    he = load_dataset("openai/openai_humaneval", split="test")
    he_indices = rng.sample(range(len(he)), 67)
    for i in he_indices:
        item = he[i]
        prompts.append({
            "benchmark_source": "humaneval",
            "problem_id": item["task_id"],  # e.g., "HumanEval/42"
            "prompt_text": item["prompt"],   # function signature + docstring
            "canonical_answer": item["canonical_solution"],
            "test_code": item["test"],       # for grading in Phase 2
            "answer_type": "code",
        })

    # MBPP: use sanitized split (427 problems) or test split
    mbpp = load_dataset("google-research-datasets/mbpp", "sanitized", split="test")
    mbpp_indices = rng.sample(range(len(mbpp)), 67)
    for i in mbpp_indices:
        item = mbpp[i]
        prompts.append({
            "benchmark_source": "mbpp",
            "problem_id": f"mbpp_{item['task_id']}",
            "prompt_text": item["prompt"],
            "canonical_answer": item["code"],
            "test_code": "\n".join(item["test_list"]),
            "answer_type": "code",
        })

    # GSM8K: ~8.5K problems, sample ~66
    gsm = load_dataset("openai/gsm8k", "main", split="test")
    gsm_indices = rng.sample(range(len(gsm)), 66)
    for i in gsm_indices:
        item = gsm[i]
        # Extract final numerical answer from "#### <number>" format
        answer_text = item["answer"]
        final_answer = answer_text.split("####")[-1].strip()
        prompts.append({
            "benchmark_source": "gsm8k",
            "problem_id": f"gsm8k_{i}",
            "prompt_text": item["question"],
            "canonical_answer": final_answer,
            "test_code": None,  # GSM8K uses regex grading, not code execution
            "answer_type": "numeric",
        })

    return prompts
```

### SQLite Schema (based on RDD Section 9.2)
```python
import sqlite3

CREATE_SCHEMA = """
CREATE TABLE IF NOT EXISTS experiment_runs (
    run_id TEXT PRIMARY KEY,
    prompt_id TEXT NOT NULL,
    benchmark TEXT NOT NULL,
    noise_type TEXT NOT NULL,        -- 'clean', 'type_a_5pct', 'type_a_10pct', 'type_a_20pct', 'type_b_mandarin', etc.
    noise_level TEXT,                -- '5', '10', '20', or NULL for type_b/clean
    intervention TEXT NOT NULL,      -- 'raw', 'self_correct', 'pre_proc_sanitize', 'pre_proc_sanitize_compress', 'prompt_repetition'
    model TEXT NOT NULL,
    repetition INTEGER NOT NULL,     -- 1-5

    -- Prompt data
    prompt_text TEXT,                -- The actual prompt sent (after noise/intervention)
    prompt_tokens INTEGER,
    optimized_tokens INTEGER,        -- After compression, if applicable

    -- Response data
    raw_output TEXT,
    cot_trace TEXT,
    completion_tokens INTEGER,

    -- Grading (populated in Phase 2)
    pass_fail INTEGER,               -- 0 or 1

    -- Timing (populated in Phase 3)
    ttft_ms REAL,
    ttlt_ms REAL,
    generation_ms REAL,

    -- Pre-processor tracking (populated in Phase 3)
    preproc_model TEXT,
    preproc_input_tokens INTEGER,
    preproc_output_tokens INTEGER,
    preproc_ttft_ms REAL,
    preproc_ttlt_ms REAL,

    -- Cost tracking (populated in Phase 3)
    main_model_input_cost_usd REAL,
    main_model_output_cost_usd REAL,
    preproc_cost_usd REAL,
    total_cost_usd REAL,

    -- Metadata
    temperature REAL DEFAULT 0.0,
    timestamp TEXT,
    status TEXT DEFAULT 'pending'    -- 'pending', 'running', 'complete', 'failed'
);

CREATE INDEX IF NOT EXISTS idx_runs_prompt ON experiment_runs(prompt_id);
CREATE INDEX IF NOT EXISTS idx_runs_condition ON experiment_runs(noise_type, intervention, model);
CREATE INDEX IF NOT EXISTS idx_runs_status ON experiment_runs(status);

-- Derived metrics table (populated in Phase 5)
CREATE TABLE IF NOT EXISTS derived_metrics (
    prompt_id TEXT NOT NULL,
    condition TEXT NOT NULL,          -- e.g., 'type_a_10pct_raw'
    model TEXT NOT NULL,
    consistency_rate REAL,
    majority_pass INTEGER,
    pass_count INTEGER,
    quadrant TEXT,                    -- 'robust', 'confidently_wrong', 'lucky', 'broken'
    mean_ttft_ms REAL,
    mean_ttlt_ms REAL,
    mean_total_latency_ms REAL,
    mean_total_cost_usd REAL,
    token_savings INTEGER,
    net_token_cost INTEGER,
    std_latency_ms REAL,
    PRIMARY KEY (prompt_id, condition, model)
);
"""

def init_database(db_path: str) -> sqlite3.Connection:
    """Create the results database with full schema."""
    conn = sqlite3.connect(db_path)
    conn.executescript(CREATE_SCHEMA)
    conn.execute("PRAGMA journal_mode=WAL")  # Better concurrent read performance
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
```

### Type A Mutation Operations
```python
# Weighted mutation operations per RDD Section 5.1
MUTATION_WEIGHTS = {
    "adjacent_key_swap": 0.40,
    "char_omission": 0.25,
    "char_doubling": 0.20,
    "char_transposition": 0.15,
}

def apply_mutation(char: str, index: int, text: str, rng: random.Random, adj_map: dict) -> str:
    """Apply a single character mutation based on weighted random selection."""
    roll = rng.random()
    if roll < 0.40:
        # Adjacent key swap
        neighbors = adj_map.get(char.lower(), [])
        if neighbors:
            replacement = rng.choice(neighbors)
            return replacement if char.islower() else replacement.upper()
        return char  # No neighbors (rare), skip
    elif roll < 0.65:
        # Character omission
        return ""
    elif roll < 0.85:
        # Character doubling
        return char + char
    else:
        # Transposition (swap with next char)
        if index < len(text) - 1:
            return text[index + 1] + char  # Handled at caller level
        return char
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `random.seed(N)` global state | `random.Random(N)` instance per context | Always available, but underused | Prevents cross-contamination between noise sources |
| Manual benchmark file downloads | `datasets` library from HuggingFace | 2020+ | Standardized access, caching, versioning |
| Flat JSON result files | SQLite with typed schema | Project convention | Queryable, supports concurrent writes with WAL mode |

**Deprecated/outdated:**
- HumanEval GitHub repo's built-in execution harness is outdated; EvalPlus is the current standard for code eval. However, we only need the prompts in Phase 1, not the execution harness.
- `google-generativeai` package in pyproject.toml is deprecated (replaced by `google-genai`), but this is a Phase 3 concern.

## Open Questions

1. **MBPP Split Selection**
   - What we know: MBPP has multiple splits -- "full" (974 problems), "sanitized" (427 hand-verified), and standard train/test splits. The sanitized split has cleaner problem descriptions.
   - What's unclear: Which split best serves the study. The "sanitized" split has higher quality but fewer problems (427 vs 974).
   - Recommendation: Use the sanitized test split for higher quality problem descriptions. 427 problems is more than enough to sample 67.

2. **HumanEval Prompt Format**
   - What we know: HumanEval prompts are function signatures with docstrings, not natural language questions. They look like `def function_name(args):\n    """docstring with examples"""\n`.
   - What's unclear: Whether this format is suitable for noise injection. Character-level noise in code signatures could break parsing.
   - Recommendation: The keyword protection mechanism handles this. Function signatures, keywords, and variable names are protected. Noise applies to the natural language portions (docstring text).

3. **GSM8K Problem ID Stability**
   - What we know: GSM8K doesn't have stable problem IDs like HumanEval's `task_id`. Problems are identified by index.
   - What's unclear: Whether indices are stable across dataset versions.
   - Recommendation: Use the canonical HuggingFace dataset version (`openai/gsm8k`) and store the index along with a hash of the question text for verification.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-01 | 200 prompts curated with correct schema | unit | `pytest tests/test_prompts.py -x` | No -- Wave 0 |
| DATA-02 | Experiment matrix has correct dimensions and structure | unit | `pytest tests/test_matrix.py -x` | No -- Wave 0 |
| DATA-03 | SQLite schema created, inserts/queries work | unit | `pytest tests/test_db.py -x` | No -- Wave 0 |
| DATA-04 | Config module exposes all required constants | unit | `pytest tests/test_config.py -x` | No -- Wave 0 |
| NOISE-01 | Type A noise at 5/10/20% produces expected error rates | unit | `pytest tests/test_noise_generator.py::test_type_a_error_rates -x` | No -- Wave 0 |
| NOISE-02 | Protected tokens survive mutation | unit | `pytest tests/test_noise_generator.py::test_keyword_protection -x` | No -- Wave 0 |
| NOISE-03 | Type B ESL patterns produce linguistically valid transformations | unit | `pytest tests/test_noise_generator.py::test_type_b_patterns -x` | No -- Wave 0 |
| NOISE-04 | Same seed produces identical output | unit | `pytest tests/test_noise_generator.py::test_determinism -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/conftest.py` -- Shared fixtures (sample prompts, temp DB, config instances)
- [ ] `tests/test_config.py` -- Covers DATA-04
- [ ] `tests/test_noise_generator.py` -- Covers NOISE-01 through NOISE-04
- [ ] `tests/test_db.py` -- Covers DATA-03
- [ ] `tests/test_prompts.py` -- Covers DATA-01
- [ ] `tests/test_matrix.py` -- Covers DATA-02

## Sources

### Primary (HIGH confidence)
- RDD Section 5.1 -- Type A noise mutation weights (40/25/20/15), error rates (5/10/20%)
- RDD Section 5.2 -- Type B ESL patterns (Mandarin, Spanish, Japanese, Mixed)
- RDD Section 9.2 -- Execution log schema (all fields documented)
- RDD Section 4.1 -- Experimental design matrix (2x4 factorial + compression)
- RDD Section 4.3 -- Benchmark selection (HumanEval 164, MBPP 974, GSM8K ~1300)
- CLAUDE.md -- Project conventions (logging, seeds, pinned models, SQLite)
- CONTEXT.md -- All locked decisions from discuss phase

### Secondary (MEDIUM confidence)
- [HuggingFace openai/openai_humaneval](https://huggingface.co/datasets/openai/openai_humaneval) -- Dataset structure and fields
- [HuggingFace google-research-datasets/mbpp](https://huggingface.co/datasets/google-research-datasets/mbpp) -- MBPP splits and sanitized version
- [HuggingFace openai/gsm8k](https://huggingface.co/datasets/openai/gsm8k) -- GSM8K format with "####" answer extraction
- [ACL BEA 2021 - Identifying negative language transfer in learner errors](https://aclanthology.org/2021.bea-1.7.pdf) -- L1 transfer patterns for ESL noise
- [Typo-Distance QWERTY mapping](https://github.com/wsong/Typo-Distance) -- Keyboard adjacency grid approach

### Tertiary (LOW confidence)
- General SLA research on Mandarin/Spanish/Japanese L1 transfer -- patterns are well-documented but specific regex implementations need validation against corpus data

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- stdlib Python + one external library (`datasets`), all verified
- Architecture: HIGH -- patterns are straightforward Python with well-understood requirements from RDD
- Pitfalls: HIGH -- determinism, keyword protection, and matrix dimensions are concrete, testable concerns
- ESL patterns: MEDIUM -- linguistic accuracy requires careful implementation against SLA literature

**Research date:** 2026-03-19
**Valid until:** 2026-04-19 (stable domain, no fast-moving dependencies)
