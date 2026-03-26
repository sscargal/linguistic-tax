"""Generate Cluster B and C emphasis variants and experiment matrices.

Cluster B: Instruction-emphasis variants (20 prompts x 5 conditions x 5 reps = 500 items)
Cluster C: Sentence-initial capitalization variants (20 prompts x 2 conditions x 5 reps = 200 items)

This script is idempotent and uses deterministic prompt selection.
"""

import json
import logging
import re
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.emphasis_converter import (
    apply_instruction_caps,
    apply_instruction_bold,
    apply_mixed_emphasis,
    apply_aggressive_caps,
    lowercase_sentence_initial,
    _split_code_and_text,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROMPTS_PATH = PROJECT_ROOT / "data" / "prompts.json"
EMPHASIS_DIR = PROJECT_ROOT / "data" / "emphasis"
CLUSTER_B_VARIANTS_PATH = EMPHASIS_DIR / "cluster_b_variants.json"
CLUSTER_C_VARIANTS_PATH = EMPHASIS_DIR / "cluster_c_variants.json"
MATRIX_B_PATH = PROJECT_ROOT / "data" / "emphasis_matrix_b.json"
MATRIX_C_PATH = PROJECT_ROOT / "data" / "emphasis_matrix_c.json"

MODEL = "nvidia/nemotron-3-super-120b-a12b:free"
REPETITIONS = 5
PROMPT_COUNT = 20

# Instruction verbs/phrases for Cluster B selection
INSTRUCTION_PATTERNS = [
    "return", "should", "must", "will",
    "do not", "don't", "need to", "have to",
]


# ---------------------------------------------------------------------------
# Prompt selection helpers
# ---------------------------------------------------------------------------

def _extract_natural_language(prompt_text: str) -> str:
    """Extract natural language portions from prompt text.

    Strips fenced code blocks but preserves docstrings (indented text inside
    triple-quote blocks) since docstrings contain natural language instructions.

    Args:
        prompt_text: Full prompt text.

    Returns:
        Text with fenced code blocks removed but docstrings preserved.
    """
    # Remove fenced code blocks (```...```)
    text = re.sub(r"```[\s\S]*?```", "", prompt_text)
    # Extract docstring content (between triple quotes)
    docstrings = re.findall(r'"""([\s\S]*?)"""', text)
    docstrings += re.findall(r"'''([\s\S]*?)'''", text)
    if docstrings:
        return " ".join(docstrings)
    # Fallback: return everything that's not a code line
    # (lines starting with def, class, import, from, or pure code patterns)
    lines = text.split("\n")
    nl_lines = [
        line for line in lines
        if not re.match(r"^\s*(def |class |import |from |@|if |elif |else:|try:|except|return |raise )", line.strip())
        and line.strip()
    ]
    return " ".join(nl_lines)


def _count_instruction_verbs(prompt_text: str) -> int:
    """Count instruction verb occurrences in natural language portions of text.

    Uses docstring extraction to avoid counting 'return' in code.

    Args:
        prompt_text: Full prompt text including possible code blocks.

    Returns:
        Count of instruction verb matches in natural language text.
    """
    nl_text = _extract_natural_language(prompt_text)
    count = 0
    for pattern in INSTRUCTION_PATTERNS:
        count += len(re.findall(
            r"\b" + re.escape(pattern) + r"\b",
            nl_text,
            re.IGNORECASE,
        ))
    return count


def _count_sentences(prompt_text: str) -> int:
    """Count sentence boundaries in natural language portions of text.

    Uses regex: [.!?] followed by whitespace then uppercase letter.

    Args:
        prompt_text: Full prompt text.

    Returns:
        Count of sentence boundaries found.
    """
    nl_text = _extract_natural_language(prompt_text)
    return len(re.findall(r"[.!?]\s+[A-Z]", nl_text))


def select_cluster_b_prompts(prompts: list[dict]) -> list[dict]:
    """Select 20 prompts with most instruction verbs (HumanEval + MBPP only).

    Args:
        prompts: All prompts from prompts.json.

    Returns:
        List of 20 prompt records sorted by instruction verb count descending.
    """
    candidates = [
        p for p in prompts
        if p["benchmark_source"] in ("humaneval", "mbpp")
    ]
    scored = [
        (p, _count_instruction_verbs(p["prompt_text"]))
        for p in candidates
    ]
    # Filter: must have 2+ instruction verbs
    scored = [(p, s) for p, s in scored if s >= 2]
    # Sort by score desc, then by problem_id for determinism
    scored.sort(key=lambda x: (-x[1], x[0]["problem_id"]))
    selected = [p for p, _ in scored[:PROMPT_COUNT]]

    if len(selected) < PROMPT_COUNT:
        # Fall back to prompts with 1+ if not enough with 2+
        remaining = [
            (p, s) for p in candidates
            if (s := _count_instruction_verbs(p["prompt_text"])) >= 1
            and p not in selected
        ]
        remaining.sort(key=lambda x: (-x[1], x[0]["problem_id"]))
        for p, _ in remaining:
            if len(selected) >= PROMPT_COUNT:
                break
            selected.append(p)

    logger.info("Cluster B: selected %d prompts", len(selected))
    return selected


def select_cluster_c_prompts(prompts: list[dict]) -> list[dict]:
    """Select 20 prompts with most sentence boundaries (all benchmarks).

    Args:
        prompts: All prompts from prompts.json.

    Returns:
        List of 20 prompt records sorted by sentence count descending.
    """
    scored = [
        (p, _count_sentences(p["prompt_text"]))
        for p in prompts
    ]
    # Filter: must have 3+ sentence boundaries
    scored = [(p, s) for p, s in scored if s >= 3]
    # Sort by score desc, then by problem_id for determinism
    scored.sort(key=lambda x: (-x[1], x[0]["problem_id"]))
    selected = [p for p, _ in scored[:PROMPT_COUNT]]

    if len(selected) < PROMPT_COUNT:
        # Fall back to 2+ boundaries
        remaining = [
            (p, s) for p in prompts
            if (s := _count_sentences(p["prompt_text"])) >= 2
            and p not in selected
        ]
        remaining.sort(key=lambda x: (-x[1], x[0]["problem_id"]))
        for p, _ in remaining:
            if len(selected) >= PROMPT_COUNT:
                break
            selected.append(p)

    logger.info("Cluster C: selected %d prompts", len(selected))
    return selected


# ---------------------------------------------------------------------------
# Variant generation
# ---------------------------------------------------------------------------

def generate_cluster_b_variants(selected_prompts: list[dict]) -> dict:
    """Generate Cluster B variants using nested schema.

    Args:
        selected_prompts: List of 20 prompt records.

    Returns:
        Dict with nested schema: {metadata: {...}, prompts: {id: {intervention: text}}}
    """
    data: dict = {
        "metadata": {
            "description": "Cluster B instruction emphasis variants",
            "prompt_count": len(selected_prompts),
            "conditions": [
                "raw",
                "emphasis_instruction_caps",
                "emphasis_instruction_bold",
                "emphasis_mixed",
                "emphasis_aggressive_caps",
            ],
        },
        "prompts": {},
    }

    for p in selected_prompts:
        pid = p["problem_id"]
        text = p["prompt_text"]
        data["prompts"][pid] = {
            "emphasis_instruction_caps": apply_instruction_caps(text),
            "emphasis_instruction_bold": apply_instruction_bold(text),
            "emphasis_mixed": apply_mixed_emphasis(text),
            "emphasis_aggressive_caps": apply_aggressive_caps(text),
        }

    return data


def generate_cluster_c_variants(selected_prompts: list[dict]) -> dict:
    """Generate Cluster C variants using nested schema.

    Args:
        selected_prompts: List of 20 prompt records.

    Returns:
        Dict with nested schema: {metadata: {...}, prompts: {id: {intervention: text}}}
    """
    data: dict = {
        "metadata": {
            "description": "Cluster C sentence-initial capitalization variants",
            "prompt_count": len(selected_prompts),
            "conditions": [
                "raw",
                "emphasis_lowercase_initial",
            ],
        },
        "prompts": {},
    }

    for p in selected_prompts:
        pid = p["problem_id"]
        text = p["prompt_text"]
        data["prompts"][pid] = {
            "emphasis_lowercase_initial": lowercase_sentence_initial(text),
        }

    return data


# ---------------------------------------------------------------------------
# Matrix generation
# ---------------------------------------------------------------------------

def generate_matrix_b(selected_prompts: list[dict]) -> list[dict]:
    """Generate experiment matrix for Cluster B (500 items).

    Args:
        selected_prompts: List of 20 prompt records.

    Returns:
        List of 500 experiment matrix items.
    """
    conditions = [
        "raw",
        "emphasis_instruction_caps",
        "emphasis_instruction_bold",
        "emphasis_mixed",
        "emphasis_aggressive_caps",
    ]
    items: list[dict] = []
    for p in selected_prompts:
        for condition in conditions:
            for rep in range(1, REPETITIONS + 1):
                items.append({
                    "prompt_id": p["problem_id"],
                    "noise_type": "clean",
                    "noise_level": None,
                    "intervention": condition,
                    "model": MODEL,
                    "repetition_num": rep,
                    "status": "pending",
                    "experiment": "emphasis_cluster_b",
                })
    return items


def generate_matrix_c(selected_prompts: list[dict]) -> list[dict]:
    """Generate experiment matrix for Cluster C (200 items).

    Args:
        selected_prompts: List of 20 prompt records.

    Returns:
        List of 200 experiment matrix items.
    """
    conditions = ["raw", "emphasis_lowercase_initial"]
    items: list[dict] = []
    for p in selected_prompts:
        for condition in conditions:
            for rep in range(1, REPETITIONS + 1):
                items.append({
                    "prompt_id": p["problem_id"],
                    "noise_type": "clean",
                    "noise_level": None,
                    "intervention": condition,
                    "model": MODEL,
                    "repetition_num": rep,
                    "status": "pending",
                    "experiment": "emphasis_cluster_c",
                })
    return items


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify_code_blocks_preserved(
    original_prompts: list[dict],
    variants_data: dict,
) -> bool:
    """Verify that code blocks in variants match the originals.

    Args:
        original_prompts: List of prompt records.
        variants_data: Nested variants JSON structure.

    Returns:
        True if all code blocks are preserved, False otherwise.
    """
    prompts_by_id = {p["problem_id"]: p for p in original_prompts}
    all_ok = True
    for pid, interventions in variants_data["prompts"].items():
        original = prompts_by_id[pid]["prompt_text"]
        original_code = [
            content for content, is_code in _split_code_and_text(original)
            if is_code
        ]
        for intervention, converted in interventions.items():
            converted_code = [
                content for content, is_code in _split_code_and_text(converted)
                if is_code
            ]
            if original_code != converted_code:
                logger.error(
                    "Code blocks differ for %s / %s", pid, intervention
                )
                all_ok = False
    return all_ok


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Generate Cluster B and C variants and experiment matrices."""
    # Load prompts
    with open(PROMPTS_PATH) as f:
        prompts = json.load(f)
    logger.info("Loaded %d prompts from %s", len(prompts), PROMPTS_PATH)

    # Ensure output directory exists
    EMPHASIS_DIR.mkdir(parents=True, exist_ok=True)

    # --- Cluster B ---
    b_prompts = select_cluster_b_prompts(prompts)
    b_variants = generate_cluster_b_variants(b_prompts)
    b_matrix = generate_matrix_b(b_prompts)

    # Verify code blocks
    if not verify_code_blocks_preserved(b_prompts, b_variants):
        logger.error("Code block verification FAILED for Cluster B")
        sys.exit(1)

    with open(CLUSTER_B_VARIANTS_PATH, "w") as f:
        json.dump(b_variants, f, indent=2)
    logger.info("Wrote %s (%d prompts)", CLUSTER_B_VARIANTS_PATH, len(b_variants["prompts"]))

    with open(MATRIX_B_PATH, "w") as f:
        json.dump(b_matrix, f, indent=2)
    logger.info("Wrote %s (%d items)", MATRIX_B_PATH, len(b_matrix))

    # --- Cluster C ---
    c_prompts = select_cluster_c_prompts(prompts)
    c_variants = generate_cluster_c_variants(c_prompts)
    c_matrix = generate_matrix_c(c_prompts)

    # Verify code blocks
    if not verify_code_blocks_preserved(c_prompts, c_variants):
        logger.error("Code block verification FAILED for Cluster C")
        sys.exit(1)

    with open(CLUSTER_C_VARIANTS_PATH, "w") as f:
        json.dump(c_variants, f, indent=2)
    logger.info("Wrote %s (%d prompts)", CLUSTER_C_VARIANTS_PATH, len(c_variants["prompts"]))

    with open(MATRIX_C_PATH, "w") as f:
        json.dump(c_matrix, f, indent=2)
    logger.info("Wrote %s (%d items)", MATRIX_C_PATH, len(c_matrix))

    # --- Summary ---
    print("\n--- Generation Summary ---")
    print(f"Cluster B: {len(b_prompts)} prompts, 5 conditions, {len(b_matrix)} matrix items")
    print(f"  Prompt IDs: {[p['problem_id'] for p in b_prompts]}")
    print(f"Cluster C: {len(c_prompts)} prompts, 2 conditions, {len(c_matrix)} matrix items")
    print(f"  Prompt IDs: {[p['problem_id'] for p in c_prompts]}")

    # Sample conversions
    sample_b_pid = b_prompts[0]["problem_id"]
    sample_b = b_variants["prompts"][sample_b_pid]
    print(f"\nSample Cluster B conversion ({sample_b_pid}):")
    for k, v in sample_b.items():
        print(f"  {k}: {v[:80]}...")

    sample_c_pid = c_prompts[0]["problem_id"]
    sample_c = c_variants["prompts"][sample_c_pid]
    print(f"\nSample Cluster C conversion ({sample_c_pid}):")
    for k, v in sample_c.items():
        print(f"  {k}: {v[:80]}...")

    print("\nAll done.")


if __name__ == "__main__":
    main()
