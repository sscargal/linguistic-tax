"""Validation tests for the experiment matrix in data/experiment_matrix.json."""

import json
import sys
from pathlib import Path

import pytest

from src.config import INTERVENTIONS, NOISE_TYPES
from src.model_registry import registry

MATRIX_PATH = Path(__file__).parent.parent / "data" / "experiment_matrix.json"

# Valid interventions include Exp 2's "compress_only"
VALID_INTERVENTIONS = set(INTERVENTIONS) | {"compress_only"}


@pytest.fixture(scope="module")
def matrix() -> list[dict]:
    """Load the experiment matrix from data/experiment_matrix.json."""
    assert MATRIX_PATH.exists(), f"Matrix file not found: {MATRIX_PATH}"
    with open(MATRIX_PATH, encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, list), "experiment_matrix.json must be a JSON array"
    return data


def test_file_exists_and_valid_json() -> None:
    """Test that data/experiment_matrix.json exists and contains valid JSON."""
    assert MATRIX_PATH.exists(), f"Matrix file not found: {MATRIX_PATH}"
    with open(MATRIX_PATH, encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, list)


def test_matrix_is_list_of_dicts(matrix: list[dict]) -> None:
    """Test that the matrix is a list of dictionaries."""
    for i, item in enumerate(matrix):
        assert isinstance(item, dict), f"Item {i} is not a dict: {type(item)}"


def test_required_keys(matrix: list[dict]) -> None:
    """Test that each work item has all required keys."""
    required_keys = {
        "prompt_id",
        "noise_type",
        "noise_level",
        "intervention",
        "model",
        "repetition_num",
        "status",
        "experiment",
    }
    for i, item in enumerate(matrix):
        missing = required_keys - set(item.keys())
        assert not missing, f"Item {i} missing keys: {missing}"


def test_all_status_pending(matrix: list[dict]) -> None:
    """Test that all status values are 'pending'."""
    statuses = {item["status"] for item in matrix}
    assert statuses == {"pending"}, f"Non-pending statuses found: {statuses}"


def test_experiment1_count(matrix: list[dict]) -> None:
    """Test Experiment 1 has 80,000 rows (200x8x5x2x5)."""
    exp1 = [m for m in matrix if m["experiment"] == "noise_recovery"]
    assert len(exp1) == 80_000, (
        f"Expected 80,000 Exp 1 items, got {len(exp1)}"
    )


def test_experiment2_count(matrix: list[dict]) -> None:
    """Test Experiment 2 has 2,000 rows (200x1x1x2x5)."""
    exp2 = [m for m in matrix if m["experiment"] == "compression"]
    assert len(exp2) == 2_000, (
        f"Expected 2,000 Exp 2 items, got {len(exp2)}"
    )


def test_total_count(matrix: list[dict]) -> None:
    """Test total count is 82,000."""
    assert len(matrix) == 82_000, (
        f"Expected 82,000 total items, got {len(matrix)}"
    )


def test_no_duplicate_work_items(matrix: list[dict]) -> None:
    """Test no duplicate (prompt_id, noise_type, intervention, model, repetition_num) tuples."""
    seen = set()
    for item in matrix:
        key = (
            item["prompt_id"],
            item["noise_type"],
            item["intervention"],
            item["model"],
            item["repetition_num"],
        )
        assert key not in seen, f"Duplicate work item: {key}"
        seen.add(key)


def test_valid_noise_types(matrix: list[dict]) -> None:
    """Test that all noise_type values are from NOISE_TYPES."""
    valid = set(NOISE_TYPES)
    for item in matrix:
        assert item["noise_type"] in valid, (
            f"Invalid noise_type: {item['noise_type']}"
        )


def test_valid_interventions(matrix: list[dict]) -> None:
    """Test that all intervention values are valid."""
    for item in matrix:
        assert item["intervention"] in VALID_INTERVENTIONS, (
            f"Invalid intervention: {item['intervention']}"
        )


def test_valid_models(matrix: list[dict]) -> None:
    """Test that all model values are from registry target models."""
    valid = set(registry.target_models())
    for item in matrix:
        assert item["model"] in valid, f"Invalid model: {item['model']}"


def test_repetition_range(matrix: list[dict]) -> None:
    """Test that repetition_num ranges from 1 to 5."""
    reps = {item["repetition_num"] for item in matrix}
    assert reps == {1, 2, 3, 4, 5}, f"Unexpected repetition values: {reps}"


def test_compression_study_items(matrix: list[dict]) -> None:
    """Test that compression study items have correct noise and intervention."""
    exp2 = [m for m in matrix if m["experiment"] == "compression"]
    for item in exp2:
        assert item["noise_type"] == "clean", (
            f"Compression item has noise_type={item['noise_type']}"
        )
        assert item["intervention"] == "compress_only", (
            f"Compression item has intervention={item['intervention']}"
        )
