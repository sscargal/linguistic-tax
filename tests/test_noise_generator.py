"""Tests for the noise generator module.

Covers:
- NOISE-01: Type A character-level noise at 5%, 10%, 20% error rates
- NOISE-02: Keyword protection for Python keywords, function names, operators, numbers
- NOISE-04: Determinism (same seed = identical output)
- Integration: derive_seed imported from config
"""

import sys

import pytest

sys.path.insert(0, "src")

from noise_generator import (
    build_adjacency_map,
    identify_protected_spans,
    inject_type_a_noise,
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
        """5% error rate on 200-char string should mutate ~10 chars."""
        text = "a" * 200
        result = inject_type_a_noise(text, error_rate=0.05, seed=42)
        diff_count = sum(1 for a, b in zip(text, result) if a != b) + abs(len(result) - len(text))
        assert 5 <= diff_count <= 15, f"Expected ~10 mutations, got {diff_count}"

    def test_rate_010_approximate_mutations(self) -> None:
        """10% error rate on 200-char string should mutate ~20 chars."""
        text = "a" * 200
        result = inject_type_a_noise(text, error_rate=0.10, seed=42)
        diff_count = sum(1 for a, b in zip(text, result) if a != b) + abs(len(result) - len(text))
        assert 13 <= diff_count <= 27, f"Expected ~20 mutations, got {diff_count}"

    def test_rate_020_approximate_mutations(self) -> None:
        """20% error rate on 200-char string should mutate ~40 chars."""
        text = "a" * 200
        result = inject_type_a_noise(text, error_rate=0.20, seed=42)
        diff_count = sum(1 for a, b in zip(text, result) if a != b) + abs(len(result) - len(text))
        assert 30 <= diff_count <= 50, f"Expected ~40 mutations, got {diff_count}"


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
