"""Prompt repetition module implementing the Leviathan et al. <QUERY><QUERY> technique.

The prompt repetition strategy duplicates the user's prompt text, separated by
two newlines. This allows the model to attend to the content twice during the
parallelizable prefill stage, potentially improving robustness to noise at zero
additional cost (the extra tokens add no output latency).

Reference: Leviathan et al. -- prompt repetition as a zero-cost robustness
intervention for LLM reasoning under noisy input conditions.
"""


def repeat_prompt(text: str) -> str:
    """Repeat the prompt text with a double-newline separator.

    The input text is duplicated verbatim -- no cleaning, normalization,
    or modification is applied. Both copies are identical, including any
    noise present in the original.

    Args:
        text: The prompt text to repeat (may contain noise).

    Returns:
        The prompt text repeated twice, separated by two newlines.
    """
    return f"{text}\n\n{text}"
