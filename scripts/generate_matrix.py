"""CLI wrapper to materialize the full experiment matrix as a JSON file.

Thin wrapper around src.matrix_generator.generate_matrix().
Generates all prompt x noise x intervention x model x repetition combinations
for Experiment 1 (noise recovery) and Experiment 2 (compression study).
"""

import argparse
import json
import logging
import pathlib
import sys

# Allow imports from src/
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from src.matrix_generator import generate_matrix

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """CLI entry point for experiment matrix generation."""
    parser = argparse.ArgumentParser(
        description="Generate the full experiment matrix as JSON"
    )
    parser.add_argument(
        "--prompts",
        type=str,
        default="data/prompts.json",
        help="Path to curated prompts JSON (default: data/prompts.json)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/experiment_matrix.json",
        help="Output path for experiment matrix (default: data/experiment_matrix.json)",
    )
    parser.add_argument(
        "--models",
        type=str,
        default=None,
        help="Comma-separated model IDs (default: all configured target models)",
    )
    args = parser.parse_args()

    output_path = pathlib.Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    models = args.models.split(",") if args.models else None
    matrix = generate_matrix(prompts_path=args.prompts, models=models)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(matrix, f, indent=2, ensure_ascii=False)

    logger.info("Wrote %d work items to %s", len(matrix), output_path)


if __name__ == "__main__":
    main()
