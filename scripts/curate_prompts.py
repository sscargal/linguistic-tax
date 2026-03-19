"""One-time script to curate 200 benchmark prompts from HuggingFace.

Downloads and samples prompts from HumanEval (67), MBPP sanitized (67),
and GSM8K (66) using a fixed random seed for reproducibility. Writes
curated prompts to data/prompts.json.

First run requires network access to download from HuggingFace.
Subsequent runs use the local cache (~/.cache/huggingface/datasets/).
"""

import argparse
import hashlib
import json
import logging
import random
from pathlib import Path

from datasets import load_dataset

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def curate_prompts(seed: int = 42) -> list[dict]:
    """Curate 200 benchmark prompts from HumanEval, MBPP, and GSM8K.

    Uses a fixed random seed to ensure deterministic sampling across runs.
    Returns a sorted list (by problem_id) for stable ordering.

    Args:
        seed: Random seed for reproducible sampling.

    Returns:
        List of 200 prompt dictionaries with benchmark_source, problem_id,
        prompt_text, canonical_answer, test_code, and answer_type fields.
    """
    rng = random.Random(seed)
    prompts: list[dict] = []

    # HumanEval: 164 problems, sample 67
    logger.info("Loading HumanEval dataset...")
    he = load_dataset("openai/openai_humaneval", split="test")
    he_indices = rng.sample(range(len(he)), 67)
    for idx in he_indices:
        item = he[idx]
        prompts.append(
            {
                "benchmark_source": "humaneval",
                "problem_id": item["task_id"],
                "prompt_text": item["prompt"],
                "canonical_answer": item["canonical_solution"],
                "test_code": item["test"],
                "answer_type": "code",
            }
        )
    logger.info("Sampled %d HumanEval prompts", len(he_indices))

    # MBPP sanitized: sample 67
    logger.info("Loading MBPP sanitized dataset...")
    mbpp = load_dataset("google-research-datasets/mbpp", "sanitized", split="test")
    mbpp_indices = rng.sample(range(len(mbpp)), 67)
    for idx in mbpp_indices:
        item = mbpp[idx]
        prompts.append(
            {
                "benchmark_source": "mbpp",
                "problem_id": f"mbpp_{item['task_id']}",
                "prompt_text": item["prompt"],
                "canonical_answer": item["code"],
                "test_code": "\n".join(item["test_list"]),
                "answer_type": "code",
            }
        )
    logger.info("Sampled %d MBPP prompts", len(mbpp_indices))

    # GSM8K: ~1300 test problems, sample 66
    logger.info("Loading GSM8K dataset...")
    gsm = load_dataset("openai/gsm8k", "main", split="test")
    gsm_indices = rng.sample(range(len(gsm)), 66)
    for idx in gsm_indices:
        item = gsm[idx]
        prompts.append(
            {
                "benchmark_source": "gsm8k",
                "problem_id": f"gsm8k_{idx}",
                "prompt_text": item["question"],
                "canonical_answer": item["answer"].split("####")[-1].strip(),
                "test_code": None,
                "answer_type": "numeric",
                "question_hash": hashlib.sha256(
                    item["question"].encode()
                ).hexdigest()[:16],
            }
        )
    logger.info("Sampled %d GSM8K prompts", len(gsm_indices))

    # Sort by problem_id for deterministic ordering
    prompts.sort(key=lambda p: p["problem_id"])
    logger.info("Total curated prompts: %d", len(prompts))

    return prompts


def main() -> None:
    """CLI entry point for prompt curation."""
    parser = argparse.ArgumentParser(
        description="Curate 200 benchmark prompts from HuggingFace datasets"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible sampling (default: 42)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/prompts.json",
        help="Output path for curated prompts (default: data/prompts.json)",
    )
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    prompts = curate_prompts(seed=args.seed)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(prompts, f, indent=2, ensure_ascii=False)

    logger.info("Wrote %d prompts to %s", len(prompts), output_path)


if __name__ == "__main__":
    main()
