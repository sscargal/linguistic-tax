"""Tests for the grading pipeline module.

Covers code execution sandbox (HumanEval/MBPP), code extraction,
harness assembly, GradeResult dataclass, and database integration.
Includes adversarial sandbox tests for security (infinite loops,
memory bombs, fork bombs).
"""

import sqlite3

import pytest

from src.grade_results import (
    GradeResult,
    extract_code,
    grade_code,
    _build_humaneval_harness,
    _build_mbpp_harness,
    _extract_entry_point,
    _run_sandbox,
    _set_limits,
)
from src.db import init_database, insert_run, save_grade_result


# ---------------------------------------------------------------------------
# GradeResult dataclass
# ---------------------------------------------------------------------------

class TestGradeResult:
    """Tests for the GradeResult frozen dataclass."""

    def test_graderesult_fields(self):
        """GradeResult has all required fields."""
        r = GradeResult(
            passed=True,
            fail_reason=None,
            stdout="ok",
            stderr="",
            execution_time_ms=1.5,
            extraction_method=None,
        )
        assert r.passed is True
        assert r.fail_reason is None
        assert r.stdout == "ok"
        assert r.stderr == ""
        assert r.execution_time_ms == 1.5
        assert r.extraction_method is None

    def test_graderesult_frozen(self):
        """GradeResult is immutable."""
        r = GradeResult(
            passed=True, fail_reason=None, stdout="", stderr="",
            execution_time_ms=0.0, extraction_method=None,
        )
        with pytest.raises(AttributeError):
            r.passed = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Code extraction
# ---------------------------------------------------------------------------

class TestExtractCode:
    """Tests for extract_code function."""

    def test_strips_python_fences(self):
        """Strips ```python fences and returns inner code."""
        response = "Here is the code:\n```python\ndef foo():\n    return 42\n```\n"
        assert extract_code(response) == "def foo():\n    return 42"

    def test_strips_plain_fences(self):
        """Strips ``` fences without language tag."""
        response = "```\ndef bar():\n    pass\n```"
        assert extract_code(response) == "def bar():\n    pass"

    def test_multiple_blocks_returns_last(self):
        """With multiple code blocks, returns the LAST block."""
        response = (
            "First attempt:\n```python\nv1 = 1\n```\n"
            "Better version:\n```python\nv2 = 2\n```\n"
        )
        assert extract_code(response) == "v2 = 2"

    def test_no_fences_returns_stripped(self):
        """With no fences, returns the full text stripped."""
        response = "  def baz():\n    return 0  "
        assert extract_code(response) == "def baz():\n    return 0"


# ---------------------------------------------------------------------------
# Sandbox runner
# ---------------------------------------------------------------------------

class TestRunSandbox:
    """Tests for _run_sandbox subprocess execution."""

    def test_simple_print(self):
        """_run_sandbox('print(\"hello\")') returns returncode=0 with stdout containing hello."""
        result = _run_sandbox("print('hello')")
        assert result.returncode == 0
        assert "hello" in result.stdout

    @pytest.mark.timeout(30)
    def test_sandbox_timeout(self):
        """Infinite loop times out within 15 seconds."""
        result = _run_sandbox("while True: pass", timeout=5.0)
        # Should have been killed -- non-zero return code
        assert result.returncode != 0

    @pytest.mark.timeout(30)
    def test_sandbox_memory_limit(self):
        """Memory bomb is killed by RLIMIT_AS."""
        result = _run_sandbox("x = [0] * (10**9)")
        assert result.returncode != 0

    @pytest.mark.timeout(30)
    def test_sandbox_fork_bomb(self):
        """Fork bomb does not hang, completes within 15 seconds."""
        code = "import os\nfor _ in range(100):\n    try:\n        os.fork()\n    except OSError:\n        break"
        result = _run_sandbox(code, timeout=10.0)
        # Completes without hanging (either succeeds or fails, but doesn't hang)
        assert isinstance(result.returncode, int)

    def test_syntax_error(self):
        """Syntax error returns non-zero with SyntaxError in stderr."""
        result = _run_sandbox("def foo(:\n    pass")
        assert result.returncode != 0
        assert "SyntaxError" in result.stderr


# ---------------------------------------------------------------------------
# Harness assembly
# ---------------------------------------------------------------------------

class TestHarnessAssembly:
    """Tests for HumanEval and MBPP harness builders."""

    def test_humaneval_harness(self):
        """_build_humaneval_harness concatenates code + test + check call."""
        llm_code = "def foo():\n    return 42"
        test_code = "def check(candidate):\n    assert candidate() == 42"
        entry_point = "foo"
        harness = _build_humaneval_harness(llm_code, test_code, entry_point)
        assert "def foo():" in harness
        assert "def check(candidate):" in harness
        assert "check(foo)" in harness

    def test_mbpp_harness(self):
        """_build_mbpp_harness concatenates code + test assertions."""
        llm_code = "def add(a, b):\n    return a + b"
        test_code = "assert add(1, 2) == 3"
        harness = _build_mbpp_harness(llm_code, test_code)
        assert "def add(a, b):" in harness
        assert "assert add(1, 2) == 3" in harness

    def test_extract_entry_point(self):
        """_extract_entry_point extracts function name from prompt text."""
        prompt = "def separate_paren_groups(paren_string: str) -> List[str]:"
        assert _extract_entry_point(prompt) == "separate_paren_groups"

    def test_extract_entry_point_none(self):
        """_extract_entry_point returns None when no def found."""
        assert _extract_entry_point("no function here") is None


# ---------------------------------------------------------------------------
# grade_code integration
# ---------------------------------------------------------------------------

class TestGradeCode:
    """Tests for grade_code function."""

    def test_humaneval_pass(self):
        """grade_code with correct HumanEval solution returns passed=True."""
        llm_output = (
            "def separate_paren_groups(paren_string: str):\n"
            "    result = []\n"
            "    current = ''\n"
            "    depth = 0\n"
            "    for c in paren_string:\n"
            "        if c == '(':\n"
            "            depth += 1\n"
            "            current += c\n"
            "        elif c == ')':\n"
            "            depth -= 1\n"
            "            current += c\n"
            "            if depth == 0:\n"
            "                result.append(current)\n"
            "                current = ''\n"
            "    return result\n"
        )
        prompt_record = {
            "benchmark_source": "humaneval",
            "problem_id": "HumanEval/1",
            "prompt_text": "from typing import List\n\ndef separate_paren_groups(paren_string: str) -> List[str]:",
            "test_code": (
                "\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\n"
                "def check(candidate):\n"
                "    assert candidate('(()()) ((())) () ((())()())') == [\n"
                "        '(()())', '((()))', '()', '((())()())'\n"
                "    ]\n"
                "    assert candidate('() (()) ((())) (((())))') == [\n"
                "        '()', '(())', '((()))', '(((())))'\n"
                "    ]\n"
                "    assert candidate('(()(())((())))') == [\n"
                "        '(()(())((())))'\n"
                "    ]\n"
                "    assert candidate('( ) (( )) (( )( ))') == [\n"
                "        '()', '(())', '(()())'\n"
                "    ]\n"
            ),
        }
        result = grade_code(llm_output, prompt_record)
        assert result.passed is True
        assert result.fail_reason is None

    def test_humaneval_fail(self):
        """grade_code with wrong HumanEval solution returns passed=False."""
        llm_output = "def separate_paren_groups(s):\n    return [s]\n"
        prompt_record = {
            "benchmark_source": "humaneval",
            "problem_id": "HumanEval/1",
            "prompt_text": "def separate_paren_groups(paren_string: str) -> List[str]:",
            "test_code": (
                "def check(candidate):\n"
                "    assert candidate('(()()) ((())) () ((())()())') == [\n"
                "        '(()())', '((()))', '()', '((())()())'\n"
                "    ]\n"
            ),
        }
        result = grade_code(llm_output, prompt_record)
        assert result.passed is False
        assert result.fail_reason in ("crash", "assertion_error")

    def test_mbpp_pass(self):
        """grade_code with correct MBPP solution returns passed=True."""
        llm_output = (
            "def sort_sublists(input_list):\n"
            "    return [sorted(sublist) for sublist in input_list]\n"
        )
        prompt_record = {
            "benchmark_source": "mbpp",
            "problem_id": "mbpp_104",
            "prompt_text": "Write a function to sort each sublist of strings in a given list of lists.",
            "test_code": (
                'assert sort_sublists(([" red ","green" ],["blue "," black"],[" orange","brown"]))=='
                '[[" red ", "green"], [" black", "blue "], [" orange", "brown"]]'
            ),
        }
        result = grade_code(llm_output, prompt_record)
        assert result.passed is True

    def test_empty_response(self):
        """grade_code with empty response returns fail with no_output."""
        prompt_record = {
            "benchmark_source": "humaneval",
            "problem_id": "HumanEval/1",
            "prompt_text": "def foo():",
            "test_code": "def check(candidate): assert candidate() == 1",
        }
        result = grade_code("", prompt_record)
        assert result.passed is False
        assert result.fail_reason == "no_output"

    def test_timeout_code(self):
        """grade_code with timeout code returns fail with timeout."""
        llm_output = "def foo():\n    while True: pass\n"
        prompt_record = {
            "benchmark_source": "humaneval",
            "problem_id": "HumanEval/1",
            "prompt_text": "def foo():",
            "test_code": "def check(candidate): assert candidate() == 1",
        }
        result = grade_code(llm_output, prompt_record)
        assert result.passed is False
        assert result.fail_reason == "timeout"


# ---------------------------------------------------------------------------
# DB schema extension and save_grade_result
# ---------------------------------------------------------------------------

class TestDBSchema:
    """Tests for grading_details table and save_grade_result."""

    def test_grading_details_table_created(self, tmp_db_path):
        """init_database creates grading_details table with correct columns."""
        conn = init_database(tmp_db_path)
        cursor = conn.execute("PRAGMA table_info(grading_details)")
        columns = {row[1] for row in cursor.fetchall()}
        expected = {"run_id", "fail_reason", "extraction_method", "stdout",
                    "stderr", "execution_time_ms", "graded_at"}
        assert expected == columns
        conn.close()

    def test_save_grade_result(self, tmp_db_path):
        """save_grade_result writes pass_fail to experiment_runs and metadata to grading_details."""
        conn = init_database(tmp_db_path)
        # Insert a run first
        insert_run(conn, {
            "run_id": "test-001",
            "prompt_id": "HumanEval/1",
            "benchmark": "humaneval",
            "noise_type": "clean",
            "intervention": "raw",
            "model": "test-model",
            "repetition": 1,
            "status": "completed",
        })
        # Save grade result
        save_grade_result(
            conn, "test-001", passed=True, fail_reason=None,
            stdout="ok", stderr="", execution_time_ms=5.0,
            extraction_method=None,
        )
        # Check experiment_runs pass_fail updated
        row = conn.execute(
            "SELECT pass_fail FROM experiment_runs WHERE run_id='test-001'"
        ).fetchone()
        assert row[0] == 1

        # Check grading_details inserted
        detail = conn.execute(
            "SELECT * FROM grading_details WHERE run_id='test-001'"
        ).fetchone()
        assert detail is not None
        conn.close()
