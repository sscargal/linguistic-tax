# Phase 4: Pilot Validation - Research

**Researched:** 2026-03-21
**Domain:** End-to-end pilot validation, grading spot-check, cost projection, pipeline validation
**Confidence:** HIGH

## Summary

Phase 4 is a validation gate, not a feature-building phase. The execution engine, grading pipeline, and all interventions already exist from Phases 1-3. This phase creates a standalone `src/pilot.py` module that: (1) selects 20 stratified prompts, (2) runs them through the full pipeline, (3) validates grading accuracy via automated spot-check, (4) audits data completeness, (5) checks noise injection fidelity, (6) measures pre-processor semantic fidelity via BERTScore, (7) profiles latency, (8) projects full-run cost with bootstrap CIs, and (9) produces a structured PASS/FAIL verdict.

The pilot run involves 8,200 API calls (410 items per prompt x 20 prompts), not ~4,100 as initially estimated. This is because each prompt has 8 noise types x 5 interventions x 2 models x 5 repetitions = 400 (noise_recovery experiment) + 10 (compression experiment with `compress_only` intervention). Estimated pilot cost is ~$28 across all models including pre-processor calls.

**Primary recommendation:** Build `src/pilot.py` as a single module with clear entry points (`select_pilot_prompts()`, `run_spot_check()`, `compute_cost_projection()`, `run_pilot_verdict()`) that compose the existing execution engine and grading pipeline rather than reimplementing any logic.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Stratified sample across benchmarks: ~7 HumanEval, ~7 MBPP, ~6 GSM8K
- Selection uses a fixed seed for reproducibility
- Full factorial design: all noise types x levels x interventions x 5 repetitions
- Selected prompt IDs saved to `data/pilot_prompts.json` for auditability
- Standalone `src/pilot.py` module with `select_pilot_prompts()`, `run_spot_check()`, `compute_cost_projection()`
- Automated spot-check report: ALL GSM8K results + 20% of code grading results
- Failure criterion: any systematic grading error pattern = fail. Isolated edge cases acceptable.
- Report saved to `results/pilot_spot_check.json`
- Per-condition cost breakdown with bootstrap CIs
- Budget gate: `--budget` flag with configurable threshold (default $200)
- Output: `results/pilot_cost_projection.json` + terminal summary table
- Minimum 95% completion rate. Any systematic failure = auto-fail.
- Zero-variance flag: informational, not auto-fail
- Structured verdict: `results/pilot_verdict.json` with overall PASS/FAIL
- Informational power analysis in verdict report
- Latency profiling from pilot TTFT/TTLT data
- Pre-processor fidelity via BERTScore (0.85 threshold starting point)
- Data completeness audit: no unexpected NULLs, correct model versions, timestamps, non-zero tokens
- Noise injection sanity check: verify runtime error rates match expected rates

### Claude's Discretion
- Exact BERTScore threshold tuning (0.85 is starting point)
- Bootstrap sample count for cost projection CIs
- Power analysis methodology (rough estimate is fine)
- Internal structure of verdict report
- How to present the spot-check comparison (table format, grouping)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PILOT-01 | Run pilot experiment with 20 prompts across all conditions to validate full pipeline end-to-end | Pilot prompt selection via stratified sampling, execution via existing `run_experiment.py` engine filtered to pilot prompt IDs, data completeness audit, noise sanity check |
| PILOT-02 | Verify grading accuracy via manual spot-check of pilot results | Automated spot-check report covering ALL GSM8K + 20% code results, side-by-side comparison format, systematic error detection |
| PILOT-03 | Generate cost projection for full experiment run from pilot data | Per-condition cost rollup from actual pilot data, bootstrap CIs, budget gate with configurable threshold, wall-clock time estimate |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| bert-score | 0.3.13+ | Pre-processor semantic fidelity measurement | Already in pyproject.toml; standard NLP metric for meaning preservation |
| scipy | 1.12.0+ | Bootstrap CIs for cost projection | Already in pyproject.toml; `scipy.stats.bootstrap` for confidence intervals |
| numpy | (transitive) | Array operations for statistical computations | Comes with scipy/bert-score |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sqlite3 | stdlib | Query pilot results from DB | All analysis functions read from results.db |
| json | stdlib | Read/write pilot config and reports | pilot_prompts.json, verdict.json, etc. |
| random | stdlib | Stratified prompt selection with fixed seed | `select_pilot_prompts()` |
| logging | stdlib | All output per CLAUDE.md conventions | Throughout pilot.py |
| argparse | stdlib | CLI interface for pilot module | Entry point with --budget, --db flags |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| scipy.stats.bootstrap | Manual bootstrap loop | scipy provides correct BCa intervals out of the box |
| bert-score | Manual cosine similarity | BERTScore captures semantic similarity better than naive approaches |

**Installation:**
```bash
pip install bert-score  # already in pyproject.toml but may not be installed yet
```

**Version verification:** All packages already pinned in pyproject.toml. BERTScore 0.3.13 is the minimum version specified.

## Architecture Patterns

### Recommended Project Structure
```
src/
  pilot.py               # NEW: Pilot validation module
data/
  pilot_prompts.json      # NEW: Selected pilot prompt IDs
results/
  pilot_spot_check.json   # NEW: Grading spot-check report
  pilot_cost_projection.json  # NEW: Cost projection with CIs
  pilot_verdict.json      # NEW: Structured PASS/FAIL verdict
tests/
  test_pilot.py           # NEW: Unit tests for pilot module
```

### Pattern 1: Composition Over Reimplementation
**What:** `pilot.py` composes existing modules rather than reimplementing logic
**When to use:** Always -- the execution engine, grading, noise generation, and DB access already exist
**Example:**
```python
# Filter experiment matrix to pilot prompts, then use run_engine
def run_pilot(pilot_prompt_ids: list[str], budget: float = 200.0, db_path: str | None = None) -> dict:
    """Run pilot experiment for selected prompts."""
    # Load and filter matrix to pilot prompt IDs
    # Use run_experiment.run_engine() or _process_item() for execution
    # Then run analysis functions on results
```

### Pattern 2: Argparse CLI with Subcommands or Sequential Steps
**What:** CLI entry point matching existing patterns in run_experiment.py, grade_results.py
**When to use:** For the pilot.py main() function
**Example:**
```python
def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pilot validation for Linguistic Tax")
    parser.add_argument("--budget", type=float, default=200.0, help="Budget threshold for full run")
    parser.add_argument("--db", type=str, default=None, help="Override results DB path")
    parser.add_argument("--select-only", action="store_true", help="Only select prompts, don't run")
    parser.add_argument("--analyze-only", action="store_true", help="Only analyze existing results")
    return parser
```

### Pattern 3: JSON Report Output
**What:** All pilot outputs saved as structured JSON for auditability and downstream consumption
**When to use:** For spot-check, cost projection, and verdict reports
**Example:**
```python
# Each report is a self-contained JSON file
{
    "generated_at": "2026-03-21T...",
    "pilot_prompt_ids": [...],
    "total_items": 8200,
    "completion_rate": 0.98,
    ...
}
```

### Anti-Patterns to Avoid
- **Reimplementing execution logic:** Do NOT rebuild the item processing loop -- use existing `_process_item()` or `run_engine()`
- **Hardcoding pilot prompt IDs:** Use seeded random selection saved to `data/pilot_prompts.json`
- **Using print() for output:** Use Python `logging` module per CLAUDE.md conventions
- **Storing results outside SQLite:** All experimental results go in `results.db`; only analysis reports use JSON

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Bootstrap CIs | Manual resampling loop | `scipy.stats.bootstrap()` | Correct BCa intervals, handles edge cases |
| Semantic similarity | Token overlap or cosine sim | `bert_score.score()` | Contextual embeddings capture meaning preservation |
| Stratified sampling | Manual group-by-benchmark logic | Simple `random.Random(seed).sample()` per group | Straightforward, deterministic |
| Cost computation | Manual price lookups | `src.config.compute_cost()` | Already implemented with full price table |
| Noise injection verification | Re-implementing noise | `src.noise_generator.inject_type_a_noise()` | Already tested for determinism |

**Key insight:** Phase 4 creates NO new infrastructure -- it validates and reports on what Phases 1-3 built.

## Common Pitfalls

### Pitfall 1: `compress_only` Intervention Not Handled
**What goes wrong:** The experiment matrix contains items with `intervention='compress_only'` (10 per prompt, from the "compression" experiment). But `apply_intervention()` in `run_experiment.py` does not handle this case -- it will raise `ValueError("Unknown intervention: compress_only")`.
**Why it happens:** The matrix was built in Phase 1 to cover all experiments including the standalone compression study. Phase 3 implemented the 5 main interventions but missed `compress_only`.
**How to avoid:** Either (a) add a `compress_only` case to `apply_intervention()` that calls compress without sanitize, or (b) filter out `compress_only` items from the pilot (since the CONTEXT.md discussions only mention the 5 main interventions). Decision needed before implementation.
**Warning signs:** ValueError exceptions during pilot execution on clean+compress_only items.

### Pitfall 2: Actual Item Count is 8,200, Not ~4,100
**What goes wrong:** The CONTEXT.md estimates ~4,100 API calls. The actual count is 8,200 (410 items per prompt x 20 prompts). This is because 8 noise types x 5 interventions x 2 models x 5 reps = 400, plus 10 compression items per prompt.
**Why it happens:** The ~4,100 estimate likely counted conditions per model (205 per prompt) not both models.
**How to avoid:** Base cost estimates on actual matrix filtering. Estimated pilot cost is ~$28 total.
**Warning signs:** Pilot runs longer and costs more than expected.

### Pitfall 3: BERTScore First-Run Download
**What goes wrong:** BERTScore downloads a ~400MB model (roberta-large) on first invocation. This can cause timeouts or failures if not anticipated.
**Why it happens:** The model is not bundled with the pip package.
**How to avoid:** Document the first-run download requirement. Consider pre-downloading in a setup step.
**Warning signs:** Long hang on first BERTScore call, network errors.

### Pitfall 4: Spot-Check Sampling Bias
**What goes wrong:** Random sampling of code results for spot-check may miss systematic errors concentrated in one benchmark or noise condition.
**Why it happens:** Pure random sampling does not stratify by benchmark/noise/intervention.
**How to avoid:** Stratify spot-check sampling: ensure representation across benchmarks, noise types, and interventions. The decision to check ALL GSM8K results already addresses the most fragile path.
**Warning signs:** Spot-check passes but full run reveals consistent grading errors in one condition.

### Pitfall 5: GSM8K Extraction Edge Cases
**What goes wrong:** GSM8K regex extraction is the most fragile grading path. Noisy prompts can cause LLMs to produce unusual answer formats not captured by the extraction patterns.
**Why it happens:** Type A noise at 20% can significantly alter prompt structure, causing LLMs to respond in unexpected formats.
**How to avoid:** The spot-check explicitly checks ALL GSM8K results. Look for patterns in `fail_reason='extraction_failed'` vs. `fail_reason='wrong_answer'`.
**Warning signs:** High `extraction_failed` rate in GSM8K results under high noise conditions.

### Pitfall 6: Zero-Variance Expectation at temp=0
**What goes wrong:** All 5 repetitions may produce identical results for many conditions since temperature=0.0. This is expected behavior, not an error.
**Why it happens:** Deterministic sampling at temperature=0.
**How to avoid:** The zero-variance flag is informational only. Do NOT auto-fail on this. However, if variance IS observed (different results across repetitions), that is the more interesting finding worth investigating.
**Warning signs:** Zero-variance across literally ALL conditions might indicate a pipeline bug (e.g., caching responses).

## Code Examples

### Stratified Prompt Selection
```python
import json
import random

def select_pilot_prompts(
    prompts_path: str = "data/prompts.json",
    seed: int = 42,
    n_humaneval: int = 7,
    n_mbpp: int = 7,
    n_gsm8k: int = 6,
) -> list[str]:
    """Select stratified pilot prompts across benchmarks."""
    with open(prompts_path) as f:
        prompts = json.load(f)

    by_benchmark: dict[str, list[str]] = {}
    for p in prompts:
        by_benchmark.setdefault(p["benchmark_source"], []).append(p["problem_id"])

    rng = random.Random(seed)
    selected: list[str] = []
    selected.extend(rng.sample(by_benchmark["humaneval"], n_humaneval))
    selected.extend(rng.sample(by_benchmark["mbpp"], n_mbpp))
    selected.extend(rng.sample(by_benchmark["gsm8k"], n_gsm8k))
    return selected
```

### Bootstrap Cost Projection
```python
import numpy as np
from scipy.stats import bootstrap

def compute_cost_projection(
    pilot_costs: list[float],
    n_pilot_prompts: int = 20,
    n_full_prompts: int = 200,
    n_bootstrap: int = 10000,
    confidence_level: float = 0.95,
) -> dict:
    """Project full-run cost from pilot data with bootstrap CIs."""
    pilot_array = np.array(pilot_costs)
    scale_factor = n_full_prompts / n_pilot_prompts

    # Total pilot cost and projection
    pilot_total = pilot_array.sum()
    projected_total = pilot_total * scale_factor

    # Bootstrap CI on the per-prompt cost, then scale
    per_prompt = pilot_array  # cost per prompt aggregated
    result = bootstrap(
        (per_prompt,),
        np.sum,
        n_resamples=n_bootstrap,
        confidence_level=confidence_level,
        method="bca",
    )
    ci_low = result.confidence_interval.low * scale_factor
    ci_high = result.confidence_interval.high * scale_factor

    return {
        "pilot_total_cost": float(pilot_total),
        "projected_full_cost": float(projected_total),
        "ci_low": float(ci_low),
        "ci_high": float(ci_high),
        "confidence_level": confidence_level,
        "n_bootstrap": n_bootstrap,
    }
```

### BERTScore Fidelity Check
```python
from bert_score import score as bert_score_fn

def check_preproc_fidelity(
    originals: list[str],
    preprocessed: list[str],
    threshold: float = 0.85,
) -> dict:
    """Check pre-processor semantic fidelity using BERTScore."""
    P, R, F1 = bert_score_fn(
        preprocessed, originals,
        lang="en",
        verbose=False,
    )
    f1_scores = F1.tolist()
    flagged = [
        {"index": i, "f1": f1_scores[i]}
        for i in range(len(f1_scores))
        if f1_scores[i] < threshold
    ]
    return {
        "mean_f1": float(sum(f1_scores) / len(f1_scores)),
        "min_f1": float(min(f1_scores)),
        "threshold": threshold,
        "flagged_count": len(flagged),
        "flagged_pairs": flagged,
    }
```

### Data Completeness Audit
```python
def audit_data_completeness(conn, pilot_prompt_ids: list[str]) -> dict:
    """Verify all expected fields are populated in pilot results."""
    required_fields = [
        "prompt_text", "prompt_tokens", "raw_output", "completion_tokens",
        "pass_fail", "ttft_ms", "ttlt_ms", "total_cost_usd",
        "model", "timestamp",
    ]
    issues = []
    rows = query_runs(conn, status="completed")
    pilot_rows = [r for r in rows if r["prompt_id"] in pilot_prompt_ids]

    for row in pilot_rows:
        for field in required_fields:
            if row.get(field) is None:
                issues.append({"run_id": row["run_id"], "field": field, "issue": "NULL"})
        if row.get("prompt_tokens", 0) == 0:
            issues.append({"run_id": row["run_id"], "field": "prompt_tokens", "issue": "zero"})

    return {
        "total_checked": len(pilot_rows),
        "issues_found": len(issues),
        "issues": issues,
    }
```

### Noise Injection Sanity Check
```python
def verify_noise_rates(
    prompts_by_id: dict,
    pilot_prompt_ids: list[str],
    base_seed: int = 42,
    tolerance: float = 0.5,  # allow 50% relative deviation
) -> dict:
    """Verify noise injection produces expected error rates."""
    from src.noise_generator import inject_type_a_noise
    from src.config import derive_seed

    results = []
    for pid in pilot_prompt_ids:
        prompt = prompts_by_id[pid]
        clean = prompt["prompt_text"]
        answer_type = prompt.get("answer_type", "code")
        for rate_str, rate_float in [("5", 0.05), ("10", 0.10), ("20", 0.20)]:
            seed = derive_seed(base_seed, pid, "type_a", rate_str)
            noisy = inject_type_a_noise(clean, error_rate=rate_float, seed=seed, answer_type=answer_type)
            # Count character differences
            diffs = sum(1 for a, b in zip(clean, noisy) if a != b)
            # Account for length changes
            diffs += abs(len(clean) - len(noisy))
            actual_rate = diffs / max(len(clean), 1)
            expected_rate = rate_float
            deviation = abs(actual_rate - expected_rate) / expected_rate if expected_rate > 0 else 0
            results.append({
                "prompt_id": pid,
                "noise_level": rate_str,
                "expected_rate": expected_rate,
                "actual_rate": round(actual_rate, 4),
                "relative_deviation": round(deviation, 4),
                "flagged": deviation > tolerance,
            })

    flagged = [r for r in results if r["flagged"]]
    return {
        "total_checks": len(results),
        "flagged_count": len(flagged),
        "flagged": flagged,
    }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual pilot validation | Automated spot-check with structured verdict | N/A (this phase defines it) | Reproducible validation gate |
| Simple cost extrapolation | Bootstrap CIs on per-condition costs | N/A | Accounts for cost variance across conditions |

**Key note:** This phase does not adopt new libraries or approaches. It composes existing Phase 1-3 infrastructure into a validation workflow.

## Open Questions

1. **`compress_only` intervention handling**
   - What we know: The experiment matrix has 10 items per prompt with `intervention='compress_only'` and `experiment='compression'`. The `apply_intervention()` function in `run_experiment.py` does not handle this case.
   - What's unclear: Should the pilot include these items or filter them out? If included, `compress_only` needs to be added to the intervention router.
   - Recommendation: Add `compress_only` to the intervention router in `run_experiment.py` (routes to compress-without-sanitize), since these are legitimate experiment items. Alternatively, filter them from the pilot if the compression experiment is not part of the pilot scope. The CONTEXT.md mentions "all noise conditions and intervention types" which suggests inclusion.

2. **BERTScore model selection**
   - What we know: Default BERTScore uses `roberta-large` (~400MB download). Lighter models exist.
   - What's unclear: Whether the default model is sufficient or if `microsoft/deberta-xlarge-mnli` (recommended for English) is better.
   - Recommendation: Use the default `roberta-large` -- well-established, adequate for this use case, and the 0.85 threshold was likely calibrated against it.

3. **Power analysis methodology**
   - What we know: RDD Section 21.3 requests a rough power analysis after pilot to check if N=200 is sufficient for GLMM effect sizes.
   - What's unclear: Exact methodology for pilot-stage power estimation with binary outcomes and crossed random effects.
   - Recommendation: Use observed pilot effect sizes (pass rate differences between clean and noisy conditions) to compute required N via a simplified binomial power calculation. This is explicitly an informational rough estimate, not the full GLMM power analysis (deferred to Phase 5).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_pilot.py -x` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PILOT-01 | Stratified prompt selection produces correct counts | unit | `pytest tests/test_pilot.py::test_select_pilot_prompts -x` | No -- Wave 0 |
| PILOT-01 | Pilot matrix filtering returns correct item count | unit | `pytest tests/test_pilot.py::test_filter_pilot_matrix -x` | No -- Wave 0 |
| PILOT-01 | Data completeness audit detects NULL fields | unit | `pytest tests/test_pilot.py::test_data_completeness_audit -x` | No -- Wave 0 |
| PILOT-01 | Noise sanity check verifies expected error rates | unit | `pytest tests/test_pilot.py::test_noise_sanity_check -x` | No -- Wave 0 |
| PILOT-02 | Spot-check selects ALL GSM8K + 20% code results | unit | `pytest tests/test_pilot.py::test_spot_check_sampling -x` | No -- Wave 0 |
| PILOT-02 | Spot-check report contains required fields | unit | `pytest tests/test_pilot.py::test_spot_check_report_format -x` | No -- Wave 0 |
| PILOT-03 | Cost projection scales correctly from pilot to full | unit | `pytest tests/test_pilot.py::test_cost_projection -x` | No -- Wave 0 |
| PILOT-03 | Budget gate triggers when projection exceeds threshold | unit | `pytest tests/test_pilot.py::test_budget_gate -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_pilot.py -x`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_pilot.py` -- covers PILOT-01, PILOT-02, PILOT-03
- [ ] No new framework install needed -- pytest already configured

## Sources

### Primary (HIGH confidence)
- Direct code inspection of `src/run_experiment.py`, `src/config.py`, `src/db.py`, `src/grade_results.py` -- verified all function signatures, DB schema, price table
- Direct inspection of `data/experiment_matrix.json` -- verified 82,000 items, 410 per prompt, `compress_only` intervention presence
- Direct inspection of `data/prompts.json` -- verified 200 prompts (67 HumanEval, 67 MBPP, 66 GSM8K)
- `docs/RDD_Linguistic_Tax_v4.md` Section 9.2 -- execution log schema fields
- `docs/RDD_Linguistic_Tax_v4.md` Section 21.3 -- power analysis recommendation
- `pyproject.toml` -- verified all dependencies including bert-score

### Secondary (MEDIUM confidence)
- BERTScore default model (roberta-large) -- based on library documentation and common usage
- scipy.stats.bootstrap BCa method -- standard scipy API

### Tertiary (LOW confidence)
- BERTScore 0.85 threshold appropriateness -- starting point from CONTEXT.md, may need tuning based on actual data

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in pyproject.toml, no new dependencies
- Architecture: HIGH -- straightforward composition of existing modules, patterns well-established in codebase
- Pitfalls: HIGH -- discovered from direct code inspection (compress_only gap, item count discrepancy)
- Cost estimates: MEDIUM -- based on rough token assumptions (500 in, 200 out); actual costs depend on prompt length distribution

**Research date:** 2026-03-21
**Valid until:** 2026-04-21 (stable -- no fast-moving dependencies)
