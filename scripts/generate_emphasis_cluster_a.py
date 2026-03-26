"""Generate emphasis variants and experiment matrix for Cluster A (AQ-NH-05).

Reads key terms from data/emphasis/cluster_a_key_terms.json and the base
prompts from data/prompts.json, then produces:
- data/emphasis/cluster_a_bold.json   (20 prompts with **bold** key terms)
- data/emphasis/cluster_a_caps.json   (20 prompts with ALL CAPS key terms)
- data/emphasis/cluster_a_quotes.json (20 prompts with 'quoted' key terms)
- data/emphasis_matrix_a.json         (400-item experiment matrix)

This script is idempotent and can be re-run to regenerate from key_terms.
"""

import json
import logging
import sys
from pathlib import Path

# Add project root to path so we can import src modules
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.emphasis_converter import (
    apply_bold_emphasis,
    apply_caps_emphasis,
    apply_quotes_emphasis,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = PROJECT_ROOT / "data"
EMPHASIS_DIR = DATA_DIR / "emphasis"
PROMPTS_FILE = DATA_DIR / "prompts.json"
KEY_TERMS_FILE = EMPHASIS_DIR / "cluster_a_key_terms.json"

MODEL = "nvidia/nemotron-3-super-120b-a12b:free"
REPETITIONS = 5
EXPERIMENT_NAME = "emphasis_cluster_a"


def load_prompts() -> dict[str, str]:
    """Load base prompts from data/prompts.json, indexed by problem_id.

    Returns:
        Dictionary mapping problem_id to prompt_text.
    """
    with open(PROMPTS_FILE) as f:
        data = json.load(f)
    return {p["problem_id"]: p["prompt_text"] for p in data}


def load_key_terms() -> dict[str, dict]:
    """Load key terms from cluster_a_key_terms.json.

    Returns:
        Dictionary mapping prompt_id to key_terms metadata.
    """
    with open(KEY_TERMS_FILE) as f:
        data = json.load(f)
    return data["prompts"]


def generate_variants(
    prompts: dict[str, str],
    key_terms_map: dict[str, dict],
) -> dict[str, dict[str, str]]:
    """Generate bold, caps, and quotes variants for each prompt.

    Args:
        prompts: Mapping of prompt_id to prompt_text.
        key_terms_map: Mapping of prompt_id to key_terms metadata.

    Returns:
        Dictionary with keys 'bold', 'caps', 'quotes', each mapping
        prompt_id to converted text.
    """
    variants: dict[str, dict[str, str]] = {
        "bold": {},
        "caps": {},
        "quotes": {},
    }

    converters = {
        "bold": apply_bold_emphasis,
        "caps": apply_caps_emphasis,
        "quotes": apply_quotes_emphasis,
    }

    for prompt_id, term_info in key_terms_map.items():
        if prompt_id not in prompts:
            logger.warning("Prompt %s not found in prompts.json, skipping", prompt_id)
            continue

        base_text = prompts[prompt_id]
        terms = term_info["key_terms"]

        for variant_name, converter_fn in converters.items():
            converted = converter_fn(base_text, terms)

            # Validate: no double-wrapping
            if variant_name == "bold" and "****" in converted:
                logger.error(
                    "Double-wrapping detected in bold variant for %s", prompt_id
                )
            if variant_name == "quotes" and "''" in converted:
                logger.error(
                    "Double-wrapping detected in quotes variant for %s", prompt_id
                )

            variants[variant_name][prompt_id] = converted

    return variants


def generate_matrix(prompt_ids: list[str]) -> list[dict]:
    """Generate the 400-item experiment matrix.

    20 prompts x 4 conditions (raw + 3 emphasis) x 5 repetitions = 400 items.

    Args:
        prompt_ids: List of prompt identifiers.

    Returns:
        List of experiment matrix items.
    """
    interventions = ["raw", "emphasis_bold", "emphasis_caps", "emphasis_quotes"]
    matrix: list[dict] = []

    for prompt_id in sorted(prompt_ids):
        for intervention in interventions:
            for rep in range(1, REPETITIONS + 1):
                matrix.append({
                    "prompt_id": prompt_id,
                    "noise_type": "clean",
                    "noise_level": None,
                    "intervention": intervention,
                    "model": MODEL,
                    "repetition_num": rep,
                    "status": "pending",
                    "experiment": EXPERIMENT_NAME,
                })

    return matrix


def write_json(filepath: Path, data: object) -> None:
    """Write data to a JSON file with consistent formatting.

    Args:
        filepath: Path to the output file.
        data: JSON-serializable data.
    """
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    logger.info("Wrote %s", filepath)


def main() -> None:
    """Generate emphasis variants and experiment matrix for Cluster A."""
    # Load inputs
    prompts = load_prompts()
    key_terms_map = load_key_terms()

    logger.info(
        "Loaded %d prompts, %d key term entries",
        len(prompts),
        len(key_terms_map),
    )

    # Verify all key_terms prompts exist in prompts.json
    missing = [pid for pid in key_terms_map if pid not in prompts]
    if missing:
        logger.error("Missing prompts: %s", missing)
        sys.exit(1)

    # Generate variants
    variants = generate_variants(prompts, key_terms_map)

    # Write variant files
    for variant_name, variant_data in variants.items():
        filepath = EMPHASIS_DIR / f"cluster_a_{variant_name}.json"
        write_json(filepath, variant_data)

    # Generate and write experiment matrix
    prompt_ids = list(key_terms_map.keys())
    matrix = generate_matrix(prompt_ids)
    write_json(DATA_DIR / "emphasis_matrix_a.json", matrix)

    # Summary
    logger.info(
        "Generated 3 variant files and %d-item matrix",
        len(matrix),
    )
    for variant_name, variant_data in variants.items():
        logger.info("  %s: %d entries", variant_name, len(variant_data))


if __name__ == "__main__":
    main()
