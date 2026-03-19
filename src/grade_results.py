"""Grading pipeline for the Linguistic Tax research toolkit.

Provides auto-grading of LLM outputs for HumanEval/MBPP (code execution
in a subprocess sandbox) and GSM8K (regex-based numerical extraction).
Includes CLI interface for batch grading.

Code execution uses resource-limited subprocesses with RLIMIT_AS (512 MB),
RLIMIT_NPROC (50), and RLIMIT_CPU (15s) to contain infinite loops,
memory bombs, and fork bombs.
"""

import ast
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
    """

    passed: bool
    fail_reason: str | None
    stdout: str
    stderr: str
    execution_time_ms: float
    extraction_method: str | None


# ---------------------------------------------------------------------------
# Code extraction
# ---------------------------------------------------------------------------

def extract_code(response: str) -> str:
    """Extract Python code from LLM response, handling markdown fences.

    Uses the LAST code block if multiple are present (LLMs often iterate).
    Falls back to the full response text if no fences found.

    Args:
        response: Raw LLM response text.

    Returns:
        Extracted code string, stripped of markdown fences.
    """
    blocks = re.findall(r'```(?:python)?\s*\n(.*?)```', response, re.DOTALL)
    if blocks:
        return blocks[-1].strip()
    return response.strip()


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
    """Assemble MBPP execution script.

    Concatenates the LLM code and the direct assert statements.

    Args:
        llm_code: Extracted code from LLM response.
        test_code: Direct assert statements from prompts.json.

    Returns:
        Complete Python script string for execution.
    """
    return f"{llm_code}\n\n{test_code}\n"


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

    # Extract code from markdown fences
    code = extract_code(raw_output)

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
    benchmark = prompt_record["benchmark_source"]
    test_code = prompt_record.get("test_code", "")

    if benchmark == "humaneval":
        entry_point = _extract_entry_point(prompt_record["prompt_text"])
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
    else:
        fail_reason = "crash"

    return GradeResult(
        passed=False, fail_reason=fail_reason,
        stdout=result.stdout, stderr=stderr,
        execution_time_ms=elapsed, extraction_method=None,
    )
