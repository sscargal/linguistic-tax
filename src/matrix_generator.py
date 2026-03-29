"""Matrix generation module for the Linguistic Tax research toolkit.

Generates all prompt x noise x intervention x model x repetition combinations
for Experiment 1 (noise recovery) and Experiment 2 (compression study).
"""

import json
import logging
from typing import Any

from src.config import INTERVENTIONS, NOISE_TYPES, ExperimentConfig
from src.model_registry import registry

logger = logging.getLogger(__name__)


def extract_noise_level(noise_type: str) -> str | None:
    """Extract numeric noise level from noise type string.

    Args:
        noise_type: Noise type identifier (e.g., "type_a_5pct", "clean").

    Returns:
        Numeric level string ("5", "10", "20") or None for non-Type-A noise.
    """
    if noise_type.startswith("type_a_"):
        # Extract number from e.g. "type_a_5pct" -> "5"
        return noise_type.split("_")[2].replace("pct", "")
    return None


def generate_matrix(
    prompts_path: str,
    config: ExperimentConfig | None = None,
    models: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Generate the full experiment matrix as a list of work items.

    Creates work items for:
    - Experiment 1 (noise_recovery): Full factorial of prompts x noise x
      intervention x model x repetition
    - Experiment 2 (compression): Clean prompts x compress_only x model x
      repetition

    Args:
        prompts_path: Path to the curated prompts JSON file.
        config: Experiment configuration. Defaults to ExperimentConfig().
        models: List of model IDs to include. Defaults to registry.target_models().

    Returns:
        List of work item dictionaries, each with prompt_id, noise_type,
        noise_level, intervention, model, repetition_num, status, experiment.
    """
    if config is None:
        config = ExperimentConfig()
    if models is None:
        models = registry.target_models()

    # Load prompts to get prompt_ids
    with open(prompts_path, encoding="utf-8") as f:
        prompts = json.load(f)
    prompt_ids = [p["problem_id"] for p in prompts]
    logger.info("Loaded %d prompt IDs from %s", len(prompt_ids), prompts_path)

    matrix: list[dict[str, Any]] = []

    # Experiment 1: Noise and Recovery
    for prompt_id in prompt_ids:
        for noise_type in NOISE_TYPES:
            for intervention in INTERVENTIONS:
                for model in models:
                    for rep in range(1, config.repetitions + 1):
                        matrix.append(
                            {
                                "prompt_id": prompt_id,
                                "noise_type": noise_type,
                                "noise_level": extract_noise_level(noise_type),
                                "intervention": intervention,
                                "model": model,
                                "repetition_num": rep,
                                "status": "pending",
                                "experiment": "noise_recovery",
                            }
                        )

    exp1_count = len(matrix)
    logger.info("Experiment 1 (noise_recovery): %d work items", exp1_count)

    # Experiment 2: Compression study
    for prompt_id in prompt_ids:
        for model in models:
            for rep in range(1, config.repetitions + 1):
                matrix.append(
                    {
                        "prompt_id": prompt_id,
                        "noise_type": "clean",
                        "noise_level": None,
                        "intervention": "compress_only",
                        "model": model,
                        "repetition_num": rep,
                        "status": "pending",
                        "experiment": "compression",
                    }
                )

    exp2_count = len(matrix) - exp1_count
    logger.info("Experiment 2 (compression): %d work items", exp2_count)
    logger.info("Total matrix size: %d work items", len(matrix))

    return matrix
