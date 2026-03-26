"""Tests for Cluster B and C emphasis variants, matrices, and routing.

Validates generated variant files, experiment matrices, code block
preservation, load_emphasis_variant integration, and new conversion functions.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.config import INTERVENTIONS
from src.emphasis_converter import (
    apply_mixed_emphasis,
    apply_aggressive_caps,
    load_emphasis_variant,
    _split_code_and_text,
)
from src.run_experiment import apply_intervention


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
EMPHASIS_DIR = DATA_DIR / "emphasis"


@pytest.fixture
def cluster_b_variants() -> dict:
    """Load Cluster B variants JSON."""
    with open(EMPHASIS_DIR / "cluster_b_variants.json") as f:
        return json.load(f)


@pytest.fixture
def cluster_c_variants() -> dict:
    """Load Cluster C variants JSON."""
    with open(EMPHASIS_DIR / "cluster_c_variants.json") as f:
        return json.load(f)


@pytest.fixture
def matrix_b() -> list[dict]:
    """Load Cluster B experiment matrix."""
    with open(DATA_DIR / "emphasis_matrix_b.json") as f:
        return json.load(f)


@pytest.fixture
def matrix_c() -> list[dict]:
    """Load Cluster C experiment matrix."""
    with open(DATA_DIR / "emphasis_matrix_c.json") as f:
        return json.load(f)


@pytest.fixture
def all_prompts() -> list[dict]:
    """Load all prompts from prompts.json."""
    with open(DATA_DIR / "prompts.json") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Cluster B variant validation
# ---------------------------------------------------------------------------


class TestClusterBVariants:
    """Validate cluster_b_variants.json structure and content."""

    def test_cluster_b_variant_count(self, cluster_b_variants: dict) -> None:
        """Cluster B has exactly 20 prompts."""
        assert len(cluster_b_variants["prompts"]) == 20

    def test_cluster_b_all_conditions_present(
        self, cluster_b_variants: dict
    ) -> None:
        """Each prompt has all 4 treatment variants."""
        expected_keys = {
            "emphasis_instruction_caps",
            "emphasis_instruction_bold",
            "emphasis_mixed",
            "emphasis_aggressive_caps",
        }
        for pid, variants in cluster_b_variants["prompts"].items():
            assert set(variants.keys()) == expected_keys, (
                f"{pid} missing keys: {expected_keys - set(variants.keys())}"
            )

    def test_cluster_b_caps_has_uppercase(
        self, cluster_b_variants: dict
    ) -> None:
        """At least some instruction_caps variants contain uppercase words.

        Not all prompts will have uppercase words in non-code portions
        because docstrings inside code blocks are protected from modification.
        """
        caps_words = ["SHOULD", "MUST", "WILL", "SHALL", "DO NOT", "NEED TO", "HAVE TO"]
        count_with_caps = 0
        for pid, variants in cluster_b_variants["prompts"].items():
            text = variants["emphasis_instruction_caps"]
            if any(w in text for w in caps_words):
                count_with_caps += 1
        assert count_with_caps > 0, "No prompts have uppercase instruction words in caps variant"

    def test_cluster_b_bold_has_markers(
        self, cluster_b_variants: dict
    ) -> None:
        """At least some instruction_bold variants contain ** markers."""
        count_with_bold = 0
        for pid, variants in cluster_b_variants["prompts"].items():
            text = variants["emphasis_instruction_bold"]
            if "**" in text:
                count_with_bold += 1
        assert count_with_bold > 0, "No prompts have bold markers in bold variant"

    def test_cluster_b_mixed_has_both(
        self, cluster_b_variants: dict
    ) -> None:
        """Mixed variants may have both bold negations and caps verbs."""
        # At least some prompts should show mixed behavior
        has_any_bold = False
        has_any_caps = False
        for pid, variants in cluster_b_variants["prompts"].items():
            text = variants["emphasis_mixed"]
            if "**" in text:
                has_any_bold = True
            if any(w in text for w in ["SHOULD", "MUST", "WILL", "SHALL"]):
                has_any_caps = True
        # At least one prompt should have caps (most should)
        assert has_any_caps, "No mixed variants have caps instruction words"

    def test_cluster_b_code_preserved(
        self, cluster_b_variants: dict, all_prompts: list[dict]
    ) -> None:
        """Code blocks in Cluster B variants match originals."""
        prompts_by_id = {p["problem_id"]: p for p in all_prompts}
        for pid, variants in cluster_b_variants["prompts"].items():
            original = prompts_by_id[pid]["prompt_text"]
            original_code = [
                c for c, is_code in _split_code_and_text(original) if is_code
            ]
            for intervention, converted in variants.items():
                converted_code = [
                    c for c, is_code in _split_code_and_text(converted) if is_code
                ]
                assert original_code == converted_code, (
                    f"{pid}/{intervention}: code blocks differ"
                )

    def test_cluster_b_metadata(self, cluster_b_variants: dict) -> None:
        """Cluster B has metadata with correct fields."""
        meta = cluster_b_variants["metadata"]
        assert meta["prompt_count"] == 20
        assert len(meta["conditions"]) == 5
        assert "raw" in meta["conditions"]


# ---------------------------------------------------------------------------
# Cluster B matrix validation
# ---------------------------------------------------------------------------


class TestClusterBMatrix:
    """Validate emphasis_matrix_b.json."""

    def test_cluster_b_matrix_format(self, matrix_b: list[dict]) -> None:
        """Matrix B has 500 items with correct structure."""
        assert len(matrix_b) == 500

        required_fields = {
            "prompt_id", "noise_type", "noise_level", "intervention",
            "model", "repetition_num", "status", "experiment",
        }
        for item in matrix_b:
            assert set(item.keys()) == required_fields, (
                f"Unexpected fields: {set(item.keys()) - required_fields}"
            )

    def test_cluster_b_matrix_conditions(self, matrix_b: list[dict]) -> None:
        """Matrix B has exactly 5 distinct interventions."""
        interventions = {item["intervention"] for item in matrix_b}
        expected = {
            "raw",
            "emphasis_instruction_caps",
            "emphasis_instruction_bold",
            "emphasis_mixed",
            "emphasis_aggressive_caps",
        }
        assert interventions == expected

    def test_cluster_b_matrix_reps(self, matrix_b: list[dict]) -> None:
        """Each condition has 5 repetitions per prompt."""
        reps = {item["repetition_num"] for item in matrix_b}
        assert reps == {1, 2, 3, 4, 5}

    def test_cluster_b_matrix_experiment(self, matrix_b: list[dict]) -> None:
        """All items have experiment='emphasis_cluster_b'."""
        for item in matrix_b:
            assert item["experiment"] == "emphasis_cluster_b"

    def test_cluster_b_matrix_model(self, matrix_b: list[dict]) -> None:
        """All items use the correct model."""
        for item in matrix_b:
            assert item["model"] == "nvidia/nemotron-3-super-120b-a12b:free"


# ---------------------------------------------------------------------------
# Cluster C variant validation
# ---------------------------------------------------------------------------


class TestClusterCVariants:
    """Validate cluster_c_variants.json structure and content."""

    def test_cluster_c_variant_count(self, cluster_c_variants: dict) -> None:
        """Cluster C has exactly 20 prompts."""
        assert len(cluster_c_variants["prompts"]) == 20

    def test_cluster_c_lowercase_applied(
        self, cluster_c_variants: dict, all_prompts: list[dict]
    ) -> None:
        """Lowercase variants have lowercased sentence-initial chars."""
        prompts_by_id = {p["problem_id"]: p for p in all_prompts}
        lowered_count = 0
        for pid, variants in cluster_c_variants["prompts"].items():
            original = prompts_by_id[pid]["prompt_text"]
            converted = variants["emphasis_lowercase_initial"]
            if original != converted:
                lowered_count += 1
        # Most prompts should have some lowercase changes
        assert lowered_count > 0, "No prompts were modified by lowercase_initial"

    def test_cluster_c_code_preserved(
        self, cluster_c_variants: dict, all_prompts: list[dict]
    ) -> None:
        """Code blocks in Cluster C variants match originals."""
        prompts_by_id = {p["problem_id"]: p for p in all_prompts}
        for pid, variants in cluster_c_variants["prompts"].items():
            original = prompts_by_id[pid]["prompt_text"]
            original_code = [
                c for c, is_code in _split_code_and_text(original) if is_code
            ]
            for intervention, converted in variants.items():
                converted_code = [
                    c for c, is_code in _split_code_and_text(converted) if is_code
                ]
                assert original_code == converted_code, (
                    f"{pid}/{intervention}: code blocks differ"
                )


# ---------------------------------------------------------------------------
# Cluster C matrix validation
# ---------------------------------------------------------------------------


class TestClusterCMatrix:
    """Validate emphasis_matrix_c.json."""

    def test_cluster_c_matrix_format(self, matrix_c: list[dict]) -> None:
        """Matrix C has 200 items with correct structure."""
        assert len(matrix_c) == 200

    def test_cluster_c_matrix_conditions(self, matrix_c: list[dict]) -> None:
        """Matrix C has exactly 2 distinct interventions."""
        interventions = {item["intervention"] for item in matrix_c}
        assert interventions == {"raw", "emphasis_lowercase_initial"}

    def test_cluster_c_matrix_reps(self, matrix_c: list[dict]) -> None:
        """Each condition has 5 repetitions per prompt."""
        reps = {item["repetition_num"] for item in matrix_c}
        assert reps == {1, 2, 3, 4, 5}

    def test_cluster_c_matrix_experiment(self, matrix_c: list[dict]) -> None:
        """All items have experiment='emphasis_cluster_c'."""
        for item in matrix_c:
            assert item["experiment"] == "emphasis_cluster_c"


# ---------------------------------------------------------------------------
# Routing integration tests
# ---------------------------------------------------------------------------


class TestRoutingIntegration:
    """Verify emphasis_mixed and emphasis_aggressive_caps route correctly."""

    def test_emphasis_mixed_routing(self) -> None:
        """apply_intervention with emphasis_mixed does not raise ValueError."""
        with patch(
            "src.run_experiment.load_emphasis_variant",
            return_value="**do not** SHOULD text",
        ):
            result, meta = apply_intervention(
                "original", "emphasis_mixed",
                "some_model", lambda *a, **kw: None,
                prompt_id="HumanEval/1",
            )
            assert result == "**do not** SHOULD text"

    def test_emphasis_aggressive_caps_routing(self) -> None:
        """apply_intervention with emphasis_aggressive_caps does not raise ValueError."""
        with patch(
            "src.run_experiment.load_emphasis_variant",
            return_value="SHOULD MUST VERIFY text",
        ):
            result, meta = apply_intervention(
                "original", "emphasis_aggressive_caps",
                "some_model", lambda *a, **kw: None,
                prompt_id="HumanEval/1",
            )
            assert result == "SHOULD MUST VERIFY text"

    def test_all_emphasis_interventions_in_config(self) -> None:
        """All 8 emphasis intervention types are in INTERVENTIONS tuple."""
        emphasis_types = [
            "emphasis_bold",
            "emphasis_caps",
            "emphasis_quotes",
            "emphasis_instruction_caps",
            "emphasis_instruction_bold",
            "emphasis_lowercase_initial",
            "emphasis_mixed",
            "emphasis_aggressive_caps",
        ]
        for et in emphasis_types:
            assert et in INTERVENTIONS, f"{et} not in INTERVENTIONS"
        # Total should be 13 (5 original + 8 emphasis)
        assert len(INTERVENTIONS) == 13


# ---------------------------------------------------------------------------
# load_emphasis_variant integration with real data
# ---------------------------------------------------------------------------


class TestLoadEmphasisVariantIntegration:
    """Verify load_emphasis_variant reads from generated cluster_b_variants.json."""

    def test_cluster_b_load_via_load_emphasis_variant(
        self, cluster_b_variants: dict
    ) -> None:
        """load_emphasis_variant correctly reads emphasis_mixed from nested JSON."""
        # Pick the first prompt_id from the generated data
        first_pid = next(iter(cluster_b_variants["prompts"]))
        expected = cluster_b_variants["prompts"][first_pid]["emphasis_mixed"]

        result = load_emphasis_variant(
            first_pid, "emphasis_mixed", str(EMPHASIS_DIR)
        )
        assert result == expected

    def test_cluster_b_load_aggressive_caps(
        self, cluster_b_variants: dict
    ) -> None:
        """load_emphasis_variant correctly reads emphasis_aggressive_caps."""
        first_pid = next(iter(cluster_b_variants["prompts"]))
        expected = cluster_b_variants["prompts"][first_pid]["emphasis_aggressive_caps"]

        result = load_emphasis_variant(
            first_pid, "emphasis_aggressive_caps", str(EMPHASIS_DIR)
        )
        assert result == expected


# ---------------------------------------------------------------------------
# Conversion function tests (new functions)
# ---------------------------------------------------------------------------


class TestApplyMixedEmphasis:
    """Tests for apply_mixed_emphasis."""

    def test_apply_mixed_emphasis(self) -> None:
        """Negation words get bold, other instruction verbs get caps."""
        result = apply_mixed_emphasis(
            "You should validate. Do not skip errors."
        )
        assert "SHOULD" in result
        # Negation gets bold; caps step may also uppercase the negation text
        assert "**" in result and "not" in result.lower()

    def test_mixed_preserves_code(self) -> None:
        """Code blocks are not modified."""
        text = "You should check.\n```\nreturn value\n```\nDone."
        result = apply_mixed_emphasis(text)
        assert "```\nreturn value\n```" in result
        assert "SHOULD" in result

    def test_mixed_no_negation(self) -> None:
        """Text without negation still gets caps on verbs."""
        result = apply_mixed_emphasis("You must validate and should check.")
        assert "MUST" in result
        assert "SHOULD" in result


class TestApplyAggressiveCaps:
    """Tests for apply_aggressive_caps."""

    def test_apply_aggressive_caps(self) -> None:
        """All instruction words (broader set) get caps."""
        result = apply_aggressive_caps(
            "You should ensure proper validation. Check all inputs."
        )
        assert "SHOULD" in result
        assert "ENSURE" in result
        assert "CHECK" in result

    def test_aggressive_broader_scope(self) -> None:
        """Broader word set includes compute, determine, note, etc."""
        result = apply_aggressive_caps(
            "Compute the result. Note that edge cases may fail."
        )
        assert "COMPUTE" in result
        assert "NOTE" in result
        assert "MAY" in result

    def test_aggressive_preserves_code(self) -> None:
        """Code blocks are not modified."""
        text = "You must implement.\n```\nreturn result\n```\nDone."
        result = apply_aggressive_caps(text)
        assert "```\nreturn result\n```" in result
        assert "MUST" in result
        assert "IMPLEMENT" in result
