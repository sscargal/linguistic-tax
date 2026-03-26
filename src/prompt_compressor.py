"""Prompt compressor and sanitizer module for pre-processing interventions.

Provides:
- SELF_CORRECT_PREFIX: Exact RDD Section 6 wording for the self-correct intervention.
- build_self_correct_prompt(): Prepend self-correct prefix to a prompt.
- sanitize(): Fix spelling/grammar via a cheap pre-processor model.
- sanitize_and_compress(): Fix errors and compress via a cheap pre-processor model.

Pre-processor functions accept a callable (call_fn) for API calls, enabling
easy testing with mocks and avoiding circular imports with api_client.
"""

import logging
from collections.abc import Callable
from typing import Any

from src.model_registry import registry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SELF_CORRECT_PREFIX: str = (
    "Note: my prompt below may contain spelling or grammar errors. "
    "First, correct any errors you find, then execute the corrected "
    "version of my request."
)

_SANITIZE_SYSTEM: str = "You are a text corrector."
_SANITIZE_INSTRUCTION: str = (
    "Fix all spelling and grammar errors in the following text. "
    "Return only the corrected text, no explanation.\n---\n"
)

_COMPRESS_SYSTEM: str = "You are a prompt optimizer."
_COMPRESS_INSTRUCTION: str = (
    "Fix all spelling and grammar errors in the following text, then "
    "remove redundancy and condense to minimal phrasing. Preserve all "
    "original intent. Return only the optimized text, no explanation.\n---\n"
)


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def build_self_correct_prompt(text: str) -> str:
    """Prepend the self-correct instruction prefix to a prompt.

    Args:
        text: The prompt text (may contain noise).

    Returns:
        The self-correct prefix followed by a separator and the prompt text.
    """
    return f"{SELF_CORRECT_PREFIX}\n---\n{text}"


def _get_preproc_model(main_model: str) -> str:
    """Return the preprocessor model ID for a given target model.

    If no preprocessor mapping exists, logs a warning and returns
    the model itself as a fallback (self-preprocessing).

    Args:
        main_model: The main model identifier (e.g., "claude-sonnet-4-20250514").

    Returns:
        The corresponding cheap pre-processor model identifier, or
        main_model itself if no mapping exists.
    """
    preproc = registry.get_preproc(main_model)
    if preproc is None:
        logger.warning(
            "No pre-processor mapping for '%s'; using model itself as fallback",
            main_model,
        )
        return main_model
    return preproc


def sanitize(
    text: str,
    main_model: str,
    call_fn: Callable[..., Any],
) -> tuple[str, dict[str, Any]]:
    """Sanitize a noisy prompt by fixing spelling and grammar via a cheap model.

    Calls the pre-processor model to correct errors in the prompt text.
    Falls back to the raw prompt if the pre-processor returns an empty
    result or a result longer than 1.5x the original text.

    Args:
        text: The noisy prompt text to sanitize.
        main_model: The main model identifier (used to look up pre-processor).
        call_fn: Callable that makes API calls. Expected signature:
            call_fn(model, system, user_message, max_tokens, temperature) -> response

    Returns:
        A tuple of (processed_text, metadata_dict).
        metadata_dict contains preproc_model, token counts, timing, and
        optionally preproc_failed=True if fallback was triggered.
    """
    preproc_model = _get_preproc_model(main_model)
    user_message = _SANITIZE_INSTRUCTION + text

    response = call_fn(
        model=preproc_model,
        system=_SANITIZE_SYSTEM,
        user_message=user_message,
        max_tokens=max(512, len(text) * 2),
        temperature=0.0,
    )

    return _process_response(response, text, preproc_model)


def sanitize_and_compress(
    text: str,
    main_model: str,
    call_fn: Callable[..., Any],
) -> tuple[str, dict[str, Any]]:
    """Sanitize and compress a noisy prompt via a cheap model.

    Calls the pre-processor model to fix errors and remove redundancy.
    Falls back to the raw prompt if the pre-processor returns an empty
    result or a result longer than 1.5x the original text.

    Args:
        text: The noisy prompt text to sanitize and compress.
        main_model: The main model identifier (used to look up pre-processor).
        call_fn: Callable that makes API calls. Expected signature:
            call_fn(model, system, user_message, max_tokens, temperature) -> response

    Returns:
        A tuple of (processed_text, metadata_dict).
        metadata_dict contains preproc_model, token counts, timing, and
        optionally preproc_failed=True if fallback was triggered.
    """
    preproc_model = _get_preproc_model(main_model)
    user_message = _COMPRESS_INSTRUCTION + text

    response = call_fn(
        model=preproc_model,
        system=_COMPRESS_SYSTEM,
        user_message=user_message,
        max_tokens=max(512, len(text) * 2),
        temperature=0.0,
    )

    return _process_response(response, text, preproc_model)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _process_response(
    response: Any,
    original_text: str,
    preproc_model: str,
) -> tuple[str, dict[str, Any]]:
    """Process a pre-processor API response with fallback logic.

    Args:
        response: The API response object with text, token counts, and timing.
        original_text: The original input text (for fallback and length comparison).
        preproc_model: The pre-processor model used (for metadata).

    Returns:
        A tuple of (processed_text, metadata_dict).
    """
    result = response.text.strip()
    metadata: dict[str, Any] = {
        "preproc_model": preproc_model,
        "preproc_input_tokens": response.input_tokens,
        "preproc_output_tokens": response.output_tokens,
        "preproc_ttft_ms": response.ttft_ms,
        "preproc_ttlt_ms": response.ttlt_ms,
    }

    # Fallback: empty or bloated output
    if not result or len(result) > len(original_text) * 1.5:
        logger.warning(
            "Pre-processor fallback: model=%s, output_len=%d, input_len=%d",
            preproc_model,
            len(result),
            len(original_text),
        )
        metadata["preproc_failed"] = True
        return original_text, metadata

    return result, metadata
