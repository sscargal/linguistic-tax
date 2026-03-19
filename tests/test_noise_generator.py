"""Tests for the noise generator module.

Covers:
- NOISE-01: Type A character-level noise at 5%, 10%, 20% error rates
- NOISE-02: Keyword protection for Python keywords, function names, operators, numbers
- NOISE-03: Type B ESL syntactic noise for Mandarin, Spanish, Japanese, Mixed
- NOISE-04: Determinism (same seed = identical output) for both noise types
- CLI: Command-line interface for both char and esl modes
- Integration: derive_seed imported from config
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, "src")

from noise_generator import (
    ESLPattern,
    JAPANESE_PATTERNS,
    MANDARIN_PATTERNS,
    SPANISH_PATTERNS,
    build_adjacency_map,
    identify_protected_spans,
    inject_type_a_noise,
    inject_type_b_noise,
)
from config import derive_seed


# ---------------------------------------------------------------------------
# Test strings
# ---------------------------------------------------------------------------
CODE_PROMPT = (
    'def sort_list(items):\n'
    '    """Sort the given list in ascending order and return it."""\n'
    '    return sorted(items)'
)

MATH_PROMPT = (
    "If John has 5 apples and gives 2 to Mary, "
    "how many apples does John have left?"
)


# ---------------------------------------------------------------------------
# build_adjacency_map tests
# ---------------------------------------------------------------------------
class TestBuildAdjacencyMap:
    """Tests for QWERTY adjacency map construction."""

    def test_f_neighbors(self) -> None:
        adj = build_adjacency_map()
        neighbors = adj["f"]
        for expected in ["d", "g", "r", "t", "v", "c"]:
            assert expected in neighbors, f"'{expected}' not in f neighbors: {neighbors}"

    def test_covers_all_lowercase_letters(self) -> None:
        adj = build_adjacency_map()
        for char in "abcdefghijklmnopqrstuvwxyz":
            assert char in adj, f"'{char}' missing from adjacency map"


# ---------------------------------------------------------------------------
# inject_type_a_noise tests
# ---------------------------------------------------------------------------
class TestTypeANoise:
    """Tests for Type A character-level noise injection."""

    def test_rate_zero_returns_input_unchanged(self) -> None:
        result = inject_type_a_noise(CODE_PROMPT, error_rate=0.0, seed=42)
        assert result == CODE_PROMPT

    def test_rate_005_approximate_mutations(self) -> None:
        """5% error rate on 200-char string should produce visible mutations."""
        text = "a" * 200
        result = inject_type_a_noise(text, error_rate=0.05, seed=42)
        # Count visible changes: non-'a' chars + length difference
        visible = sum(1 for c in result if c != "a") + abs(len(result) - len(text))
        assert 3 <= visible <= 15, f"Expected ~10 visible mutations, got {visible}"

    def test_rate_010_approximate_mutations(self) -> None:
        """10% error rate on 200-char string should produce visible mutations."""
        text = "a" * 200
        result = inject_type_a_noise(text, error_rate=0.10, seed=42)
        visible = sum(1 for c in result if c != "a") + abs(len(result) - len(text))
        assert 5 <= visible <= 27, f"Expected ~20 visible mutations, got {visible}"

    def test_rate_020_approximate_mutations(self) -> None:
        """20% error rate on 200-char string should produce visible mutations."""
        text = "a" * 200
        result = inject_type_a_noise(text, error_rate=0.20, seed=42)
        visible = sum(1 for c in result if c != "a") + abs(len(result) - len(text))
        assert 15 <= visible <= 50, f"Expected ~40 visible mutations, got {visible}"


# ---------------------------------------------------------------------------
# Determinism tests (NOISE-04)
# ---------------------------------------------------------------------------
class TestDeterminism:
    """Tests for noise generator determinism."""

    def test_same_seed_identical_output(self) -> None:
        r1 = inject_type_a_noise(CODE_PROMPT, error_rate=0.10, seed=42)
        r2 = inject_type_a_noise(CODE_PROMPT, error_rate=0.10, seed=42)
        assert r1 == r2, "Same seed must produce identical output"

    def test_different_seeds_different_output(self) -> None:
        r1 = inject_type_a_noise(CODE_PROMPT, error_rate=0.10, seed=42)
        r2 = inject_type_a_noise(CODE_PROMPT, error_rate=0.10, seed=99)
        assert r1 != r2, "Different seeds should produce different output"


# ---------------------------------------------------------------------------
# Keyword protection tests (NOISE-02)
# ---------------------------------------------------------------------------
class TestKeywordProtection:
    """Tests for keyword protection in Type A noise."""

    def test_preserves_python_keywords(self) -> None:
        """Python keywords def, return must survive mutation."""
        result = inject_type_a_noise(CODE_PROMPT, error_rate=0.20, seed=42)
        assert "def " in result, f"'def' keyword mutated: {result}"
        assert "return " in result, f"'return' keyword mutated: {result}"

    def test_preserves_function_names(self) -> None:
        """Function name sort_list should survive mutation."""
        result = inject_type_a_noise(CODE_PROMPT, error_rate=0.20, seed=42)
        assert "sort_list" in result, f"Function name mutated: {result}"

    def test_preserves_numbers_in_numeric_prompts(self) -> None:
        """Numbers must survive in numeric answer_type prompts."""
        result = inject_type_a_noise(MATH_PROMPT, error_rate=0.20, seed=42, answer_type="numeric")
        assert "5" in result, f"Number '5' mutated: {result}"
        assert "2" in result, f"Number '2' mutated: {result}"

    def test_preserves_operators(self) -> None:
        code_with_ops = "x = a + b - c * d / e"
        result = inject_type_a_noise(code_with_ops, error_rate=0.20, seed=42)
        for op in ["+", "-", "*", "/"]:
            assert op in result, f"Operator '{op}' mutated: {result}"


# ---------------------------------------------------------------------------
# derive_seed integration tests
# ---------------------------------------------------------------------------
class TestDeriveSeedIntegration:
    """Tests that derive_seed (from config) works correctly."""

    def test_same_args_same_result(self) -> None:
        s1 = derive_seed(42, "HumanEval/1", "type_a", "10")
        s2 = derive_seed(42, "HumanEval/1", "type_a", "10")
        assert s1 == s2

    def test_different_prompt_ids_different_result(self) -> None:
        s1 = derive_seed(42, "HumanEval/1", "type_a", "10")
        s2 = derive_seed(42, "HumanEval/2", "type_a", "10")
        assert s1 != s2


# ---------------------------------------------------------------------------
# ESLPattern dataclass tests
# ---------------------------------------------------------------------------
class TestESLPatternDataclass:
    """Tests for ESLPattern dataclass structure."""

    def test_esl_pattern_has_required_fields(self) -> None:
        p = ESLPattern(
            name="test",
            l1_source="mandarin",
            description="test pattern",
            pattern=r"\bthe\b",
            replacement="",
        )
        assert p.name == "test"
        assert p.l1_source == "mandarin"
        assert p.description == "test pattern"
        assert p.pattern == r"\bthe\b"
        assert p.replacement == ""


# ---------------------------------------------------------------------------
# ESL pattern list tests (NOISE-03)
# ---------------------------------------------------------------------------
class TestESLPatternLists:
    """Tests for ESL pattern collections."""

    def test_mandarin_patterns_count(self) -> None:
        assert 5 <= len(MANDARIN_PATTERNS) <= 8, (
            f"Expected 5-8 Mandarin patterns, got {len(MANDARIN_PATTERNS)}"
        )

    def test_mandarin_patterns_l1_source(self) -> None:
        for p in MANDARIN_PATTERNS:
            assert p.l1_source == "mandarin"

    def test_spanish_patterns_count(self) -> None:
        assert 5 <= len(SPANISH_PATTERNS) <= 8, (
            f"Expected 5-8 Spanish patterns, got {len(SPANISH_PATTERNS)}"
        )

    def test_spanish_patterns_l1_source(self) -> None:
        for p in SPANISH_PATTERNS:
            assert p.l1_source == "spanish"

    def test_japanese_patterns_count(self) -> None:
        assert 5 <= len(JAPANESE_PATTERNS) <= 8, (
            f"Expected 5-8 Japanese patterns, got {len(JAPANESE_PATTERNS)}"
        )

    def test_japanese_patterns_l1_source(self) -> None:
        for p in JAPANESE_PATTERNS:
            assert p.l1_source == "japanese"


# ---------------------------------------------------------------------------
# Type B noise injection tests (NOISE-03)
# ---------------------------------------------------------------------------
class TestTypeBNoise:
    """Tests for Type B ESL syntactic noise injection."""

    def test_mandarin_removes_articles(self) -> None:
        text = "Write a function that sorts the list"
        result = inject_type_b_noise(text, "mandarin")
        # Mandarin pattern should remove articles
        assert "a " not in result.lower().split("th")[0] or "the " not in result.lower(), (
            f"Expected article removal, got: {result}"
        )

    def test_spanish_produces_changes(self) -> None:
        text = "The function depends on the input to sort the list"
        result = inject_type_b_noise(text, "spanish")
        assert result != text, f"Spanish patterns should modify text, got unchanged: {result}"

    def test_japanese_produces_changes(self) -> None:
        text = "Write a function that sorts the list and return the result"
        result = inject_type_b_noise(text, "japanese")
        assert result != text, f"Japanese patterns should modify text, got unchanged: {result}"

    def test_mixed_applies_multiple_l1_patterns(self) -> None:
        text = "Write a function that sorts the list and return the result"
        result = inject_type_b_noise(text, "mixed")
        assert result != text, f"Mixed mode should modify text, got unchanged: {result}"

    def test_type_b_deterministic(self) -> None:
        """Type B is rule-based, so same input = same output (NOISE-04)."""
        text = "Write a function that sorts the list"
        r1 = inject_type_b_noise(text, "mandarin")
        r2 = inject_type_b_noise(text, "mandarin")
        assert r1 == r2, "Type B noise must be deterministic"


# ---------------------------------------------------------------------------
# Full determinism tests for both types (NOISE-04)
# ---------------------------------------------------------------------------
class TestFullDeterminism:
    """Comprehensive determinism verification for both noise types."""

    def test_type_a_determinism_multiple_calls(self) -> None:
        text = "Please write a function that computes the fibonacci sequence"
        results = [inject_type_a_noise(text, 0.10, 42) for _ in range(5)]
        assert all(r == results[0] for r in results), "Type A not deterministic across 5 calls"

    def test_type_b_determinism_all_l1(self) -> None:
        text = "Write a function that sorts the list and return the result"
        for l1 in ["mandarin", "spanish", "japanese", "mixed"]:
            r1 = inject_type_b_noise(text, l1)
            r2 = inject_type_b_noise(text, l1)
            assert r1 == r2, f"Type B not deterministic for l1={l1}"


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------
class TestCLI:
    """Tests for the noise generator CLI interface."""

    def test_cli_char_mode(self, tmp_path: Path) -> None:
        """CLI --type char --rate 0.10 --seed 42 processes input."""
        input_file = tmp_path / "input.json"
        output_file = tmp_path / "output.json"
        input_data = [
            {
                "prompt_id": "test_1",
                "prompt_text": "Write a function that sorts a list",
                "answer_type": "code",
            }
        ]
        input_file.write_text(json.dumps(input_data))

        result = subprocess.run(
            [
                sys.executable, "src/noise_generator.py",
                "--input", str(input_file),
                "--type", "char",
                "--rate", "0.10",
                "--seed", "42",
                "--output", str(output_file),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        output_data = json.loads(output_file.read_text())
        assert len(output_data) == 1
        assert "noisy_text" in output_data[0]

    def test_cli_esl_mode(self, tmp_path: Path) -> None:
        """CLI --type esl --l1 mandarin processes input."""
        input_file = tmp_path / "input.json"
        output_file = tmp_path / "output.json"
        input_data = [
            {
                "prompt_id": "test_1",
                "prompt_text": "Write a function that sorts the list",
                "answer_type": "code",
            }
        ]
        input_file.write_text(json.dumps(input_data))

        result = subprocess.run(
            [
                sys.executable, "src/noise_generator.py",
                "--input", str(input_file),
                "--type", "esl",
                "--l1", "mandarin",
                "--seed", "42",
                "--output", str(output_file),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        output_data = json.loads(output_file.read_text())
        assert len(output_data) == 1
        assert "noisy_text" in output_data[0]
