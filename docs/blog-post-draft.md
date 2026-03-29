# The Linguistic Tax: We Built a Prompt Optimizer, Then Discovered LLMs Don't Need One

**TL;DR:** We set out to measure how typos, grammar errors, and non-native English degrade LLM accuracy, then built an automated "prompt optimizer" to fix it. After 4,100 controlled experiments on GPT-5-mini, we found the linguistic tax is surprisingly small — and our optimizer barely moves the needle. Modern frontier LLMs have largely solved this problem themselves. Here's what we learned.

---

## The Hypothesis

Every day, millions of people prompt LLMs with imperfect English. Typos, autocorrect failures, ESL grammar patterns — these are the norm, not the exception. We hypothesized that this "linguistic tax" meaningfully degrades LLM accuracy and that a lightweight preprocessor could recover the lost performance.

We designed a rigorous experiment:

- **200 benchmark prompts** across three tasks: code generation (HumanEval, MBPP) and math reasoning (GSM8K)
- **8 noise conditions**: clean, three levels of character noise (5%, 10%, 20% of characters corrupted), and four ESL patterns (Mandarin, Spanish, Japanese, and mixed L1 transfer)
- **5 interventions**: raw (no fix), self-correct ("fix my errors then answer"), preprocessor sanitization, sanitization + compression, and prompt repetition
- **5 repetitions** per condition at temperature=0.0 for stability measurement

We ran a 20-prompt pilot (4,100 experiment items) on GPT-5-mini. Total cost: $5.55.

## The Results

### Finding 1: The Linguistic Tax Exists, But It's Small

| Noise Level | Pass Rate | Degradation |
|---|---|---|
| Clean (no noise) | 85.0% | — |
| 5% character noise | 86.0% | +1.0% (within variance) |
| 10% character noise | 78.0% | -7.0% |
| 20% character noise | 78.0% | -7.0% |
| ESL patterns (average) | 84.2% | -0.8% (negligible) |

At 20% character corruption — text that is nearly unreadable to humans — GPT-5-mini still achieves 78% accuracy. That's a 7% tax on severely mangled input. ESL grammar patterns (article omission, tense errors, word order changes) have almost zero effect.

### Finding 2: The Tax Falls Unevenly Across Tasks

Not all tasks are equally vulnerable:

| Benchmark | Clean | 20% Noise | Degradation |
|---|---|---|---|
| GSM8K (math) | 100% | 93.3% | -6.7% |
| HumanEval (code) | 94.3% | 100%* | +5.7%* |
| MBPP (code) | 62.9% | 42.9% | **-20.0%** |

*HumanEval's improvement under noise is a small-sample artifact (7 prompts, 5 reps).

The real story is **MBPP**: ambiguous coding tasks drop 20 percentage points under heavy noise. When the prompt is already unclear ("Write a function to find the maximum product subarray"), adding typos pushes the model past a comprehension threshold. Math reasoning, with its unambiguous numerical structure, is barely affected.

### Finding 3: Our Preprocessor Doesn't Help (But Doesn't Hurt Either)

| Intervention | Pass Rate | vs Raw | Cost |
|---|---|---|---|
| Raw (baseline) | 83.0% | — | $0.99 |
| Prompt repetition | 82.9% | -0.1% | $0.99 |
| Preprocessor (sanitize) | 82.2% | -0.8% | $1.01 |
| Sanitize + compress | 75.1% | **-7.9%** | $1.03 |
| Self-correct | 73.1% | **-9.9%** | $1.39 |
| Compress only | 73.0% | **-10.0%** | $0.13 |

The sanitizer (a cheap GPT-4o-mini call that fixes typos and grammar) preserves accuracy at 82.2% — essentially matching raw. It doesn't hurt, but it doesn't help either. The model is already robust enough that cleaning the input provides no measurable benefit.

### Finding 4: Compression and Self-Correct Are Actively Harmful

This was the most surprising result. Two interventions that seem intuitively helpful actually **destroy accuracy**:

**Compression (-8 to -10%):** Removing redundancy and condensing prompts loses signal the model needs. Even on clean, noise-free prompts, compression drops accuracy from 83% to 73%. The tokens we think are "redundant" aren't redundant to the model.

**Self-correct (-10%):** Prepending "fix any errors, then answer" causes the model to:
- Output a "Corrected prompt:" preamble before answering (99% of responses)
- Generate multiple solution variants instead of one answer (57% of code responses)
- Produce 40% more output tokens (857 vs 612 average)

On code generation specifically, self-correct drops HumanEval from 95.7% to 65.7% — a catastrophic 30-point decline. The model overthinks the correction task and loses focus on the actual problem. Ironically, it *helps* GSM8K math (+0.9%), where the structured "correct then solve" framing aids chain-of-thought reasoning.

### Finding 5: Prompt Repetition Is Free and Neutral

Inspired by [Leviathan et al. (2025)](https://arxiv.org/abs/2512.14982), we tested simply duplicating the prompt: `<QUERY><QUERY>`. The theory is that causal attention allows every token to attend to its copy, effectively "self-correcting" through redundancy.

Result: 82.9% vs 83.0% raw. Perfectly neutral. It doesn't help, but unlike compression, it doesn't hurt. The cost of doubling input tokens ($0.99 vs $0.99) is negligible because output tokens dominate the bill.

## The Toolkit

We built `propt` (prompt optimizer toolkit) as an open-source research platform:

- **Multi-provider support**: Anthropic, Google, OpenAI, OpenRouter — configure any combination of target and preprocessor models
- **Deterministic noise injection**: Fixed-seed character mutations and linguistically-grounded ESL patterns for reproducibility
- **Automated grading**: HumanEval/MBPP sandboxed code execution, GSM8K numerical extraction with priority cascade
- **Session management**: Per-run isolation, cost tracking, resumability
- **Parallel execution**: Multiple models run concurrently across providers

The full experiment matrix for 200 prompts generates ~41,000 items per model. With preprocessor caching (identical noisy prompts produce identical preprocessor output across repetitions), redundant API calls are eliminated automatically.

## What This Means

**For users:** Don't worry about typos in your prompts. Modern frontier LLMs handle them gracefully. Definitely don't compress your prompts to save tokens — you'll lose more in accuracy than you save in cost.

**For prompt optimization tool builders:** The market for "prompt cleaning" tools aimed at frontier models is shrinking. The models themselves are absorbing this capability. Focus on structural prompt engineering (formatting, few-shot examples, system prompts) rather than surface-level text cleaning.

**For researchers:** The linguistic tax is a moving target. As models improve, the gap between clean and noisy prompts narrows. A longitudinal study across model generations (GPT-4 vs GPT-5 vs GPT-5-mini) would quantify this trajectory.

## Limitations and Gaps

This pilot has several limitations that a full study should address:

<!-- GAP 1: Single model -->
**Single model tested.** We only tested GPT-5-mini. The linguistic tax may be larger on smaller or older models (GPT-4o-mini, Claude Haiku, Gemini Flash). Testing across model sizes would reveal whether noise robustness scales with model capability — and whether the preprocessor helps weaker models where frontier models don't need it.

<!-- GAP 2: Small sample -->
**Small sample size.** 20 prompts (7 HumanEval, 7 MBPP, 6 GSM8K) with 5 repetitions. Some cells have only 5 data points. The type_a_5pct > clean anomaly and HumanEval's improvement under noise are likely small-sample artifacts. The full 200-prompt run would provide statistical power for significance testing.

<!-- GAP 3: Noise realism -->
**Synthetic noise only.** Our Type A noise (random character mutations) and Type B noise (rule-based ESL patterns) are systematic approximations. Real-world noisy prompts from actual users would be more ecologically valid. We have 20 real-world noisy prompts collected from public sources but haven't integrated them into the experimental pipeline yet.

<!-- GAP 4: Task diversity -->
**Limited task types.** Code generation and math reasoning are well-defined tasks with clear right/wrong answers. Creative writing, summarization, and open-ended Q&A might show different noise sensitivity patterns. The linguistic tax may matter more for nuanced tasks where small wording changes shift meaning.

<!-- GAP 5: Older models -->
**No longitudinal comparison.** The most compelling story would be: "Here's how the linguistic tax has shrunk over model generations." Testing GPT-4 (2023) vs GPT-4o (2024) vs GPT-5-mini (2025) on identical noisy prompts would directly measure this trajectory.

<!-- GAP 6: Compression analysis -->
**Compression mechanism unexplored.** We know compression hurts, but we don't know exactly why. Is it removing key technical terms? Losing context from docstrings? Changing function signatures? A qualitative analysis of what the compressor removes vs. what causes failures would be valuable.

## Reproducing This Work

The toolkit and all experimental infrastructure are open source:

```bash
# Install
git clone https://github.com/[repo]/linguistic-tax
cd linguistic-tax
uv sync

# Configure
uv run propt setup

# Run pilot (20 prompts, ~$5, ~9 hours)
uv run propt pilot

# View results
uv run propt report
```

All noise generation uses fixed random seeds. All API calls use temperature=0.0. Results are stored in per-session SQLite databases with full provenance (noisy prompt, preprocessor output, model response, grading details).

---

*Built with [propt](https://github.com/[repo]/linguistic-tax) — a research toolkit for measuring prompt noise and intervention effects on LLM accuracy.*
