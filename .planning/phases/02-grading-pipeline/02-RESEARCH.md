# Phase 2: Grading Pipeline - Research

**Researched:** 2026-03-19
**Domain:** Python subprocess sandboxing, regex-based numerical extraction, SQLite schema extension
**Confidence:** HIGH

## Summary

Phase 2 builds an auto-grading pipeline for two distinct problem types: code execution (HumanEval/MBPP) and numerical answer matching (GSM8K). The code grading path requires a subprocess sandbox with resource limits (timeout, memory, fork bomb protection) using Python's standard library `subprocess` and `resource` modules -- no external dependencies needed. The math grading path requires regex-based extraction of the last numerical answer from LLM output with normalization for format variants (commas, currency, fractions, percentages, LaTeX).

The existing codebase provides a solid foundation: `src/db.py` has the schema with a `pass_fail` INTEGER column, `data/prompts.json` contains 200 prompts (67 HumanEval, 67 MBPP, 66 GSM8K) with `test_code` fields for code benchmarks and `canonical_answer` for GSM8K. HumanEval tests use a `check(candidate)` pattern while MBPP tests use direct `assert` statements -- the grader must handle both conventions.

**Primary recommendation:** Build `src/grade_results.py` as a single module with separate `grade_code()` and `grade_math()` functions, a `_run_sandbox()` helper for subprocess execution with `resource.setrlimit()` in `preexec_fn`, and a thin argparse CLI. Extend the SQLite schema with a `grading_details` table for stdout/stderr/fail_reason/extraction_method metadata.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Sandbox Security Model**: subprocess-based with resource limits (no Docker). 10s timeout, 512 MB RLIMIT_AS, RLIMIT_NPROC capped at ~10. Allow file writes in temp dir, allow network. Same Python interpreter. Sequential execution.
- **Code Execution Model**: Separate runners for HumanEval vs MBPP. Strip markdown fences, use last code block. Test assertions bundled in prompts.json. Optional CLI subcommand for HuggingFace test data refresh.
- **GSM8K Answer Extraction**: Normalized comparison -- strip commas/whitespace/currency/units, convert to float, compare within epsilon (1e-6). Extract last number. Convert fractions/percentages to decimal. Handle negative formats. Log extraction method.
- **Grading Interface**: Python API (grade_code(), grade_math()) with thin CLI wrapper via argparse. Single file: src/grade_results.py. Batch mode for single run or all NULL pass_fail. Auto-detect benchmark type. CLI output: summary/json/table. Re-grading with --force flag.
- **Edge Case Handling**: All failures recorded as pass_fail=0 with reason codes: timeout, crash, memory_exceeded, syntax_error, no_output, extraction_failed, import_error. Binary grading (all-or-nothing). Empty responses fail with no_output.
- **Logging and Storage**: Capture full stdout, stderr, return code, execution time. Store grading details in SQLite. Need new columns or grading_details table.
- **Testing**: Adversarial sandbox tests (infinite loops, memory bombs, fork bombs). 15-20 GSM8K format variant tests.

### Claude's Discretion
- Return type design for grade_code()/grade_math() (bool, dataclass, or dict)
- Exact DB schema changes (new columns vs separate table)
- Specific regex patterns for GSM8K number extraction
- Pre-check with ast.parse() before subprocess (optimization choice)
- How to distinguish assertion failures from other runtime errors in reason codes

### Deferred Ideas (OUT OF SCOPE)
- Docker container isolation for sandbox execution
- Parallel sandbox execution
- Non-Python code detection
- Multiple function definition handling
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| GRAD-01 | Auto-grade HumanEval/MBPP outputs via sandboxed subprocess code execution with timeout and resource limits | Subprocess sandbox pattern with resource.setrlimit(), separate HumanEval (check/candidate) vs MBPP (direct assert) runners, code extraction from markdown |
| GRAD-02 | Auto-grade GSM8K outputs via regex extraction of final numerical answer with format-variant handling | Multi-pattern regex extractor with normalization pipeline, epsilon comparison, extraction method logging |
| GRAD-03 | Record pass/fail result for every experimental run in SQLite | Existing pass_fail column + new grading_details table for metadata (stdout, stderr, fail_reason, extraction_method, execution_time_ms) |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| subprocess | stdlib | Execute LLM-generated code in isolated process | Standard Python process management, supports timeout and preexec_fn |
| resource | stdlib | Set RLIMIT_AS, RLIMIT_NPROC, RLIMIT_CPU on child process | Only way to set per-process resource limits on Linux without Docker |
| tempfile | stdlib | Create isolated temp directories for sandbox execution | Standard for ephemeral workspaces, auto-cleanup support |
| re | stdlib | GSM8K answer extraction regex patterns | Standard regex, sufficient for number extraction |
| ast | stdlib | Optional pre-check of LLM code syntax before execution | Catches SyntaxError cheaply without subprocess overhead |
| sqlite3 | stdlib | Extend schema and write grading results | Already used by src/db.py |
| argparse | stdlib | CLI interface | Already used by src/noise_generator.py |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| signal | stdlib | SIGALRM as backup timeout in child process | Belt-and-suspenders alongside subprocess.run(timeout=) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| subprocess + resource | Docker/containers | Docker adds dependency, overkill for research; deferred per user decision |
| resource.setrlimit | cgroups v2 | Requires root, more complex; RLIMIT sufficient for research sandbox |
| re (regex) | sympy.parsing | Heavy dependency for simple number extraction; regex is sufficient |

**Installation:**
```bash
# No additional packages needed -- all stdlib
```

**Version verification:** All standard library modules, ship with Python 3.13.3 (confirmed on this system).

## Architecture Patterns

### Recommended Project Structure
```
src/
  grade_results.py      # Main grading module (API + CLI)
tests/
  test_grade_results.py # Grading tests including adversarial sandbox tests
```

### Pattern 1: Subprocess Sandbox with Resource Limits
**What:** Execute untrusted LLM code in a subprocess with `preexec_fn` setting resource limits via `resource.setrlimit()`.
**When to use:** Every HumanEval/MBPP code execution.
**Example:**
```python
import resource
import subprocess
import tempfile
import os

def _set_limits() -> None:
    """preexec_fn for subprocess: set resource limits on child process."""
    # 512 MB memory limit
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
    # Max 10 child processes (prevents fork bombs)
    resource.setrlimit(resource.RLIMIT_NPROC, (10, 10))
    # CPU time limit as backup (slightly above timeout to let subprocess.run handle it first)
    resource.setrlimit(resource.RLIMIT_CPU, (15, 15))

def _run_sandbox(code: str, timeout: float = 10.0) -> subprocess.CompletedProcess:
    """Execute code string in a sandboxed subprocess."""
    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = os.path.join(tmpdir, "solution.py")
        with open(script_path, "w") as f:
            f.write(code)
        result = subprocess.run(
            [os.sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=tmpdir,
            preexec_fn=_set_limits,
        )
        return result
```

### Pattern 2: HumanEval Test Harness Assembly
**What:** HumanEval tests use `def check(candidate)` where `candidate` is the LLM's function. The harness concatenates: LLM code + test code + `check(function_name)` call.
**When to use:** All HumanEval grading.
**Key insight:** The function name must be extracted from the prompt text (it appears as `def function_name(` in the prompt). The test code defines `check(candidate)` which is then called with the actual function name.
**Example:**
```python
def _build_humaneval_harness(llm_code: str, test_code: str, entry_point: str) -> str:
    """Assemble HumanEval execution script.

    Args:
        llm_code: Extracted code from LLM response.
        test_code: Test assertions from prompts.json test_code field.
        entry_point: Function name from prompt (e.g., 'separate_paren_groups').
    """
    # Strip METADATA dict if present (30 of 67 HumanEval tests have it)
    # Keep only the check() function definition and call
    return f"{llm_code}\n\n{test_code}\n\ncheck({entry_point})\n"
```

### Pattern 3: MBPP Test Harness Assembly
**What:** MBPP tests use direct `assert function_name(args) == expected` without a `check(candidate)` wrapper.
**When to use:** All MBPP grading.
**Example:**
```python
def _build_mbpp_harness(llm_code: str, test_code: str) -> str:
    """Assemble MBPP execution script. Simpler than HumanEval."""
    return f"{llm_code}\n\n{test_code}\n"
```

### Pattern 4: GSM8K Multi-Pattern Number Extraction
**What:** Extract the last number from LLM response using a cascade of regex patterns with normalization.
**When to use:** All GSM8K grading.
**Example:**
```python
import re
from dataclasses import dataclass

@dataclass
class ExtractionResult:
    value: float
    method: str  # 'last_number', 'fraction_converted', 'percentage', 'latex_boxed'
    raw_match: str

def _extract_number(text: str) -> ExtractionResult | None:
    """Extract final numerical answer from LLM response.

    Strategy: Check for LaTeX boxed first (explicit answer marker),
    then find all numbers, take the last one, normalize.
    """
    # 1. Check for LaTeX \boxed{answer} (explicit answer marker, highest priority)
    boxed = re.findall(r'\\boxed\{([^}]+)\}', text)
    if boxed:
        return _parse_number(boxed[-1], method='latex_boxed')

    # 2. Find all number-like patterns in text
    # Matches: integers, decimals, comma-separated, fractions, percentages
    # Handles negatives including (42) accounting notation
    patterns = [
        (r'[-]?\d{1,3}(?:,\d{3})+(?:\.\d+)?', 'comma_separated'),  # 1,234.56
        (r'[-]?\d+/\d+', 'fraction'),                                 # 3/4
        (r'[-]?\d+\.?\d*\s*%', 'percentage'),                         # 50%
        (r'\((\d+\.?\d*)\)', 'paren_negative'),                       # (42)
        (r'[-]?\d+\.\d+', 'decimal'),                                 # 3.14
        (r'[-]?\d+', 'integer'),                                       # 42
    ]
    # ... find all matches, take last one, normalize
```

### Pattern 5: GradeResult Dataclass
**What:** Structured return type for grading functions.
**Recommendation:** Use a dataclass (Claude's discretion item). Dataclass is preferable over dict (type safety, IDE support) or bool (loses metadata).
```python
@dataclass
class GradeResult:
    """Result of grading a single experimental run."""
    passed: bool           # True if pass, False if fail
    fail_reason: str | None  # None if passed; reason code if failed
    stdout: str            # Captured stdout from execution
    stderr: str            # Captured stderr from execution
    execution_time_ms: float  # Wall-clock time for grading
    extraction_method: str | None  # GSM8K only: which pattern matched
```

### Pattern 6: DB Schema Extension
**Recommendation:** Use a separate `grading_details` table rather than adding columns to `experiment_runs`. Reasons:
- `experiment_runs` already has 30 columns; adding 5 more makes it unwieldy
- Grading metadata is conceptually separate from experiment execution
- Allows re-grading without touching the runs table (except pass_fail)
- One-to-one relationship with experiment_runs via run_id

```sql
CREATE TABLE IF NOT EXISTS grading_details (
    run_id TEXT PRIMARY KEY REFERENCES experiment_runs(run_id),
    fail_reason TEXT,          -- timeout, crash, memory_exceeded, syntax_error, no_output, extraction_failed, import_error
    extraction_method TEXT,    -- last_number, fraction_converted, percentage, latex_boxed, etc.
    stdout TEXT,
    stderr TEXT,
    execution_time_ms REAL,
    graded_at TEXT             -- ISO 8601 timestamp
);
```

Note: `pass_fail` stays in `experiment_runs` where it already lives. The grading_details table holds the diagnostic metadata.

### Anti-Patterns to Avoid
- **Executing LLM code in the grader process:** Never `exec()` or `eval()` untrusted code in the main process. Always use subprocess.
- **Global resource limits:** Never call `resource.setrlimit()` in the parent process. Only in `preexec_fn` of the child.
- **Trusting LLM output structure:** Never assume the LLM returns clean Python. Always strip markdown fences, handle empty responses, handle non-Python output.
- **Using `shell=True`:** Always use list-form arguments with `subprocess.run()` to avoid shell injection.
- **Regex greediness on numbers:** The number extraction must find ALL numbers and take the LAST one, not the first. GSM8K chain-of-thought includes many intermediate numbers.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Process resource limits | Custom cgroup management | `resource.setrlimit()` in `preexec_fn` | stdlib, portable across Linux, exactly what it's designed for |
| Timeout management | Manual signal/timer | `subprocess.run(timeout=N)` | Handles cleanup, raises `TimeoutExpired` cleanly |
| Temp directory lifecycle | Manual mkdir/cleanup | `tempfile.TemporaryDirectory()` context manager | Auto-cleanup even on exceptions |
| Number normalization | Custom parser | Regex cascade with float() conversion | Simple patterns cover all GSM8K formats |

**Key insight:** This phase requires zero external dependencies. Python stdlib has everything needed for subprocess sandboxing and regex extraction.

## Common Pitfalls

### Pitfall 1: RLIMIT_AS Kills the Python Interpreter Before It Starts
**What goes wrong:** Setting RLIMIT_AS too low (e.g., 256 MB) can prevent the Python interpreter itself from starting in the subprocess, since Python 3.13 needs ~50-80 MB just to initialize.
**Why it happens:** RLIMIT_AS limits total virtual address space, not resident memory. Python allocates significant virtual memory at startup.
**How to avoid:** 512 MB (as specified in CONTEXT.md) is generous enough. Test with a simple "print('hello')" to verify the limit works.
**Warning signs:** Every sandbox execution fails with a cryptic error or empty stderr.

### Pitfall 2: HumanEval check(candidate) vs MBPP Direct Asserts
**What goes wrong:** Using the same test harness assembly for both benchmarks causes all tests to fail.
**Why it happens:** HumanEval wraps assertions in `def check(candidate):` and expects `check(function_name)` to be called. MBPP uses bare `assert function_name(args) == expected`.
**How to avoid:** Detect benchmark source and use the appropriate harness builder. HumanEval: concat code + test_code + `check(entry_point)`. MBPP: concat code + test_code directly.
**Warning signs:** 100% failure rate on one benchmark but not the other.

### Pitfall 3: HumanEval METADATA Dict in Test Code
**What goes wrong:** Some HumanEval test_code fields (30 out of 67) contain a `METADATA = {...}` dict before the `check()` function. This is harmless but should not be stripped carelessly.
**Why it happens:** HumanEval dataset convention.
**How to avoid:** Leave METADATA in place -- it's valid Python and does not affect execution. Do not attempt to strip it.

### Pitfall 4: LLM Returns Markdown-Wrapped Code
**What goes wrong:** LLM output contains ````python\n...\n```` fences. If not stripped, the fences become syntax errors.
**Why it happens:** LLMs commonly wrap code in markdown.
**How to avoid:** Strip markdown fences before execution. Use the LAST code block (per CONTEXT.md decision -- LLMs often iterate).
**Warning signs:** High rate of syntax_error failures.

### Pitfall 5: GSM8K Intermediate Numbers
**What goes wrong:** Extracting the FIRST number instead of the LAST gives wrong answers because chain-of-thought contains intermediate calculations.
**Why it happens:** Naive regex finds first match.
**How to avoid:** Use `re.findall()` and take `[-1]`. Check for `\boxed{}` first as an explicit answer marker.

### Pitfall 6: subprocess.TimeoutExpired Doesn't Kill Grandchildren
**What goes wrong:** If the LLM code spawns child processes (including fork bombs), `subprocess.run(timeout=)` kills the direct child but grandchildren may persist.
**Why it happens:** Default process group behavior.
**How to avoid:** Use `start_new_session=True` in `subprocess.run()` and kill the entire process group on timeout.
```python
import os
import signal

try:
    result = subprocess.run(
        [...],
        timeout=10,
        start_new_session=True,  # New process group
        preexec_fn=_set_limits,
    )
except subprocess.TimeoutExpired as e:
    # Kill entire process group
    os.killpg(os.getpgid(e.pid), signal.SIGKILL)
    raise
```
**Note:** `start_new_session=True` and `preexec_fn` are both used -- `start_new_session` is applied first, then `preexec_fn`. However, on some Python versions `preexec_fn` and `start_new_session` cannot be combined. Alternative: set `os.setsid()` inside `preexec_fn` itself.

### Pitfall 7: Entry Point Extraction from HumanEval Prompts
**What goes wrong:** The function name extracted from the prompt doesn't match what the LLM actually defines.
**Why it happens:** The LLM might rename the function, or the prompt might have multiple `def` statements.
**How to avoid:** Extract the entry point from the PROMPT (not the LLM output). The prompt always contains exactly one function signature. Use a simple regex: `re.search(r'def (\w+)\(', prompt_text)`.

### Pitfall 8: Float Comparison Edge Cases
**What goes wrong:** `float("1,234") ` raises ValueError. `float("$42")` raises ValueError.
**Why it happens:** float() doesn't handle locale formatting or currency symbols.
**How to avoid:** Normalize BEFORE float conversion: strip commas, strip currency/unit suffixes, handle parenthetical negatives.

## Code Examples

### Code Extraction from LLM Response
```python
import re

def extract_code(response: str) -> str:
    """Extract Python code from LLM response, handling markdown fences.

    Uses the LAST code block if multiple are present (LLMs iterate).
    Falls back to the full response if no fences found.
    """
    # Find all fenced code blocks (with or without language tag)
    blocks = re.findall(r'```(?:python)?\s*\n(.*?)```', response, re.DOTALL)
    if blocks:
        return blocks[-1].strip()
    # No fences -- treat entire response as code
    return response.strip()
```

### GSM8K Number Normalization
```python
def _normalize_number(raw: str) -> float:
    """Normalize a raw number string to float.

    Handles: commas (1,234), currency ($42), units (42 meters),
    parenthetical negatives (42), fractions (3/4), percentages (50%).
    """
    s = raw.strip()

    # Handle parenthetical negative: (42) -> -42
    paren_match = re.match(r'^\((\d+\.?\d*)\)$', s)
    if paren_match:
        return -float(paren_match.group(1))

    # Handle fraction: 3/4 -> 0.75
    frac_match = re.match(r'^(-?\d+)/(\d+)$', s)
    if frac_match:
        return float(frac_match.group(1)) / float(frac_match.group(2))

    # Handle percentage: 50% -> 50 (not 0.5 -- GSM8K convention)
    if s.endswith('%'):
        s = s[:-1]

    # Strip currency and unit suffixes
    s = re.sub(r'^\$', '', s)
    s = re.sub(r'\s*(dollars?|meters?|hours?|minutes?|seconds?|kg|lbs?|miles?|feet|cm|mm|m)\s*$', '', s, flags=re.IGNORECASE)

    # Strip commas
    s = s.replace(',', '')

    return float(s.strip())
```

### CLI Pattern (Following noise_generator.py Convention)
```python
def main() -> None:
    parser = argparse.ArgumentParser(description="Grade experiment results")
    parser.add_argument("--db", default=None, help="Path to results database")
    parser.add_argument("--run-id", default=None, help="Grade a single run by ID")
    parser.add_argument("--force", action="store_true", help="Re-grade already graded runs")
    parser.add_argument("--format", choices=["summary", "json", "table"], default="summary")
    args = parser.parse_args()
    # ... implementation
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `exec()` in-process | subprocess with resource limits | Long-standing best practice | Prevents untrusted code from affecting grader |
| Manual temp file cleanup | `tempfile.TemporaryDirectory()` context manager | Python 3.2+ | Reliable cleanup even on crashes |
| Single regex for numbers | Multi-pattern cascade with normalization | GSM8K community standard | Handles real-world LLM output diversity |

**Deprecated/outdated:**
- `os.popen()`: Replaced by subprocess module long ago. Never use for code execution.
- `resource.RLIMIT_VMEM`: Not available on Linux. Use `RLIMIT_AS` instead.

## Open Questions

1. **preexec_fn + start_new_session Compatibility**
   - What we know: Both are subprocess.run() parameters. `start_new_session=True` calls `os.setsid()`. On some Python versions there may be interaction.
   - What's unclear: Whether combining them works correctly on Python 3.13.
   - Recommendation: Test during implementation. If they conflict, call `os.setsid()` inside the `preexec_fn` function instead of using `start_new_session`.

2. **RLIMIT_NPROC Scope**
   - What we know: RLIMIT_NPROC limits the number of processes for the real UID, not the process.
   - What's unclear: If other user processes are running, NPROC=10 might prevent the sandbox from starting.
   - Recommendation: Set RLIMIT_NPROC to a safe value like 50 (not 10) to avoid interference, or test empirically. The fork bomb protection is belt-and-suspenders alongside the timeout.

3. **HumanEval Entry Point Extraction Reliability**
   - What we know: The prompt_text always contains a `def function_name(` signature.
   - What's unclear: Whether we should also store entry_point in prompts.json for robustness.
   - Recommendation: Extract at runtime from prompt_text. If any prompt fails extraction, log a warning and skip. Could add entry_point field to prompts.json in a future update.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_grade_results.py -x` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GRAD-01 | HumanEval code execution with sandbox (pass case) | unit | `pytest tests/test_grade_results.py::test_humaneval_pass -x` | No -- Wave 0 |
| GRAD-01 | HumanEval code execution (fail case -- wrong output) | unit | `pytest tests/test_grade_results.py::test_humaneval_fail -x` | No -- Wave 0 |
| GRAD-01 | MBPP code execution with sandbox (pass case) | unit | `pytest tests/test_grade_results.py::test_mbpp_pass -x` | No -- Wave 0 |
| GRAD-01 | Sandbox timeout on infinite loop | unit | `pytest tests/test_grade_results.py::test_sandbox_timeout -x` | No -- Wave 0 |
| GRAD-01 | Sandbox memory limit enforcement | unit | `pytest tests/test_grade_results.py::test_sandbox_memory_limit -x` | No -- Wave 0 |
| GRAD-01 | Sandbox fork bomb protection | unit | `pytest tests/test_grade_results.py::test_sandbox_fork_bomb -x` | No -- Wave 0 |
| GRAD-01 | Markdown fence stripping from LLM output | unit | `pytest tests/test_grade_results.py::test_code_extraction -x` | No -- Wave 0 |
| GRAD-01 | Syntax error in LLM code | unit | `pytest tests/test_grade_results.py::test_syntax_error -x` | No -- Wave 0 |
| GRAD-02 | GSM8K integer extraction | unit | `pytest tests/test_grade_results.py::test_gsm8k_integer -x` | No -- Wave 0 |
| GRAD-02 | GSM8K comma-separated numbers | unit | `pytest tests/test_grade_results.py::test_gsm8k_commas -x` | No -- Wave 0 |
| GRAD-02 | GSM8K fractions and percentages | unit | `pytest tests/test_grade_results.py::test_gsm8k_fractions -x` | No -- Wave 0 |
| GRAD-02 | GSM8K LaTeX boxed answers | unit | `pytest tests/test_grade_results.py::test_gsm8k_latex -x` | No -- Wave 0 |
| GRAD-02 | GSM8K negative numbers | unit | `pytest tests/test_grade_results.py::test_gsm8k_negatives -x` | No -- Wave 0 |
| GRAD-02 | GSM8K currency and unit stripping | unit | `pytest tests/test_grade_results.py::test_gsm8k_units -x` | No -- Wave 0 |
| GRAD-02 | GSM8K empty/unparseable response | unit | `pytest tests/test_grade_results.py::test_gsm8k_extraction_failed -x` | No -- Wave 0 |
| GRAD-03 | Grading result written to SQLite pass_fail column | integration | `pytest tests/test_grade_results.py::test_db_write_pass_fail -x` | No -- Wave 0 |
| GRAD-03 | Grading metadata written to grading_details table | integration | `pytest tests/test_grade_results.py::test_db_grading_details -x` | No -- Wave 0 |
| GRAD-03 | Batch grading of all NULL pass_fail runs | integration | `pytest tests/test_grade_results.py::test_batch_grading -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_grade_results.py -x`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_grade_results.py` -- covers GRAD-01, GRAD-02, GRAD-03 (all tests above)
- [ ] Conftest updates: add `sample_run_record` fixture with `raw_output` field for grading test data

## Sources

### Primary (HIGH confidence)
- Project codebase: `src/db.py` -- existing schema, insert_run(), query_runs()
- Project codebase: `src/config.py` -- ExperimentConfig, paths
- Project codebase: `data/prompts.json` -- 200 prompts, test_code fields inspected
- Project codebase: `src/noise_generator.py` -- CLI pattern to follow
- Python 3.13 stdlib: `subprocess`, `resource`, `tempfile`, `re`, `ast` -- verified available on system
- CONTEXT.md: All locked decisions verified against codebase capabilities

### Secondary (MEDIUM confidence)
- HumanEval test conventions: `check(candidate)` pattern confirmed by inspecting 67 test_code fields in prompts.json
- MBPP test conventions: direct assert pattern confirmed by inspecting 67 test_code fields
- GSM8K "last number" convention: standard in the community, referenced in CONTEXT.md

### Tertiary (LOW confidence)
- preexec_fn + start_new_session interaction on Python 3.13: needs empirical testing during implementation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all stdlib, verified on system
- Architecture: HIGH - patterns well-understood, codebase inspected
- Pitfalls: HIGH - derived from actual data inspection (HumanEval METADATA, MBPP test format differences)

**Research date:** 2026-03-19
**Valid until:** 2026-04-19 (stable domain, no fast-moving dependencies)
