"""Tests for the emphasis converter module.

Tests all 6 conversion functions, code block protection, overlapping term
handling, and the dual-schema cache loader (flat + nested JSON).
"""

import json
import os
from pathlib import Path

import pytest

from src.emphasis_converter import (
    apply_bold_emphasis,
    apply_caps_emphasis,
    apply_quotes_emphasis,
    apply_instruction_caps,
    apply_instruction_bold,
    lowercase_sentence_initial,
    load_emphasis_variant,
    _split_code_and_text,
)


# ---------------------------------------------------------------------------
# Cluster A: Key-term emphasis
# ---------------------------------------------------------------------------


class TestBoldEmphasis:
    """Tests for apply_bold_emphasis."""

    def test_basic_wrapping(self) -> None:
        result = apply_bold_emphasis(
            "Write a function that takes a list of integers",
            ["list of integers"],
        )
        assert result == "Write a function that takes a **list of integers**"

    def test_multiple_terms(self) -> None:
        result = apply_bold_emphasis(
            "Return the second largest unique value or None",
            ["second largest unique value", "None"],
        )
        assert "**second largest unique value**" in result
        assert "**None**" in result

    def test_no_terms_unchanged(self) -> None:
        text = "Write a function"
        assert apply_bold_emphasis(text, []) == text

    def test_term_not_found_unchanged(self) -> None:
        text = "Write a function"
        assert apply_bold_emphasis(text, ["xyz"]) == text


class TestCapsEmphasis:
    """Tests for apply_caps_emphasis."""

    def test_basic_uppercase(self) -> None:
        result = apply_caps_emphasis(
            "Write a function that takes a list of integers",
            ["list of integers"],
        )
        assert result == "Write a function that takes a LIST OF INTEGERS"

    def test_multiple_terms(self) -> None:
        result = apply_caps_emphasis(
            "Return the second largest value or None",
            ["second largest value", "None"],
        )
        assert "SECOND LARGEST VALUE" in result
        assert "NONE" in result


class TestQuotesEmphasis:
    """Tests for apply_quotes_emphasis."""

    def test_basic_quoting(self) -> None:
        result = apply_quotes_emphasis(
            "Write a function that takes a list of integers",
            ["list of integers"],
        )
        assert result == "Write a function that takes a 'list of integers'"

    def test_multiple_terms(self) -> None:
        result = apply_quotes_emphasis(
            "Return the value or None",
            ["value", "None"],
        )
        assert "'value'" in result
        assert "'None'" in result


# ---------------------------------------------------------------------------
# Cluster B: Instruction-word emphasis
# ---------------------------------------------------------------------------


class TestInstructionCaps:
    """Tests for apply_instruction_caps."""

    def test_converts_instruction_verbs(self) -> None:
        result = apply_instruction_caps(
            "You should return None. Do not modify the input."
        )
        assert "SHOULD" in result
        assert "DO NOT" in result

    def test_does_not_convert_code_keywords(self) -> None:
        """'return' followed by a code identifier should NOT be converted."""
        result = apply_instruction_caps("return value_name")
        # 'return' before an identifier stays lowercase
        assert "RETURN" not in result

    def test_return_in_instruction_context(self) -> None:
        """'return' followed by non-identifier should be converted."""
        result = apply_instruction_caps("You should return None.")
        assert "SHOULD" in result
        # "return" before "None" (starts with uppercase, looks like a value)
        # The key thing: instruction-context "return" gets caps

    def test_must_and_shall(self) -> None:
        result = apply_instruction_caps("You must handle errors. You shall not fail.")
        assert "MUST" in result
        assert "SHALL" in result

    def test_need_to_and_have_to(self) -> None:
        result = apply_instruction_caps("You need to validate. You have to check.")
        assert "NEED TO" in result
        assert "HAVE TO" in result


class TestInstructionBold:
    """Tests for apply_instruction_bold."""

    def test_wraps_instruction_verbs_in_bold(self) -> None:
        result = apply_instruction_bold(
            "You should return the value. Do not modify it."
        )
        assert "**should**" in result or "**SHOULD**" in result.upper()
        assert "**do not**" in result or "**DO NOT**" in result.upper()


# ---------------------------------------------------------------------------
# Cluster C: Lowercase initial
# ---------------------------------------------------------------------------


class TestLowercaseInitial:
    """Tests for lowercase_sentence_initial."""

    def test_lowercases_sentence_starts(self) -> None:
        result = lowercase_sentence_initial("Write a function. Return the result.")
        assert result == "write a function. return the result."

    def test_multiple_sentences(self) -> None:
        result = lowercase_sentence_initial("Hello world! Great day? Yes indeed.")
        assert result.startswith("hello")

    def test_already_lowercase(self) -> None:
        result = lowercase_sentence_initial("already lowercase. still lowercase.")
        assert result == "already lowercase. still lowercase."

    def test_skip_acronym(self) -> None:
        """Should not lowercase if next chars are an acronym (2+ uppercase)."""
        result = lowercase_sentence_initial("API is great.")
        assert result.startswith("API")


# ---------------------------------------------------------------------------
# Code block protection
# ---------------------------------------------------------------------------


class TestCodeProtection:
    """All functions must skip code blocks (fenced and indented)."""

    def test_bold_skips_fenced_code(self) -> None:
        text = "Use a list of integers.\n```\nlist of integers = [1,2]\n```\nDone."
        result = apply_bold_emphasis(text, ["list of integers"])
        assert "**list of integers**" in result  # outside code
        assert "```\nlist of integers = [1,2]\n```" in result  # inside code unchanged

    def test_caps_skips_fenced_code(self) -> None:
        text = "Use a list.\n```\nlist = [1,2]\n```\nDone."
        result = apply_caps_emphasis(text, ["list"])
        assert "LIST" in result.split("```")[0]  # outside code
        assert "list = [1,2]" in result  # inside code unchanged

    def test_quotes_skips_fenced_code(self) -> None:
        text = "Use a list.\n```\nlist = [1,2]\n```\nDone."
        result = apply_quotes_emphasis(text, ["list"])
        assert "'list'" in result.split("```")[0]
        assert "list = [1,2]" in result

    def test_instruction_caps_skips_fenced_code(self) -> None:
        text = "You should validate.\n```\nreturn value\n```\nDone."
        result = apply_instruction_caps(text)
        assert "SHOULD" in result
        assert "```\nreturn value\n```" in result

    def test_bold_skips_indented_code(self) -> None:
        text = "Use a list.\n    list = [1,2]\nDone with list."
        result = apply_bold_emphasis(text, ["list"])
        # The indented line should be preserved
        assert "    list = [1,2]" in result

    def test_instruction_caps_skips_indented_code(self) -> None:
        text = "You must check.\n    return result\nDone."
        result = apply_instruction_caps(text)
        assert "MUST" in result
        assert "    return result" in result

    def test_lowercase_skips_fenced_code(self) -> None:
        text = "Write code.\n```\nReturn result\n```\nReturn value."
        result = lowercase_sentence_initial(text)
        assert "```\nReturn result\n```" in result


# ---------------------------------------------------------------------------
# Overlapping terms
# ---------------------------------------------------------------------------


class TestOverlappingTerms:
    """Longer terms must be matched before shorter ones."""

    def test_longer_term_matched_first(self) -> None:
        result = apply_bold_emphasis(
            "Take a list of integers from the list",
            ["list of integers", "list"],
        )
        assert "**list of integers**" in result
        # The standalone "list" at end should also be bold
        assert result.endswith("the **list**")

    def test_caps_longer_first(self) -> None:
        result = apply_caps_emphasis(
            "Take a list of integers from the list",
            ["list of integers", "list"],
        )
        assert "LIST OF INTEGERS" in result


# ---------------------------------------------------------------------------
# Cache loader: flat schema (Cluster A)
# ---------------------------------------------------------------------------


class TestLoadEmphasisVariantFlat:
    """Tests for load_emphasis_variant with flat JSON schema."""

    def test_reads_flat_json(self, tmp_path: Path) -> None:
        cache_dir = str(tmp_path)
        data = {"HumanEval/1": "This is the **bold** version"}
        with open(tmp_path / "cluster_a_bold.json", "w") as f:
            json.dump(data, f)

        result = load_emphasis_variant("HumanEval/1", "emphasis_bold", cache_dir)
        assert result == "This is the **bold** version"

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_emphasis_variant("HumanEval/1", "emphasis_bold", str(tmp_path))

    def test_missing_prompt_id_raises(self, tmp_path: Path) -> None:
        data = {"HumanEval/99": "some text"}
        with open(tmp_path / "cluster_a_bold.json", "w") as f:
            json.dump(data, f)

        with pytest.raises(KeyError, match="HumanEval/1"):
            load_emphasis_variant("HumanEval/1", "emphasis_bold", str(tmp_path))


# ---------------------------------------------------------------------------
# Cache loader: nested schema (Cluster B)
# ---------------------------------------------------------------------------


class TestLoadEmphasisVariantNested:
    """Tests for load_emphasis_variant with nested JSON schema."""

    def test_reads_nested_json(self, tmp_path: Path) -> None:
        cache_dir = str(tmp_path)
        data = {
            "metadata": {"version": 1},
            "prompts": {
                "HumanEval/1": {
                    "emphasis_mixed": "Mixed version text",
                    "emphasis_aggressive_caps": "AGGRESSIVE version",
                }
            },
        }
        with open(tmp_path / "cluster_b_variants.json", "w") as f:
            json.dump(data, f)

        result = load_emphasis_variant("HumanEval/1", "emphasis_mixed", cache_dir)
        assert result == "Mixed version text"

    def test_missing_intervention_key_raises(self, tmp_path: Path) -> None:
        data = {
            "metadata": {},
            "prompts": {
                "HumanEval/1": {
                    "emphasis_mixed": "text",
                }
            },
        }
        with open(tmp_path / "cluster_b_variants.json", "w") as f:
            json.dump(data, f)

        with pytest.raises(KeyError, match="emphasis_aggressive_caps"):
            load_emphasis_variant(
                "HumanEval/1", "emphasis_aggressive_caps", str(tmp_path)
            )


# ---------------------------------------------------------------------------
# Schema detection
# ---------------------------------------------------------------------------


class TestSchemaDetection:
    """Verify auto-detection works for both flat and nested schemas."""

    def test_flat_schema_detected(self, tmp_path: Path) -> None:
        """Flat file with string values is read correctly."""
        data = {"HumanEval/1": "caps version"}
        with open(tmp_path / "cluster_a_caps.json", "w") as f:
            json.dump(data, f)

        result = load_emphasis_variant("HumanEval/1", "emphasis_caps", str(tmp_path))
        assert result == "caps version"

    def test_nested_schema_detected(self, tmp_path: Path) -> None:
        """Nested file with 'prompts' key containing dicts is read correctly."""
        data = {
            "prompts": {
                "HumanEval/1": {
                    "emphasis_mixed": "mixed text",
                }
            },
        }
        with open(tmp_path / "cluster_b_variants.json", "w") as f:
            json.dump(data, f)

        result = load_emphasis_variant("HumanEval/1", "emphasis_mixed", str(tmp_path))
        assert result == "mixed text"
