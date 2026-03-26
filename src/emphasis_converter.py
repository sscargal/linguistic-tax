"""Emphasis converter module for the Linguistic Tax research toolkit.

Provides conversion functions for emphasis experiments (Phase 22):
- Cluster A: Key-term emphasis (bold, CAPS, quotes)
- Cluster B: Instruction-word emphasis (caps, bold)
- Cluster C: Lowercase sentence-initial
- Cache loader for pre-computed emphasis variants (flat + nested JSON)

All functions protect code blocks (fenced and indented) from modification.
"""

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Code block protection
# ---------------------------------------------------------------------------

_FENCED_CODE_RE = re.compile(r"(```[\s\S]*?```)", re.MULTILINE)
_INDENTED_LINE_RE = re.compile(r"^(    .*)$", re.MULTILINE)


def _split_code_and_text(text: str) -> list[tuple[str, bool]]:
    """Split text into segments of (content, is_code) tuples.

    Code blocks are identified by:
    - Triple-backtick fenced blocks
    - Lines indented with 4+ spaces

    Args:
        text: The input text to split.

    Returns:
        List of (content, is_code) tuples preserving original order.
    """
    # First, identify all code regions by character offset
    code_spans: list[tuple[int, int]] = []

    for m in _FENCED_CODE_RE.finditer(text):
        code_spans.append((m.start(), m.end()))

    for m in _INDENTED_LINE_RE.finditer(text):
        # Only mark as code if not already inside a fenced block
        start, end = m.start(), m.end()
        inside_fenced = any(cs <= start and end <= ce for cs, ce in code_spans)
        if not inside_fenced:
            code_spans.append((start, end))

    if not code_spans:
        return [(text, False)]

    # Sort spans by start position
    code_spans.sort()

    # Build segments
    segments: list[tuple[str, bool]] = []
    pos = 0
    for cs, ce in code_spans:
        if cs > pos:
            segments.append((text[pos:cs], False))
        segments.append((text[cs:ce], True))
        pos = ce
    if pos < len(text):
        segments.append((text[pos:], False))

    return segments


def _apply_to_text_only(
    text: str, transform: "callable"  # noqa: F821
) -> str:
    """Apply a transform function only to non-code segments.

    Args:
        text: The input text.
        transform: A function str -> str to apply to text segments.

    Returns:
        Text with transform applied only to non-code segments.
    """
    segments = _split_code_and_text(text)
    parts: list[str] = []
    for content, is_code in segments:
        if is_code:
            parts.append(content)
        else:
            parts.append(transform(content))
    return "".join(parts)


# ---------------------------------------------------------------------------
# Cluster A: Key-term emphasis
# ---------------------------------------------------------------------------


def apply_bold_emphasis(text: str, key_terms: list[str]) -> str:
    """Wrap key terms in **bold** markdown emphasis.

    Terms are sorted by length (longest first) to prevent partial matches.
    Uses sentinel replacement to avoid double-matching.

    Args:
        text: The input prompt text.
        key_terms: List of terms to emphasize.

    Returns:
        Text with key terms wrapped in **bold**.
    """
    if not key_terms:
        return text

    def transform(segment: str) -> str:
        return _replace_terms(segment, key_terms, lambda t: f"**{t}**")

    return _apply_to_text_only(text, transform)


def apply_caps_emphasis(text: str, key_terms: list[str]) -> str:
    """Convert key terms to ALL CAPS.

    Terms are sorted by length (longest first) to prevent partial matches.

    Args:
        text: The input prompt text.
        key_terms: List of terms to emphasize.

    Returns:
        Text with key terms in ALL CAPS.
    """
    if not key_terms:
        return text

    def transform(segment: str) -> str:
        return _replace_terms(segment, key_terms, lambda t: t.upper())

    return _apply_to_text_only(text, transform)


def apply_quotes_emphasis(text: str, key_terms: list[str]) -> str:
    """Wrap key terms in 'single quotes'.

    Terms are sorted by length (longest first) to prevent partial matches.

    Args:
        text: The input prompt text.
        key_terms: List of terms to emphasize.

    Returns:
        Text with key terms in 'single quotes'.
    """
    if not key_terms:
        return text

    def transform(segment: str) -> str:
        return _replace_terms(segment, key_terms, lambda t: f"'{t}'")

    return _apply_to_text_only(text, transform)


def _replace_terms(
    text: str,
    key_terms: list[str],
    formatter: "callable",  # noqa: F821
) -> str:
    """Replace key terms with formatted versions using sentinel strategy.

    Sorts terms by length descending, replaces with sentinels, then
    substitutes sentinels with formatted text. This prevents partial
    matches and double-replacement.

    Args:
        text: Text to process.
        key_terms: Terms to replace.
        formatter: Function that takes original term and returns formatted version.

    Returns:
        Text with terms replaced.
    """
    sorted_terms = sorted(key_terms, key=len, reverse=True)
    sentinels: dict[str, str] = {}

    result = text
    for i, term in enumerate(sorted_terms):
        sentinel = f"\x00SENT{i}\x00"
        sentinels[sentinel] = formatter(term)
        result = result.replace(term, sentinel)

    for sentinel, replacement in sentinels.items():
        result = result.replace(sentinel, replacement)

    return result


# ---------------------------------------------------------------------------
# Cluster B: Instruction-word emphasis
# ---------------------------------------------------------------------------

# Instruction verb patterns — multi-word phrases first
_INSTRUCTION_PHRASES = [
    "do not",
    "don't",
    "need to",
    "have to",
]

_INSTRUCTION_WORDS = [
    "should",
    "must",
    "will",
    "shall",
]

# "return" only when NOT followed by an identifier character
_RETURN_PATTERN = re.compile(
    r"\breturn\b(?!\s+[a-z_])", re.IGNORECASE
)


def _build_instruction_pattern() -> re.Pattern:
    """Build compiled regex for instruction verb detection.

    Returns:
        Compiled regex matching instruction verbs/phrases.
    """
    # Multi-word phrases (escaped for regex)
    phrase_alts = [re.escape(p) for p in _INSTRUCTION_PHRASES]
    # Single words with word boundaries
    word_alts = [re.escape(w) for w in _INSTRUCTION_WORDS]

    # Combine: phrases first (longer matches), then single words
    all_alts = phrase_alts + word_alts
    pattern = r"\b(" + "|".join(all_alts) + r")\b"
    return re.compile(pattern, re.IGNORECASE)


_INSTRUCTION_RE = _build_instruction_pattern()


def apply_instruction_caps(text: str) -> str:
    """Convert instruction verbs to ALL CAPS.

    Target words: "do not", "don't", "should", "must", "will", "shall",
    "need to", "have to", "return" (when not followed by an identifier).

    Args:
        text: The input prompt text.

    Returns:
        Text with instruction verbs in ALL CAPS.
    """
    def transform(segment: str) -> str:
        result = _INSTRUCTION_RE.sub(lambda m: m.group(0).upper(), segment)
        result = _RETURN_PATTERN.sub(lambda m: m.group(0).upper(), result)
        return result

    return _apply_to_text_only(text, transform)


def apply_mixed_emphasis(text: str) -> str:
    """Bold on negation words, CAPS on other instruction verbs.

    Negation words ("do not", "don't") get **bold**, while other
    instruction verbs ("should", "must", "will", "shall", "need to",
    "have to", "return") get ALL CAPS.

    Args:
        text: The input prompt text.

    Returns:
        Text with mixed emphasis applied.
    """
    _negation_phrases = ["do not", "don't"]
    _negation_re = re.compile(
        r"\b(" + "|".join(re.escape(p) for p in _negation_phrases) + r")\b",
        re.IGNORECASE,
    )

    def transform(segment: str) -> str:
        # First: bold negations
        result = _negation_re.sub(lambda m: f"**{m.group(0)}**", segment)
        # Then: caps on non-negation instruction words
        result = _INSTRUCTION_RE.sub(lambda m: m.group(0).upper(), result)
        result = _RETURN_PATTERN.sub(lambda m: m.group(0).upper(), result)
        return result

    return _apply_to_text_only(text, transform)


# Extended instruction word set for aggressive caps (broader scope)
_AGGRESSIVE_WORDS = [
    "should",
    "must",
    "will",
    "shall",
    "need to",
    "have to",
    "do not",
    "don't",
    "can",
    "cannot",
    "may",
    "might",
    "ought",
    "require",
    "ensure",
    "verify",
    "check",
    "validate",
    "handle",
    "implement",
    "compute",
    "calculate",
    "determine",
    "note",
    "assume",
    "consider",
    "ignore",
]

_AGGRESSIVE_RE = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in sorted(_AGGRESSIVE_WORDS, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)


def apply_aggressive_caps(text: str) -> str:
    """ALL instruction words in CAPS (broader scope than instruction_caps).

    Targets a wider set of instructional vocabulary: modal verbs, imperative
    verbs, and common programming task verbs. Uses the same code-block
    protection as other emphasis functions.

    Args:
        text: The input prompt text.

    Returns:
        Text with all instruction words in ALL CAPS.
    """
    def transform(segment: str) -> str:
        result = _AGGRESSIVE_RE.sub(lambda m: m.group(0).upper(), segment)
        result = _RETURN_PATTERN.sub(lambda m: m.group(0).upper(), result)
        return result

    return _apply_to_text_only(text, transform)


def apply_instruction_bold(text: str) -> str:
    """Wrap instruction verbs in **bold** markdown emphasis.

    Same target words as apply_instruction_caps.

    Args:
        text: The input prompt text.

    Returns:
        Text with instruction verbs wrapped in **bold**.
    """
    def transform(segment: str) -> str:
        result = _INSTRUCTION_RE.sub(lambda m: f"**{m.group(0)}**", segment)
        result = _RETURN_PATTERN.sub(lambda m: f"**{m.group(0)}**", result)
        return result

    return _apply_to_text_only(text, transform)


# ---------------------------------------------------------------------------
# Cluster C: Lowercase sentence-initial
# ---------------------------------------------------------------------------

# Matches: start of string OR sentence boundary (. ! ?) followed by whitespace
_SENTENCE_START_RE = re.compile(
    r"((?:^|[.!?]\s+))([A-Z])",
    re.MULTILINE,
)


def lowercase_sentence_initial(text: str) -> str:
    """Lowercase the first character after sentence boundaries.

    Sentence boundaries: start of string, after '. ', '! ', '? '.
    Skips if next chars form an acronym (2+ consecutive uppercase).

    Args:
        text: The input prompt text.

    Returns:
        Text with sentence-initial characters lowercased.
    """
    def transform(segment: str) -> str:
        def _replace(m: re.Match) -> str:
            prefix = m.group(1)
            char = m.group(2)
            # Check if this starts an acronym (next char is also uppercase)
            end_pos = m.end()
            if end_pos < len(segment) and segment[end_pos].isupper():
                return prefix + char  # Skip acronym
            return prefix + char.lower()

        return _SENTENCE_START_RE.sub(_replace, segment)

    return _apply_to_text_only(text, transform)


# ---------------------------------------------------------------------------
# Cache loader for pre-computed emphasis variants
# ---------------------------------------------------------------------------

_INTERVENTION_FILE_MAP: dict[str, str] = {
    "emphasis_bold": "cluster_a_bold.json",
    "emphasis_caps": "cluster_a_caps.json",
    "emphasis_quotes": "cluster_a_quotes.json",
    "emphasis_mixed": "cluster_b_variants.json",
    "emphasis_aggressive_caps": "cluster_b_variants.json",
}


def load_emphasis_variant(
    prompt_id: str,
    intervention: str,
    cache_dir: str = "data/emphasis",
) -> str:
    """Load a pre-computed emphasis variant from a JSON cache file.

    Supports two JSON schemas via auto-detection:
    - Flat schema (Cluster A): {prompt_id: converted_text}
    - Nested schema (Cluster B): {prompts: {prompt_id: {intervention: text}}}

    Schema detection: if top-level key "prompts" exists and its values are
    dicts (not strings), use nested lookup; otherwise use flat lookup.

    Args:
        prompt_id: The prompt identifier (e.g., "HumanEval/1").
        intervention: The intervention type (e.g., "emphasis_bold").
        cache_dir: Directory containing cache JSON files.

    Returns:
        The pre-converted prompt text.

    Raises:
        FileNotFoundError: If cache file does not exist.
        KeyError: If prompt_id or intervention not found in cache.
    """
    filename = _INTERVENTION_FILE_MAP.get(intervention)
    if filename is None:
        raise KeyError(
            f"Unknown intervention '{intervention}' — "
            f"expected one of {list(_INTERVENTION_FILE_MAP.keys())}"
        )

    filepath = Path(cache_dir) / filename
    if not filepath.exists():
        raise FileNotFoundError(
            f"Cache file not found: {filepath} "
            f"(for intervention '{intervention}')"
        )

    with open(filepath) as f:
        data = json.load(f)

    # Schema detection: check if "prompts" key exists with dict values
    if "prompts" in data and isinstance(data["prompts"], dict):
        # Check if values are dicts (nested) vs strings (flat with "prompts" key)
        sample_val = next(iter(data["prompts"].values()), None)
        if isinstance(sample_val, dict):
            # Nested schema
            if prompt_id not in data["prompts"]:
                raise KeyError(
                    f"Prompt '{prompt_id}' not found in {filepath}. "
                    f"Available: {list(data['prompts'].keys())[:5]}"
                )
            prompt_data = data["prompts"][prompt_id]
            if intervention not in prompt_data:
                raise KeyError(
                    f"Intervention '{intervention}' not found for prompt "
                    f"'{prompt_id}' in {filepath}. "
                    f"Available: {list(prompt_data.keys())}"
                )
            return prompt_data[intervention]

    # Flat schema
    if prompt_id not in data:
        raise KeyError(
            f"Prompt '{prompt_id}' not found in {filepath}. "
            f"Available: {list(data.keys())[:5]}"
        )
    return data[prompt_id]
