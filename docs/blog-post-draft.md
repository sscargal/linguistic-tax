# The Linguistic Tax: We Built a Prompt Optimizer, Then Discovered LLMs Don't Need One

**TL;DR:** We set out to measure how typos, grammar errors, and non-native English degrade LLM accuracy, then built an automated "prompt optimizer" to fix it. After 8,000+ controlled experiments across two models (GPT-5-mini and GPT-4o-mini), we found the linguistic tax is surprisingly small on frontier models — and our optimizer barely moves the needle. But we also discovered that prompt compression actively destroys accuracy, and we can show you exactly why.

---

## The Hypothesis

Every day, millions of people prompt LLMs with imperfect English. Typos, autocorrect failures, ESL grammar patterns — these are the norm, not the exception. We hypothesized that this "linguistic tax" meaningfully degrades LLM accuracy and that a lightweight preprocessor could recover the lost performance.

We designed a controlled experiment:

- **200 benchmark prompts** across three tasks: code generation (HumanEval, MBPP) and math reasoning (GSM8K)
- **8 noise conditions**: clean, three levels of character noise (5%, 10%, 20% of characters corrupted), and four ESL patterns (Mandarin, Spanish, Japanese, and mixed L1 transfer)
- **6 interventions**: raw (no fix), self-correct ("fix my errors then answer"), preprocessor sanitization, sanitization + compression, compression only, and prompt repetition
- **5 repetitions** per condition at temperature=0.0 for stability measurement
- **20 real-world noisy prompts** modeled on actual user input patterns (mobile typos, autocorrect errors, voice-to-text artifacts, ESL constructions, rushed shorthand)

We ran 20-prompt pilots on two models: GPT-5-mini ($5.55) and GPT-4o-mini (~$1). We tested both to see whether noise robustness scales with model capability.

## The Results

### Finding 1: The Linguistic Tax Exists, But It's Small

*GPT-5-mini, raw intervention, 4,098 experiment items:*

| Noise Level | Pass Rate | Degradation |
|---|---|---|
| Clean (no noise) | 85.0% | — |
| 5% character noise | 86.0% | +1.0% (within variance) |
| 10% character noise | 78.0% | -7.0% |
| 20% character noise | 78.0% | -7.0% |
| ESL patterns (average) | 84.2% | -0.8% (negligible) |

At 20% character corruption — text that is nearly unreadable to humans — GPT-5-mini still achieves 78% accuracy. That's a 7% tax on severely mangled input. ESL grammar patterns (article omission, tense errors, word order changes) have almost zero effect.

*Placeholder for GPT-4o-mini comparison table — results pending.*

<!-- TODO: Insert GPT-4o-mini noise comparison table here after pilot completes -->

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

### Finding 4: Compression Destroys Accuracy — And We Know Why

This was the most surprising result. Compression drops accuracy by 8-10%, and we traced exactly how it breaks things by examining every case where compression caused a previously-passing prompt to fail.

**The compressor solves problems instead of preserving them.** A math prompt asking "The Smith twins each found 30 eggs. All the other eggs except 10 were found by their friends. How many eggs did the friends find?" was compressed to "The Smith twins found 30 eggs. Their friends found the remaining 70 eggs." The compressor computed the answer and embedded it in the prompt, changing the task from reasoning to reading comprehension.

**The compressor changes specifications.** A code prompt asking to "count uppercase vowels in given indices" was compressed to "count uppercase vowels at even indices" — with the test cases altered to match the new (wrong) interpretation. The expected output for `count_upper('dBBE')` changed from 0 to 2.

**The compressor inverts meaning.** "Each ice cube makes the coffee 12 milliliters weaker" became "Each ice cube adds 12 milliliters of water... also warms the coffee." The word "weaker" was replaced with "warms" — the exact opposite.

The root cause is fundamental: **the compressor is an LLM itself** (GPT-4o-mini), and it can't help but "understand" and "improve" the text. When you ask a language model to compress, it interprets. When it interprets, it changes meaning. The tokens we think are redundant carry signal the model needs.

### Finding 5: Self-Correct Is Harmful for Code, Neutral for Math

Prepending "fix any errors in my prompt, then answer" causes the model to:
- Output a "Corrected prompt:" preamble before answering (99% of responses)
- Generate multiple solution variants instead of one answer (57% of code responses)
- Produce 40% more output tokens (857 vs 612 average)

On code generation specifically, self-correct drops HumanEval from 95.7% to 65.7% — a catastrophic 30-point decline. The model overthinks the correction task and loses focus on the actual problem. Ironically, it *helps* GSM8K math (+0.9%), where the structured "correct then solve" framing aids chain-of-thought reasoning.

### Finding 6: Prompt Repetition Is Free and Neutral

Inspired by [Leviathan et al. (2025)](https://arxiv.org/abs/2512.14982), we tested simply duplicating the prompt: `<QUERY><QUERY>`. The theory is that causal attention allows every token to attend to its copy, effectively "self-correcting" through redundancy.

Result: 82.9% vs 83.0% raw. Perfectly neutral. It doesn't help, but unlike compression, it doesn't hurt. The cost of doubling input tokens ($0.99 vs $0.99) is negligible because output tokens dominate the bill.

### Finding 7: Model Comparison — Does Capability Predict Robustness?

*Results pending from GPT-4o-mini pilot.*

<!-- TODO: Insert comparative analysis here. Key questions:
- Does GPT-4o-mini show a larger linguistic tax?
- Does the preprocessor help MORE on the weaker model?
- Does compression hurt LESS on the weaker model (less to lose)?
-->

## Real-World Noise Testing

Beyond synthetic noise, we tested 20 prompts modeled on patterns from real user interactions:

| Category | Example | What Makes It Realistic |
|---|---|---|
| Mobile keyboard | "writ ea function taht takes a list of integrs" | Adjacent-key swaps, transpositions, missing spaces |
| Autocorrect | "merge two sorted lists into one sorted lost" | Plausible wrong words ('lost' for 'list') |
| ESL (Mandarin L1) | "Please help me write function, input is list of number" | Missing articles, bare nouns, topic-comment structure |
| ESL (Spanish L1) | "function that receive a string and return the string inversed" | 'receive' for 'takes', 'inversed' for 'reversed' |
| Voice-to-text | "sixty miles per our for too hours" | Homophones, no punctuation, spelled-out numbers |
| Rushed typing | "fn that flattens nested list. recursive pls" | Abbreviations, no articles, informal shorthand |
| Copy-paste | Non-breaking spaces in code indentation | Invisible Unicode corruption from web copy |
| Mixed noise | "Can u make function to check if number is prime??" | Informal + typos + missing articles combined |

<!-- TODO: Insert real-world noise test results after running them through the pipeline -->

## The Toolkit

We built `propt` (prompt optimizer toolkit) as an open-source research platform:

- **Multi-provider support**: Anthropic, Google, OpenAI, OpenRouter — configure any combination of target and preprocessor models
- **Deterministic noise injection**: Fixed-seed character mutations and linguistically-grounded ESL patterns for reproducibility
- **Automated grading**: HumanEval/MBPP sandboxed code execution, GSM8K numerical extraction with priority cascade
- **Session management**: Per-run isolation, cost tracking, resumability
- **Parallel execution**: Multiple models run concurrently across providers
- **Preprocessor caching**: Identical noisy prompts produce identical preprocessor output across repetitions — redundant API calls eliminated automatically
- **Full observability**: Every pipeline stage logged to SQLite — noisy prompt, preprocessor output, model response, extracted code/numbers, grading details

The full experiment matrix for 200 prompts generates ~41,000 items per model. A 20-prompt pilot runs in ~9 hours and costs ~$5 per model.

## What This Means

**For users:** Don't worry about typos in your prompts. Modern frontier LLMs handle them gracefully. Definitely don't compress your prompts to save tokens — you'll lose more in accuracy than you save in cost.

**For prompt optimization tool builders:** The market for "prompt cleaning" tools aimed at frontier models is shrinking. The models themselves are absorbing this capability. Focus on structural prompt engineering (formatting, few-shot examples, system prompts) rather than surface-level text cleaning.

**For researchers:** The linguistic tax is a moving target. As models improve, the gap between clean and noisy prompts narrows. The most interesting finding here isn't about noise — it's that **compression is fundamentally incompatible with accuracy** when the compressor is an LLM. Any system that "optimizes" prompts by condensing them risks the same failure modes we documented: solving problems prematurely, changing specifications, and inverting meaning.

## Limitations

**Small sample size.** 20 prompts per pilot with 5 repetitions. Some cells have only 5 data points. The type_a_5pct > clean anomaly is a small-sample artifact. A full 200-prompt run would provide statistical power for significance testing.

**Limited task types.** Code generation and math reasoning have clear right/wrong answers. Creative writing, summarization, and open-ended Q&A might show different noise sensitivity patterns.

**Two models, one provider.** Both GPT-5-mini and GPT-4o-mini are from OpenAI. Testing Claude, Gemini, or open-source models would validate whether the findings generalize across architectures.

## Reproducing This Work

The toolkit and all experimental infrastructure are open source:

```bash
# Install
git clone https://github.com/[repo]/linguistic-tax
cd linguistic-tax
uv sync

# Configure (choose your models)
uv run propt setup

# Run pilot (20 prompts, ~$5/model, ~9 hours)
uv run propt pilot

# View results
uv run propt report
```

All noise generation uses fixed random seeds. All API calls use temperature=0.0. Results are stored in per-session SQLite databases with full provenance (noisy prompt, preprocessor output, model response, grading details).

---

*Built with [propt](https://github.com/[repo]/linguistic-tax) — a research toolkit for measuring prompt noise and intervention effects on LLM accuracy.*
