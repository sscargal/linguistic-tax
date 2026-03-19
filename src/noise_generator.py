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
