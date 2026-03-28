"""Tests for the grading pipeline module.

Covers code execution sandbox (HumanEval/MBPP), code extraction,
harness assembly, GradeResult dataclass, database integration,
GSM8K math grading with multi-pattern number extraction, batch
grading, and CLI interface.
Includes adversarial sandbox tests for security (infinite loops,
memory bombs, fork bombs).
"""

import json
import sqlite3

import pytest

from src.grade_results import (
    ExtractionResult,
    GradeResult,
    extract_code,
    grade_code,
    grade_math,
    grade_run,
    batch_grade,
    _build_humaneval_harness,
    _build_mbpp_harness,
    _build_parser,
    _extract_entry_point,
    _extract_number,
    _normalize_number,
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
        assert result.fail_reason == "wrong_answer"

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
        expected = {"run_id", "fail_reason", "extraction_method",
                    "extracted_value", "expected_value", "extracted_raw_match",
                    "extracted_code", "stdout", "stderr", "execution_time_ms",
                    "graded_at"}
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


# ---------------------------------------------------------------------------
# GSM8K number extraction
# ---------------------------------------------------------------------------

class TestNormalizeNumber:
    """Tests for _normalize_number helper."""

    def test_plain_integer(self):
        assert _normalize_number("42") == 42.0

    def test_currency_prefix(self):
        assert _normalize_number("$1,234") == 1234.0

    def test_unit_suffix(self):
        assert _normalize_number("42 dollars") == 42.0

    def test_parenthetical_negative(self):
        assert _normalize_number("(42)") == -42.0

    def test_fraction(self):
        assert _normalize_number("3/4") == 0.75

    def test_percentage(self):
        assert _normalize_number("50%") == 50.0

    def test_comma_separated(self):
        assert _normalize_number("1,234,567") == 1234567.0


class TestExtractNumber:
    """Tests for _extract_number multi-pattern extractor."""

    def test_gsm8k_integer(self):
        """Plain integer extraction via 'answer is' pattern."""
        result = _extract_number("The answer is 42")
        assert result is not None
        assert result.value == 42.0
        assert result.method == "answer_is"

    def test_gsm8k_commas(self):
        """Comma-separated number extraction."""
        result = _extract_number("Total cost is $1,234.56")
        assert result is not None
        assert result.value == 1234.56
        assert result.method == "comma_separated"

    def test_gsm8k_fractions(self):
        """Fraction extraction and conversion."""
        result = _extract_number("3/4 of the pie")
        assert result is not None
        assert result.value == 0.75
        assert result.method == "fraction"

    def test_gsm8k_percentage(self):
        """Percentage extraction."""
        result = _extract_number("50% of students")
        assert result is not None
        assert result.value == 50.0
        assert result.method == "percentage"

    def test_gsm8k_latex(self):
        r"""LaTeX \boxed extraction."""
        result = _extract_number("\\boxed{42}")
        assert result is not None
        assert result.value == 42.0
        assert result.method == "latex_boxed"

    def test_gsm8k_paren_negative(self):
        """Parenthetical negative extraction."""
        result = _extract_number("The loss was (42) dollars")
        assert result is not None
        assert result.value == -42.0
        assert result.method == "paren_negative"

    def test_gsm8k_negatives(self):
        """Negative integer extraction."""
        result = _extract_number("-17 degrees")
        assert result is not None
        assert result.value == -17.0

    def test_gsm8k_decimal(self):
        """Decimal extraction."""
        result = _extract_number("3.14 meters")
        assert result is not None
        assert result.value == 3.14
        assert result.method == "decimal"

    def test_gsm8k_chain_of_thought_last_number(self):
        """Chain of thought: extracts LAST number."""
        result = _extract_number("She calculated 10 + 20 + 12 = 42")
        assert result is not None
        assert result.value == 42.0

    def test_gsm8k_empty_string(self):
        """Empty string returns None."""
        assert _extract_number("") is None

    def test_gsm8k_no_numbers(self):
        """No numbers returns None."""
        assert _extract_number("no numbers here") is None

    def test_gsm8k_extraction_failed(self):
        """Whitespace-only returns None."""
        assert _extract_number("   ") is None

    def test_gsm8k_units(self):
        """Number with units extracts correctly."""
        result = _extract_number("The distance is 42 miles")
        assert result is not None
        assert result.value == 42.0

    def test_gsm8k_latex_with_comma(self):
        r"""LaTeX \boxed with comma-formatted number."""
        result = _extract_number("\\boxed{1,234}")
        assert result is not None
        assert result.value == 1234.0
        assert result.method == "latex_boxed"

    def test_gsm8k_negative_decimal(self):
        """Negative decimal."""
        result = _extract_number("temperature is -3.5 degrees")
        assert result is not None
        assert result.value == -3.5


# ---------------------------------------------------------------------------
# grade_math
# ---------------------------------------------------------------------------

class TestGradeMath:
    """Tests for grade_math function."""

    def test_correct_answer(self):
        """grade_math with correct answer returns passed=True."""
        prompt_record = {
            "benchmark_source": "gsm8k",
            "canonical_answer": "42",
        }
        result = grade_math("The answer is 42", prompt_record)
        assert result.passed is True
        assert result.extraction_method == "answer_is"

    def test_wrong_answer(self):
        """grade_math with wrong answer returns passed=False."""
        prompt_record = {
            "benchmark_source": "gsm8k",
            "canonical_answer": "42",
        }
        result = grade_math("The answer is 43", prompt_record)
        assert result.passed is False
        assert result.fail_reason == "wrong_answer"

    def test_empty_response(self):
        """grade_math with empty response returns no_output."""
        prompt_record = {
            "benchmark_source": "gsm8k",
            "canonical_answer": "42",
        }
        result = grade_math("", prompt_record)
        assert result.passed is False
        assert result.fail_reason == "no_output"

    def test_extraction_failed(self):
        """grade_math with no numbers returns extraction_failed."""
        prompt_record = {
            "benchmark_source": "gsm8k",
            "canonical_answer": "42",
        }
        result = grade_math("no numbers", prompt_record)
        assert result.passed is False
        assert result.fail_reason == "extraction_failed"

    def test_epsilon_comparison(self):
        """grade_math with near-equal answer passes within epsilon."""
        prompt_record = {
            "benchmark_source": "gsm8k",
            "canonical_answer": "42",
        }
        result = grade_math("answer is 42.0000001", prompt_record)
        assert result.passed is True


# ---------------------------------------------------------------------------
# grade_run router
# ---------------------------------------------------------------------------

class TestGradeRun:
    """Tests for grade_run auto-routing."""

    def test_routes_humaneval(self):
        """grade_run routes humaneval to grade_code."""
        prompt_record = {
            "benchmark_source": "humaneval",
            "prompt_text": "def foo():\n    pass",
            "test_code": "def check(candidate):\n    assert candidate() is None",
        }
        result = grade_run("def foo():\n    pass\n", prompt_record)
        assert isinstance(result, GradeResult)

    def test_routes_gsm8k(self):
        """grade_run routes gsm8k to grade_math."""
        prompt_record = {
            "benchmark_source": "gsm8k",
            "canonical_answer": "42",
        }
        result = grade_run("The answer is 42", prompt_record)
        assert result.passed is True


# ---------------------------------------------------------------------------
# Batch grading
# ---------------------------------------------------------------------------

class TestBatchGrading:
    """Tests for batch_grade function."""

    def test_batch_grading(self, tmp_db_path, tmp_path):
        """batch_grade grades all NULL pass_fail runs and writes results."""
        conn = init_database(tmp_db_path)

        # Create a prompts file with a simple GSM8K problem
        prompts = [
            {
                "benchmark_source": "gsm8k",
                "problem_id": "gsm8k_test_1",
                "prompt_text": "What is 2 + 2?",
                "canonical_answer": "4",
                "answer_type": "numeric",
                "test_code": None,
            },
        ]
        prompts_path = str(tmp_path / "prompts.json")
        with open(prompts_path, "w") as f:
            json.dump(prompts, f)

        # Insert a run with raw_output but no grade
        insert_run(conn, {
            "run_id": "batch-001",
            "prompt_id": "gsm8k_test_1",
            "benchmark": "gsm8k",
            "noise_type": "clean",
            "intervention": "raw",
            "model": "test-model",
            "repetition": 1,
            "raw_output": "The answer is 4",
            "status": "completed",
        })
        conn.close()

        # Run batch grading
        summary = batch_grade(tmp_db_path, prompts_path=prompts_path)
        assert summary["total"] == 1
        assert summary["passed"] == 1

        # Verify DB was updated
        conn = init_database(tmp_db_path)
        row = conn.execute(
            "SELECT pass_fail FROM experiment_runs WHERE run_id='batch-001'"
        ).fetchone()
        assert row[0] == 1
        conn.close()

    def test_batch_force_regrading(self, tmp_db_path, tmp_path):
        """batch_grade with force=True re-grades already-graded runs."""
        conn = init_database(tmp_db_path)

        prompts = [
            {
                "benchmark_source": "gsm8k",
                "problem_id": "gsm8k_test_1",
                "prompt_text": "What is 2 + 2?",
                "canonical_answer": "4",
                "answer_type": "numeric",
                "test_code": None,
            },
        ]
        prompts_path = str(tmp_path / "prompts.json")
        with open(prompts_path, "w") as f:
            json.dump(prompts, f)

        # Insert already-graded run
        insert_run(conn, {
            "run_id": "batch-002",
            "prompt_id": "gsm8k_test_1",
            "benchmark": "gsm8k",
            "noise_type": "clean",
            "intervention": "raw",
            "model": "test-model",
            "repetition": 1,
            "raw_output": "The answer is 4",
            "pass_fail": 0,
            "status": "completed",
        })
        conn.close()

        # Without force: should skip (already graded)
        summary = batch_grade(tmp_db_path, prompts_path=prompts_path)
        assert summary["total"] == 0

        # With force: should re-grade
        summary = batch_grade(tmp_db_path, prompts_path=prompts_path, force=True)
        assert summary["total"] == 1
        assert summary["passed"] == 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

class TestCLI:
    """Tests for CLI argument parsing."""

    def test_parser_defaults(self):
        """_build_parser produces correct defaults."""
        parser = _build_parser()
        args = parser.parse_args([])
        assert args.run_id is None
        assert args.force is False
        assert args.format == "summary"

    def test_parser_force_flag(self):
        """--force flag works."""
        parser = _build_parser()
        args = parser.parse_args(["--force"])
        assert args.force is True

    def test_parser_format_choices(self):
        """--format accepts summary, json, table."""
        parser = _build_parser()
        for fmt in ("summary", "json", "table"):
            args = parser.parse_args(["--format", fmt])
            assert args.format == fmt

    def test_parser_run_id(self):
        """--run-id accepts string."""
        parser = _build_parser()
        args = parser.parse_args(["--run-id", "test-001"])
        assert args.run_id == "test-001"
