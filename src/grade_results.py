"""Grading pipeline for the Linguistic Tax research toolkit.

Provides auto-grading of LLM outputs for HumanEval/MBPP (code execution
in a subprocess sandbox) and GSM8K (regex-based numerical extraction).
Includes CLI interface for batch grading.

Code execution uses resource-limited subprocesses with RLIMIT_AS (512 MB),
RLIMIT_NPROC (50), and RLIMIT_CPU (15s) to contain infinite loops,
memory bombs, and fork bombs.
"""

import argparse
import ast
import json
import logging
import os
import re
import resource
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GradeResult:
    """Result of grading a single experimental run.

    Attributes:
        passed: True if the run passed grading.
        fail_reason: Reason code if failed; None if passed.
        stdout: Captured stdout from execution.
        stderr: Captured stderr from execution.
        execution_time_ms: Wall-clock execution time in milliseconds.
        extraction_method: GSM8K extraction method used; None for code.
        extracted_value: GSM8K extracted numerical value; None for code.
        expected_value: GSM8K canonical answer; None for code.
        extracted_raw_match: GSM8K raw matched string; None for code.
        extracted_code: Extracted code from LLM response; None for GSM8K.
    """

    passed: bool
    fail_reason: str | None
    stdout: str
    stderr: str
    execution_time_ms: float
    extraction_method: str | None
    extracted_value: float | None = None
    expected_value: float | None = None
    extracted_raw_match: str | None = None
    extracted_code: str | None = None


@dataclass
class ExtractionResult:
    """Intermediate result from GSM8K number extraction.

    Attributes:
        value: The extracted numerical value.
        method: Which extraction pattern matched.
        raw_match: The raw matched string before normalization.
    """

    value: float
    method: str
    raw_match: str


# ---------------------------------------------------------------------------
# Compiled regex patterns for GSM8K number extraction
# ---------------------------------------------------------------------------

_RE_LATEX_BOXED = re.compile(r'\\boxed\{([^}]+)\}')
_RE_COMMA_SEP = re.compile(r'-?\d{1,3}(?:,\d{3})+(?:\.\d+)?')
_RE_FRACTION = re.compile(r'-?\d+/\d+')
_RE_PERCENTAGE = re.compile(r'-?\d+\.?\d*\s*%')
_RE_PAREN_NEG = re.compile(r'\((\d+\.?\d*)\)')
_RE_DECIMAL = re.compile(r'-?\d+\.\d+')
_RE_INTEGER = re.compile(r'-?\d+')

# Unit suffixes to strip during normalization
_UNIT_PATTERN = re.compile(
    r'\s*(dollars?|meters?|hours?|minutes?|seconds?|kg|lbs?|miles?|feet|cm|mm|m)\s*$',
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Code extraction
# ---------------------------------------------------------------------------

def extract_code(response: str, expected_fn: str | None = None) -> str:
    """Extract Python code from LLM response, handling markdown fences.

    Prefers the code block containing a function definition (``def``).
    When ``expected_fn`` is provided, prefers the block defining that
    function. If multiple blocks match, uses the last one (LLMs often
    iterate). Falls back to the last block, then strips prose preamble
    and extracts code starting from the first ``def``, ``import``, or
    ``from`` statement.

    Args:
        response: Raw LLM response text.
        expected_fn: Optional expected function name to prefer when
            multiple blocks contain function definitions.

    Returns:
        Extracted code string, stripped of markdown fences.
    """
    blocks = re.findall(r'```(?:python)?\s*\n(.*?)```', response, re.DOTALL)
    if blocks:
        # Prefer blocks containing the expected function name
        if expected_fn:
            fn_blocks = [b for b in blocks if re.search(
                rf'^def {re.escape(expected_fn)}\s*\(', b, re.MULTILINE
            )]
            if fn_blocks:
                return fn_blocks[-1].strip()

        # Fall back to blocks with any function definition
        def_blocks = [b for b in blocks if re.search(r'^def \w+\(', b, re.MULTILINE)]
        if def_blocks:
            return def_blocks[-1].strip()

        return blocks[-1].strip()

    # No fences: strip prose preamble and find code start,
    # then trim trailing prose after the code ends.
    lines = response.split('\n')
    code_start = None
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith(('def ', 'import ', 'from ', 'class ')):
            code_start = i
            break

    if code_start is None:
        return response.strip()

    # Walk forward from code_start, collecting code lines.
    # Stop at a blank-line-then-prose boundary: a non-empty, non-indented
    # line that isn't valid Python syntax (e.g., "Example execution:").
    code_lines = []
    in_body = False
    for line in lines[code_start:]:
        stripped = line.lstrip()
        indent = len(line) - len(line.lstrip())

        # Indented lines or blank lines are always code
        if indent > 0 or stripped == '':
            code_lines.append(line)
            in_body = True
            continue

        # Non-indented: could be new def/class/import or prose
        if stripped.startswith(('def ', 'import ', 'from ', 'class ',
                                'return ', 'if ', 'for ', 'while ',
                                'try:', 'except ', 'with ', '#',
                                '@')):
            code_lines.append(line)
            in_body = True
            continue

        # Non-indented line that doesn't look like Python — stop
        if in_body:
            break
        code_lines.append(line)

    return '\n'.join(code_lines).strip()


# ---------------------------------------------------------------------------
# Sandbox execution
# ---------------------------------------------------------------------------

def _set_limits() -> None:
    """Set resource limits on the child subprocess.

    Called as preexec_fn in subprocess.run(). Sets:
    - New session (for process group kill on timeout)
    - RLIMIT_AS: 512 MB memory limit
    - RLIMIT_NPROC: 50 process limit (fork bomb protection)
    - RLIMIT_CPU: 15 second CPU time limit (backup timeout)
    """
    os.setsid()
    mem_limit = 512 * 1024 * 1024  # 512 MB
    resource.setrlimit(resource.RLIMIT_AS, (mem_limit, mem_limit))
    resource.setrlimit(resource.RLIMIT_NPROC, (50, 50))
    resource.setrlimit(resource.RLIMIT_CPU, (15, 15))


def _run_sandbox(code: str, timeout: float = 10.0) -> subprocess.CompletedProcess:
    """Execute code string in a sandboxed subprocess with resource limits.

    Creates a temporary directory, writes the code to a script file,
    and executes it with resource limits via preexec_fn. On timeout,
    kills the entire process group.

    Args:
        code: Python code string to execute.
        timeout: Maximum execution time in seconds.

    Returns:
        CompletedProcess with returncode, stdout, stderr.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = os.path.join(tmpdir, "solution.py")
        with open(script_path, "w") as f:
            f.write(code)

        args = [sys.executable, script_path]
        proc = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=tmpdir,
            preexec_fn=_set_limits,
        )
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
            return subprocess.CompletedProcess(
                args=args, returncode=proc.returncode,
                stdout=stdout, stderr=stderr,
            )
        except subprocess.TimeoutExpired:
            # Kill the entire process group
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError, OSError):
                pass
            proc.kill()
            stdout, stderr = proc.communicate()
            return subprocess.CompletedProcess(
                args=args, returncode=-9,
                stdout=stdout or "", stderr=stderr or "TimeoutExpired",
            )


# ---------------------------------------------------------------------------
# Harness assembly
# ---------------------------------------------------------------------------

def _build_humaneval_harness(llm_code: str, test_code: str, entry_point: str) -> str:
    """Assemble HumanEval execution script.

    Concatenates the LLM code, the test_code (which defines check(candidate)),
    and a call to check() with the actual function name.

    Args:
        llm_code: Extracted code from LLM response.
        test_code: Test assertions from prompts.json test_code field.
        entry_point: Function name from prompt (e.g., 'separate_paren_groups').

    Returns:
        Complete Python script string for execution.
    """
    return f"{llm_code}\n\n{test_code}\n\ncheck({entry_point})\n"


def _build_mbpp_harness(llm_code: str, test_code: str) -> str:
    """Assemble MBPP execution script with function name aliasing.

    Extracts the expected function name from test assertions and the
    actual function name from the LLM code. If they differ, adds an
    alias so the tests can find the function.

    Args:
        llm_code: Extracted code from LLM response.
        test_code: Direct assert statements from prompts.json.

    Returns:
        Complete Python script string for execution.
    """
    # Extract expected function name from test assertions
    expected_match = re.search(r'assert (\w+)\(', test_code)
    # Extract actual function name from LLM code (skip __init__, __str__, etc.)
    actual_match = re.search(r'^def (\w+)\(', llm_code, re.MULTILINE)
    # Skip dunder methods — find a regular function name instead
    if actual_match and actual_match.group(1).startswith("__"):
        all_defs = re.findall(r'^def (\w+)\(', llm_code, re.MULTILINE)
        non_dunder = [d for d in all_defs if not d.startswith("__")]
        if non_dunder:
            actual_match = re.search(rf'^def ({re.escape(non_dunder[0])})\(', llm_code, re.MULTILINE)
        else:
            actual_match = None

    alias = ""
    if expected_match and actual_match:
        expected_name = expected_match.group(1)
        actual_name = actual_match.group(1)
        if expected_name != actual_name:
            alias = f"\n{expected_name} = {actual_name}\n"

    return f"{llm_code}\n{alias}\n{test_code}\n"


def _extract_entry_point(prompt_text: str) -> str | None:
    """Extract function name from prompt text.

    Uses regex to find the first 'def function_name(' pattern in the
    prompt, which is the entry point the test harness will call.

    Args:
        prompt_text: The original prompt text containing a function signature.

    Returns:
        Function name string, or None if no function definition found.
    """
    match = re.search(r'def (\w+)\(', prompt_text)
    return match.group(1) if match else None


# ---------------------------------------------------------------------------
# Code grading
# ---------------------------------------------------------------------------

def grade_code(raw_output: str, prompt_record: dict) -> GradeResult:
    """Grade LLM-generated code by executing it against test assertions.

    Extracts code from the raw LLM output, builds the appropriate test
    harness (HumanEval or MBPP), and executes it in a sandboxed subprocess.

    Args:
        raw_output: Raw LLM response text.
        prompt_record: Dictionary with benchmark_source, prompt_text,
            test_code fields.

    Returns:
        GradeResult with pass/fail status and diagnostic metadata.
    """
    start = time.monotonic()

    # Empty response check
    if not raw_output or not raw_output.strip():
        elapsed = (time.monotonic() - start) * 1000
        return GradeResult(
            passed=False, fail_reason="no_output",
            stdout="", stderr="", execution_time_ms=elapsed,
            extraction_method=None,
        )

    # Determine expected function name for extraction preference
    benchmark = prompt_record["benchmark_source"]
    test_code = prompt_record.get("test_code", "")
    expected_fn: str | None = None

    if benchmark == "humaneval":
        expected_fn = _extract_entry_point(prompt_record["prompt_text"])
    elif benchmark == "mbpp":
        fn_match = re.search(r'assert (\w+)\(', test_code)
        if fn_match:
            expected_fn = fn_match.group(1)

    # Extract code from markdown fences
    code = extract_code(raw_output, expected_fn=expected_fn)

    # Optional syntax pre-check
    try:
        ast.parse(code)
    except SyntaxError:
        elapsed = (time.monotonic() - start) * 1000
        return GradeResult(
            passed=False, fail_reason="syntax_error",
            stdout="", stderr="SyntaxError in extracted code",
            execution_time_ms=elapsed, extraction_method=None,
        )

    # Build harness based on benchmark
    if benchmark == "humaneval":
        entry_point = expected_fn
        if entry_point is None:
            elapsed = (time.monotonic() - start) * 1000
            return GradeResult(
                passed=False, fail_reason="no_entry_point",
                stdout="", stderr="Could not extract entry point from prompt",
                execution_time_ms=elapsed, extraction_method=None,
            )
        harness = _build_humaneval_harness(code, test_code, entry_point)
    elif benchmark == "mbpp":
        harness = _build_mbpp_harness(code, test_code)
    else:
        elapsed = (time.monotonic() - start) * 1000
        return GradeResult(
            passed=False, fail_reason="unsupported_benchmark",
            stdout="", stderr=f"Unknown benchmark: {benchmark}",
            execution_time_ms=elapsed, extraction_method=None,
        )

    # Execute in sandbox
    result = _run_sandbox(harness)
    elapsed = (time.monotonic() - start) * 1000

    # Map results to GradeResult
    if result.returncode == 0:
        return GradeResult(
            passed=True, fail_reason=None,
            stdout=result.stdout, stderr=result.stderr,
            execution_time_ms=elapsed, extraction_method=None,
            extracted_code=code,
        )

    # Determine failure reason from stderr/returncode
    stderr = result.stderr or ""
    if result.returncode == -9 or "TimeoutExpired" in stderr:
        fail_reason = "timeout"
    elif "MemoryError" in stderr or result.returncode == -signal.SIGKILL:
        fail_reason = "memory_exceeded"
    elif "SyntaxError" in stderr:
        fail_reason = "syntax_error"
    elif "ImportError" in stderr or "ModuleNotFoundError" in stderr:
        fail_reason = "import_error"
    elif "AssertionError" in stderr:
        fail_reason = "wrong_answer"
    else:
        fail_reason = "crash"

    return GradeResult(
        passed=False, fail_reason=fail_reason,
        stdout=result.stdout, stderr=stderr,
        execution_time_ms=elapsed, extraction_method=None,
        extracted_code=code,
    )


# ---------------------------------------------------------------------------
# GSM8K number extraction and math grading
# ---------------------------------------------------------------------------

def _normalize_number(raw: str) -> float:
    """Normalize a raw number string to float.

    Handles: commas (1,234), currency ($42), units (42 meters),
    parenthetical negatives (42), fractions (3/4), percentages (50%).

    Args:
        raw: Raw number string to normalize.

    Returns:
        Normalized float value.

    Raises:
        ValueError: If the string cannot be converted to float.
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

    # Handle percentage: 50% -> 50 (GSM8K convention: keep as-is)
    if s.endswith('%'):
        s = s[:-1].strip()

    # Strip currency prefix
    s = re.sub(r'^\$', '', s)

    # Strip unit suffixes
    s = _UNIT_PATTERN.sub('', s)

    # Strip commas
    s = s.replace(',', '')

    return float(s.strip())


_RE_HASH_ANSWER = re.compile(r'####\s*(.+)')
_RE_ANSWER_IS = re.compile(
    r'(?:the\s+)?answer\s+is[:\s]+\$?(-?[\d,]+\.?\d*)',
    re.IGNORECASE,
)
_RE_ANSWER_COLON = re.compile(
    r'answer\s*:\s*\$?(-?[\d,]+\.?\d*)',
    re.IGNORECASE,
)


def _extract_number(text: str) -> ExtractionResult | None:
    """Extract the numerical answer from LLM response text.

    Uses a priority cascade to find the intended answer, avoiding
    intermediate numbers in chain-of-thought reasoning:

    1. LaTeX ``\\boxed{answer}`` — explicit answer marker
    2. ``#### answer`` — standard GSM8K answer delimiter
    3. ``Answer: N`` or ``the answer is N`` — explicit answer phrases
    4. Last number, skipping numbers inside parenthetical explanations

    Args:
        text: Raw LLM response text.

    Returns:
        ExtractionResult with value, method, and raw match; or None if
        no number found.
    """
    if not text or not text.strip():
        return None

    # 1. Check for LaTeX \boxed{answer} (highest priority)
    boxed_matches = _RE_LATEX_BOXED.findall(text)
    if boxed_matches:
        raw = boxed_matches[-1]
        try:
            value = _normalize_number(raw)
            return ExtractionResult(value=value, method="latex_boxed", raw_match=raw)
        except ValueError:
            pass

    # 2. Check for #### answer (standard GSM8K delimiter)
    hash_match = _RE_HASH_ANSWER.search(text)
    if hash_match:
        raw = hash_match.group(1).strip()
        try:
            value = _normalize_number(raw)
            return ExtractionResult(value=value, method="hash_delimiter", raw_match=raw)
        except ValueError:
            pass

    # 3. Check for "Answer: N" or "the answer is N"
    for pattern, method_name in [
        (_RE_ANSWER_COLON, "answer_colon"),
        (_RE_ANSWER_IS, "answer_is"),
    ]:
        matches = list(pattern.finditer(text))
        if matches:
            raw = matches[-1].group(1).strip()
            try:
                value = _normalize_number(raw)
                return ExtractionResult(value=value, method=method_name, raw_match=raw)
            except ValueError:
                pass

    # 4. Find all number-like patterns with their positions
    patterns = [
        (_RE_COMMA_SEP, "comma_separated"),
        (_RE_FRACTION, "fraction"),
        (_RE_PERCENTAGE, "percentage"),
        (_RE_PAREN_NEG, "paren_negative"),
        (_RE_DECIMAL, "decimal"),
        (_RE_INTEGER, "integer"),
    ]

    # (start_pos, end_pos, raw, method)
    all_matches: list[tuple[int, int, str, str]] = []

    for regex, method in patterns:
        for match in regex.finditer(text):
            raw = match.group(0)
            all_matches.append((match.start(), match.end(), raw, method))

    if not all_matches:
        return None

    # Remove matches that are fully contained within a longer match
    all_matches.sort(key=lambda x: (x[0], -(x[1] - x[0])))
    filtered: list[tuple[int, int, str, str]] = []
    for m in all_matches:
        subsumed = False
        for kept in filtered:
            if m[0] >= kept[0] and m[1] <= kept[1]:
                subsumed = True
                break
        if not subsumed:
            filtered.append(m)

    if not filtered:
        return None

    # Try to skip numbers inside parenthetical/explanatory suffixes.
    # Walk backward from the last match, skip any that sit inside
    # a parenthetical started after a prior number.
    filtered.sort(key=lambda x: x[0])

    # Find parenthetical regions: text between '(' and ')'
    paren_regions: list[tuple[int, int]] = []
    depth = 0
    paren_start = -1
    for i, ch in enumerate(text):
        if ch == '(' and depth == 0:
            paren_start = i
            depth = 1
        elif ch == '(':
            depth += 1
        elif ch == ')' and depth > 0:
            depth -= 1
            if depth == 0 and paren_start >= 0:
                paren_regions.append((paren_start, i + 1))

    def _in_parens(pos: int) -> bool:
        return any(start <= pos < end for start, end in paren_regions)

    # Take the last match NOT inside parentheses
    for start, end, raw, method in reversed(filtered):
        if not _in_parens(start):
            try:
                value = _normalize_number(raw)
                return ExtractionResult(value=value, method=method, raw_match=raw)
            except ValueError:
                continue

    # All numbers are in parens — fall back to absolute last
    _, _, raw, method = filtered[-1]
    try:
        value = _normalize_number(raw)
        return ExtractionResult(value=value, method=method, raw_match=raw)
    except ValueError:
        return None


def grade_math(raw_output: str, prompt_record: dict) -> GradeResult:
    """Grade GSM8K math answer by extracting and comparing numerical values.

    Extracts the last number from the LLM output, normalizes it,
    and compares against the canonical answer within epsilon (1e-6).

    Args:
        raw_output: Raw LLM response text.
        prompt_record: Dictionary with canonical_answer field.

    Returns:
        GradeResult with pass/fail status and extraction metadata.
    """
    start = time.monotonic()

    # Empty response check
    if not raw_output or not raw_output.strip():
        elapsed = (time.monotonic() - start) * 1000
        return GradeResult(
            passed=False, fail_reason="no_output",
            stdout="", stderr="", execution_time_ms=elapsed,
            extraction_method=None,
        )

    # Extract number
    extraction = _extract_number(raw_output)
    if extraction is None:
        elapsed = (time.monotonic() - start) * 1000
        return GradeResult(
            passed=False, fail_reason="extraction_failed",
            stdout="", stderr="No number found in output",
            execution_time_ms=elapsed, extraction_method=None,
        )

    # Parse canonical answer
    canonical = float(prompt_record["canonical_answer"])

    # Compare with epsilon
    elapsed = (time.monotonic() - start) * 1000
    passed = abs(extraction.value - canonical) < 1e-6
    return GradeResult(
        passed=passed,
        fail_reason=None if passed else "wrong_answer",
        stdout=f"Extracted: {extraction.value} (canonical: {canonical})",
        stderr="", execution_time_ms=elapsed,
        extraction_method=extraction.method,
        extracted_value=extraction.value,
        expected_value=canonical,
        extracted_raw_match=extraction.raw_match,
    )


# ---------------------------------------------------------------------------
# Routing and batch grading
# ---------------------------------------------------------------------------

def grade_run(raw_output: str, prompt_record: dict) -> GradeResult:
    """Route grading to the appropriate function based on benchmark type.

    Args:
        raw_output: Raw LLM response text.
        prompt_record: Dictionary with benchmark_source and other fields.

    Returns:
        GradeResult from the appropriate grading function.
    """
    benchmark = prompt_record["benchmark_source"]
    if benchmark in ("humaneval", "mbpp"):
        return grade_code(raw_output, prompt_record)
    elif benchmark == "gsm8k":
        return grade_math(raw_output, prompt_record)
    else:
        return GradeResult(
            passed=False, fail_reason="unsupported_benchmark",
            stdout="", stderr=f"Unknown benchmark: {benchmark}",
            execution_time_ms=0.0, extraction_method=None,
        )


def batch_grade(
    db_path: str,
    run_id: str | None = None,
    force: bool = False,
    prompts_path: str = "data/prompts.json",
) -> dict:
    """Grade experiment runs in batch, writing results to SQLite.

    Args:
        db_path: Path to the SQLite database.
        run_id: If specified, grade only this run. Otherwise grade all
            ungraded runs (or all runs if force=True).
        force: If True, re-grade already-graded runs.
        prompts_path: Path to prompts.json file.

    Returns:
        Summary dictionary with total, passed, failed, errors counts.
    """
    from src.db import init_database, query_runs, save_grade_result

    conn = init_database(db_path)

    # Load prompts
    with open(prompts_path) as f:
        prompts_list = json.load(f)
    prompts_by_id = {p["problem_id"]: p for p in prompts_list}

    # Query runs to grade
    if run_id is not None:
        runs = query_runs(conn, run_id=run_id)
    elif force:
        runs = query_runs(conn)
    else:
        # Only ungraded runs (pass_fail IS NULL)
        conn.row_factory = None  # Reset for raw query
        import sqlite3
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM experiment_runs WHERE pass_fail IS NULL"
        )
        runs = [dict(row) for row in cursor.fetchall()]

    summary = {"total": 0, "passed": 0, "failed": 0, "errors": 0}

    for run in runs:
        prompt_id = run["prompt_id"]
        prompt_record = prompts_by_id.get(prompt_id)
        if prompt_record is None:
            logger.warning("No prompt record found for %s, skipping", prompt_id)
            summary["errors"] += 1
            continue

        raw_output = run.get("raw_output", "") or ""

        try:
            result = grade_run(raw_output, prompt_record)
            save_grade_result(
                conn, run["run_id"], result.passed, result.fail_reason,
                result.stdout, result.stderr, result.execution_time_ms,
                result.extraction_method,
            )
            summary["total"] += 1
            if result.passed:
                summary["passed"] += 1
            else:
                summary["failed"] += 1
        except Exception:
            logger.exception("Error grading run %s", run["run_id"])
            summary["errors"] += 1

    conn.close()
    return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the grading CLI.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        description="Grade experiment results for the Linguistic Tax research toolkit.",
    )
    parser.add_argument(
        "--db", type=str, default=None,
        help="Path to results database (default: from ExperimentConfig)",
    )
    parser.add_argument(
        "--run-id", type=str, default=None,
        help="Grade a single run by ID",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-grade already graded runs",
    )
    parser.add_argument(
        "--format", choices=["summary", "json", "table"], default="summary",
        help="Output format (default: summary)",
    )
    parser.add_argument(
        "--prompts", type=str, default="data/prompts.json",
        help="Path to prompts JSON file (default: data/prompts.json)",
    )
    return parser


def main() -> None:
    """CLI entry point for grading experiment results."""
    parser = _build_parser()
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # Resolve DB path
    db_path = args.db
    if db_path is None:
        from src.config import ExperimentConfig
        db_path = ExperimentConfig().results_db_path

    summary = batch_grade(
        db_path=db_path,
        run_id=args.run_id,
        force=args.force,
        prompts_path=args.prompts,
    )

    if args.format == "summary":
        logger.info(
            "Graded: %d | Passed: %d | Failed: %d | Errors: %d",
            summary["total"], summary["passed"],
            summary["failed"], summary["errors"],
        )
    elif args.format == "json":
        print(json.dumps(summary, indent=2))
    elif args.format == "table":
        print(f"{'Metric':<12} {'Count':>6}")
        print("-" * 20)
        for key, val in summary.items():
            print(f"{key:<12} {val:>6}")


if __name__ == "__main__":
    main()
