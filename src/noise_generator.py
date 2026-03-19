"""Noise generation module for the Linguistic Tax research toolkit.

Provides Type A (character-level) and Type B (ESL syntactic) noise injection
with keyword protection, determinism guarantees, and CLI interface.

Type A noise applies weighted character mutations (adjacent key swap, omission,
doubling, transposition) at configurable error rates while protecting technical
tokens. Type B noise applies rule-based ESL transformation templates based on
L1 transfer error patterns from second-language acquisition research.

All noise generation uses isolated random.Random instances for reproducibility.
"""

import argparse
import json
import logging
import random
import re
from dataclasses import dataclass
from pathlib import Path

from config import derive_seed  # noqa: F401 — re-exported for downstream use

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# QWERTY Adjacency Map
# ---------------------------------------------------------------------------

QWERTY_ROWS: list[list[str]] = [
    list("qwertyuiop"),
    list("asdfghjkl"),
    list("zxcvbnm"),
]

# Row offsets model the physical stagger of a QWERTY keyboard
ROW_OFFSETS: list[float] = [0.0, 0.5, 1.0]


def build_adjacency_map() -> dict[str, list[str]]:
    """Build a mapping from each QWERTY key to its physically adjacent keys.

    Uses 2D grid positions with row offsets to compute neighbors within
    distance 1.5, matching the physical layout of a standard keyboard.

    Returns:
        Dictionary mapping each lowercase letter to a list of adjacent keys.
    """
    # Build position map: char -> (x, y)
    positions: dict[str, tuple[float, float]] = {}
    for row_idx, row in enumerate(QWERTY_ROWS):
        for col_idx, char in enumerate(row):
            x = col_idx + ROW_OFFSETS[row_idx]
            y = float(row_idx)
            positions[char] = (x, y)

    adj: dict[str, list[str]] = {}
    all_chars = list(positions.keys())

    for char in all_chars:
        cx, cy = positions[char]
        neighbors: list[str] = []
        for other in all_chars:
            if other == char:
                continue
            ox, oy = positions[other]
            dist = ((cx - ox) ** 2 + (cy - oy) ** 2) ** 0.5
            if dist < 1.5:
                neighbors.append(other)
        adj[char] = sorted(neighbors)

    return adj


# ---------------------------------------------------------------------------
# Keyword Protection
# ---------------------------------------------------------------------------

PYTHON_KEYWORDS: frozenset[str] = frozenset({
    "False", "None", "True", "and", "as", "assert", "async", "await",
    "break", "class", "continue", "def", "del", "elif", "else", "except",
    "finally", "for", "from", "global", "if", "import", "in", "is",
    "lambda", "nonlocal", "not", "or", "pass", "raise", "return", "try",
    "while", "with", "yield",
})

OPERATORS: frozenset[str] = frozenset({
    "+", "-", "*", "/", "=", "==", "!=", "<", ">", "<=", ">=",
    "**", "//", "%", "+=", "-=", "*=", "/=", "->", ":",
})


def identify_protected_spans(text: str, answer_type: str) -> list[tuple[int, int]]:
    """Identify character spans in text that should not be mutated.

    Protected spans include Python keywords, function/variable names,
    operators, and (for numeric answer types) numbers.

    Args:
        text: The input text to analyze.
        answer_type: Either "code" or "numeric".

    Returns:
        Sorted list of (start, end) tuples marking protected character ranges.
    """
    spans: list[tuple[int, int]] = []

    # Protect Python keywords (word boundaries)
    for kw in PYTHON_KEYWORDS:
        for match in re.finditer(r"\b" + re.escape(kw) + r"\b", text):
            spans.append((match.start(), match.end()))

    # Protect function names: def <name>
    for match in re.finditer(r"(?<=def )\w+", text):
        spans.append((match.start(), match.end()))

    # Protect callable names: <name>(
    for match in re.finditer(r"\w+(?=\()", text):
        spans.append((match.start(), match.end()))

    # Protect operators
    for op in sorted(OPERATORS, key=len, reverse=True):
        for match in re.finditer(re.escape(op), text):
            spans.append((match.start(), match.end()))

    # Protect numbers for numeric answer types
    if answer_type == "numeric":
        for match in re.finditer(r"\b\d+\.?\d*\b", text):
            spans.append((match.start(), match.end()))

    # Merge overlapping spans
    spans.sort()
    merged: list[tuple[int, int]] = []
    for start, end in spans:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))

    return merged


def _is_protected(index: int, spans: list[tuple[int, int]]) -> bool:
    """Check if a character index falls within any protected span."""
    for start, end in spans:
        if start <= index < end:
            return True
        if start > index:
            break
    return False


# ---------------------------------------------------------------------------
# Type A Mutation Functions
# ---------------------------------------------------------------------------

def apply_adjacent_key_swap(
    char: str, rng: random.Random, adj_map: dict[str, list[str]]
) -> str:
    """Replace a character with an adjacent key on the QWERTY keyboard.

    Args:
        char: The character to mutate.
        rng: Random instance for deterministic selection.
        adj_map: QWERTY adjacency map.

    Returns:
        An adjacent character, preserving case, or the original if no neighbors.
    """
    lower = char.lower()
    neighbors = adj_map.get(lower, [])
    if not neighbors:
        return char
    replacement = rng.choice(neighbors)
    return replacement.upper() if char.isupper() else replacement


def apply_char_omission(char: str) -> str:
    """Remove a character (return empty string).

    Args:
        char: The character to omit.

    Returns:
        Empty string.
    """
    return ""


def apply_char_doubling(char: str) -> str:
    """Double a character.

    Args:
        char: The character to double.

    Returns:
        The character repeated twice.
    """
    return char + char


# ---------------------------------------------------------------------------
# Type A Noise Injection
# ---------------------------------------------------------------------------

def inject_type_a_noise(
    text: str,
    error_rate: float,
    seed: int,
    answer_type: str = "code",
) -> str:
    """Inject character-level noise into text at the specified error rate.

    Applies weighted mutations (40% adjacent key swap, 25% omission,
    20% doubling, 15% transposition) to non-protected, non-whitespace
    characters. Uses an isolated Random instance for determinism.

    Args:
        text: The input text to inject noise into.
        error_rate: Fraction of mutable characters to mutate (0.0 to 1.0).
        seed: Random seed for reproducible output.
        answer_type: "code" or "numeric" -- controls number protection.

    Returns:
        The text with character-level noise injected.
    """
    if error_rate <= 0.0:
        return text

    rng = random.Random(seed)
    adj_map = build_adjacency_map()
    protected_spans = identify_protected_spans(text, answer_type)

    chars = list(text)
    result: list[str] = []
    skip_next = False

    for i, char in enumerate(chars):
        if skip_next:
            skip_next = False
            continue

        # Skip whitespace and protected characters
        if char.isspace() or _is_protected(i, protected_spans):
            result.append(char)
            continue

        # Decide whether to mutate this character
        if rng.random() >= error_rate:
            result.append(char)
            continue

        # Select mutation type by weighted probability
        roll = rng.random()
        if roll < 0.40:
            # Adjacent key swap
            result.append(apply_adjacent_key_swap(char, rng, adj_map))
        elif roll < 0.65:
            # Character omission
            result.append(apply_char_omission(char))
        elif roll < 0.85:
            # Character doubling
            result.append(apply_char_doubling(char))
        else:
            # Transposition: swap with next mutable character
            # Find next non-protected, non-whitespace char
            next_idx = None
            for j in range(i + 1, len(chars)):
                if not chars[j].isspace() and not _is_protected(j, protected_spans):
                    next_idx = j
                    break

            if next_idx is not None:
                result.append(chars[next_idx])
                # We need to put the current char where next_idx was
                chars[next_idx] = char
                skip_next = (next_idx == i + 1)
            else:
                result.append(char)

    return "".join(result)


# ---------------------------------------------------------------------------
# Type B: ESL Syntactic Noise
# ---------------------------------------------------------------------------

@dataclass
class ESLPattern:
    """A rule-based ESL transformation template.

    Each pattern represents a documented L1 transfer error from
    second-language acquisition research.

    Attributes:
        name: Short identifier for the pattern.
        l1_source: Source language ("mandarin", "spanish", "japanese").
        description: Linguistic explanation of the transfer error.
        pattern: Regex pattern to match in text.
        replacement: Replacement string (may include backreferences).
    """

    name: str
    l1_source: str
    description: str
    pattern: str
    replacement: str


# Mandarin L1 transfer patterns (5-8 entries)
# Based on documented L1 transfer phenomena: Mandarin Chinese has no article
# system, no tense morphology, optional copula, and topic-comment structure.
MANDARIN_PATTERNS: list[ESLPattern] = [
    ESLPattern(
        name="article_omission",
        l1_source="mandarin",
        description="Drop articles (a, an, the) - Mandarin has no article system",
        pattern=r"\b(a|an|the)\s+",
        replacement="",
    ),
    ESLPattern(
        name="tense_removal",
        l1_source="mandarin",
        description="Remove progressive aspect markers - Mandarin uses aspect particles, not tense",
        pattern=r"\b(was|were)\s+(\w+ing)\b",
        replacement=r"\2",
    ),
    ESLPattern(
        name="copula_omission",
        l1_source="mandarin",
        description="Drop copula (is/are) before predicates - copula often omitted in Mandarin",
        pattern=r"\b(is|are)\s+(?=\w)",
        replacement="",
    ),
    ESLPattern(
        name="preposition_simplification",
        l1_source="mandarin",
        description="Simplify prepositions - Mandarin preposition system is simpler",
        pattern=r"\binto\b",
        replacement="to",
    ),
    ESLPattern(
        name="plural_omission",
        l1_source="mandarin",
        description="Drop plural markers - Mandarin nouns do not inflect for number",
        pattern=r"\b(\w{3,})s\b(?!\s+(is|are|was|were|has))",
        replacement=r"\1",
    ),
    ESLPattern(
        name="third_person_s_omission",
        l1_source="mandarin",
        description="Drop third-person singular -s - Mandarin verbs do not conjugate",
        pattern=r"\b(sort|return|compute|find|give|take|make)s\b",
        replacement=r"\1",
    ),
]

# Spanish L1 transfer patterns (5-8 entries)
# Based on documented L1 transfer phenomena: preposition confusion from
# direct translation, double negatives, adjective-noun order, ser/estar
# distinction, and grammatical gender interference.
SPANISH_PATTERNS: list[ESLPattern] = [
    ESLPattern(
        name="preposition_confusion",
        l1_source="spanish",
        description="Confuse 'on' with 'of' - Spanish 'depender de' transfers as 'depend of'",
        pattern=r"\bdepend(?:s)?\s+on\b",
        replacement="depend of",
    ),
    ESLPattern(
        name="double_negative",
        l1_source="spanish",
        description="Use double negatives - standard in Spanish grammar",
        pattern=r"\bdon't\s+have\s+any\b",
        replacement="don't have no",
    ),
    ESLPattern(
        name="adjective_placement",
        l1_source="spanish",
        description="Place adjective after noun - Spanish adjective-noun order",
        pattern=r"\b(large|small|big|empty|sorted|new|old)\s+(\w+)\b",
        replacement=r"\2 \1",
    ),
    ESLPattern(
        name="ser_estar_confusion",
        l1_source="spanish",
        description="Confuse permanent/temporary states - ser/estar distinction",
        pattern=r"\b(is|are)\s+(happy|sad|tired|ready|equal|empty|full)\b",
        replacement=r"is being \2",
    ),
    ESLPattern(
        name="gender_article",
        l1_source="spanish",
        description="Apply grammatical gender to English nouns - interference from Spanish gender system",
        pattern=r"\bthe\s+problem\b",
        replacement="the problema",
    ),
    ESLPattern(
        name="reflexive_overuse",
        l1_source="spanish",
        description="Add reflexive where not needed - Spanish uses reflexives more broadly",
        pattern=r"\breturn\s+(the\s+)?(\w+)\b",
        replacement=r"return itself \2",
    ),
]

# Japanese L1 transfer patterns (5-8 entries)
# Based on documented L1 transfer phenomena: topic-comment structure (wa/ga),
# article omission (no article system), subject omission (pro-drop), and
# relative clause prenominal placement.
JAPANESE_PATTERNS: list[ESLPattern] = [
    ESLPattern(
        name="article_omission",
        l1_source="japanese",
        description="Drop articles - Japanese has no article system (like Mandarin)",
        pattern=r"\b(a|an|the)\s+",
        replacement="",
    ),
    ESLPattern(
        name="topic_comment",
        l1_source="japanese",
        description="Add topic marker 'As for X' - Japanese topic-comment (wa) structure",
        pattern=r"^(\w+)\s+",
        replacement=r"As for \1, ",
    ),
    ESLPattern(
        name="subject_omission",
        l1_source="japanese",
        description="Drop subject pronoun - Japanese is a pro-drop language",
        pattern=r"\b(you|it)\s+should\b",
        replacement="should",
    ),
    ESLPattern(
        name="plural_confusion",
        l1_source="japanese",
        description="Drop plural markers - Japanese nouns do not inflect for number",
        pattern=r"\b(\w{3,})s\b(?!\s+(is|are|was|were|has))",
        replacement=r"\1",
    ),
    ESLPattern(
        name="preposition_confusion",
        l1_source="japanese",
        description="Confuse prepositions - Japanese uses postpositions, causing transfer errors",
        pattern=r"\bfrom\s+(\w+)\s+to\b",
        replacement=r"to \1 from",
    ),
]

# L1 source to pattern list mapping
_L1_PATTERN_MAP: dict[str, list[ESLPattern]] = {
    "mandarin": MANDARIN_PATTERNS,
    "spanish": SPANISH_PATTERNS,
    "japanese": JAPANESE_PATTERNS,
}


def inject_type_b_noise(
    text: str,
    l1_source: str,
    seed: int | None = None,
) -> str:
    """Inject ESL syntactic noise based on L1 transfer patterns.

    Applies rule-based transformation templates that simulate common
    errors made by non-native English speakers based on their first
    language (L1) interference patterns.

    This function is deterministic by design: the same input text and
    L1 source always produce the same output. The seed parameter is
    accepted for interface consistency but does not affect the output.

    Args:
        text: The input text to transform.
        l1_source: Source language for patterns ("mandarin", "spanish",
            "japanese", or "mixed" for all combined).
        seed: Unused; accepted for interface consistency.

    Returns:
        The text with ESL syntactic noise applied.

    Raises:
        ValueError: If l1_source is not a recognized value.
    """
    if l1_source == "mixed":
        patterns = MANDARIN_PATTERNS + SPANISH_PATTERNS + JAPANESE_PATTERNS
    elif l1_source in _L1_PATTERN_MAP:
        patterns = _L1_PATTERN_MAP[l1_source]
    else:
        raise ValueError(
            f"Unknown l1_source: {l1_source!r}. "
            f"Expected one of: mandarin, spanish, japanese, mixed"
        )

    result = text
    for pattern in patterns:
        result = re.sub(pattern.pattern, pattern.replacement, result, flags=re.IGNORECASE)

    return result


# ---------------------------------------------------------------------------
# CLI Interface
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the noise generator CLI.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        description="Noise generator for the Linguistic Tax research toolkit.",
    )
    parser.add_argument(
        "--input", required=True, type=str,
        help="Path to JSON file with prompt records",
    )
    parser.add_argument(
        "--type", required=True, choices=["char", "esl"],
        help="Noise type: 'char' for Type A character-level, 'esl' for Type B ESL",
    )
    parser.add_argument(
        "--rate", type=float, default=0.10,
        help="Error rate for char type (default: 0.10)",
    )
    parser.add_argument(
        "--l1", type=str, choices=["mandarin", "spanish", "japanese", "mixed"],
        help="L1 source for ESL type",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed (default: 42)",
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Output file path (default: stdout)",
    )
    return parser


def main() -> None:
    """CLI entry point for noise generation."""
    parser = _build_parser()
    args = parser.parse_args()

    # Load input
    input_path = Path(args.input)
    with input_path.open() as f:
        prompts = json.load(f)

    logger.info("Processing %d prompts with type=%s", len(prompts), args.type)

    results = []
    for prompt in prompts:
        text = prompt["prompt_text"]
        answer_type = prompt.get("answer_type", "code")

        if args.type == "char":
            noisy = inject_type_a_noise(
                text,
                error_rate=args.rate,
                seed=args.seed,
                answer_type=answer_type,
            )
        else:
            if not args.l1:
                parser.error("--l1 is required when --type is 'esl'")
            noisy = inject_type_b_noise(text, l1_source=args.l1, seed=args.seed)

        result = dict(prompt)
        result["noisy_text"] = noisy
        results.append(result)

    # Write output
    output_json = json.dumps(results, indent=2)
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(output_json)
        logger.info("Wrote %d results to %s", len(results), output_path)
    else:
        print(output_json)


if __name__ == "__main__":
    main()
