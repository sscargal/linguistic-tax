# Pitfalls Research

**Domain:** LLM prompt noise/optimization benchmarking research
**Researched:** 2026-03-19
**Confidence:** HIGH (domain-specific, verified against multiple sources and the RDD)

## Critical Pitfalls

### Pitfall 1: Temperature=0 Does Not Guarantee Determinism

**What goes wrong:**
Researchers assume `temperature=0` produces identical outputs across runs, then design analysis assuming perfect reproducibility. In reality, both Anthropic and Google explicitly state that temperature=0 does not guarantee deterministic outputs. Floating-point non-associativity in GPU matrix operations, batch size variation under different server loads, and Mixture-of-Experts routing variability all introduce run-to-run variance even with greedy decoding. This means the 5 repetitions per condition in the RDD will NOT produce identical outputs even on clean prompts -- and the experiment must be designed to expect this.

**Why it happens:**
The mental model "temperature=0 = argmax = deterministic" is mathematically correct for single-device, single-request inference but breaks under the distributed, batched inference that cloud APIs use. Researchers treat API calls like function calls and expect referential transparency.

**How to avoid:**
- The RDD already accounts for this by requiring 5 repetitions and measuring stability (Consistency Rate) as an independent dimension. This is correct.
- Do NOT use exact string matching to determine if two runs "agree." Use semantic equivalence: for code, functional equivalence via test passing; for math, numerical answer equivalence.
- Log the full response text for every repetition, not just pass/fail. Post-hoc analysis may need to distinguish "same wrong answer 5 times" from "different wrong answers."
- Accept that CR < 1.0 on clean prompts is EXPECTED, not a bug. Report baseline CR for clean prompts and measure noise-induced CR degradation relative to that baseline.

**Warning signs:**
- Clean prompt baseline shows CR = 1.0 across all prompts (suspiciously perfect -- likely a grading bug hiding variation)
- Stability analysis shows no difference between clean and noisy conditions (the measurement may not be granular enough)

**Phase to address:**
Experiment harness implementation -- the execution layer must log full responses and compute CR correctly from the start. Retrofitting this is expensive.

---

### Pitfall 2: GSM8K Regex Answer Extraction Produces False Positives and False Negatives

**What goes wrong:**
GSM8K answers are typically extracted using regex matching for the `#### [number]` pattern. LLMs frequently deviate from this format: they may produce the correct numerical answer embedded in prose ("The answer is 42"), use LaTeX formatting (`\boxed{42}`), include units ("42 dollars"), or produce the answer in a different notation ("42.0" vs "42"). Strict regex misses correct answers (false negatives). Loose regex matches intermediate calculations or wrong numbers that happen to appear in the expected format (false positives). Research from ICLR 2025 shows regex-based evaluation methods produce unreliable rankings that can flip model ordering.

**Why it happens:**
Different models and different prompt phrasings elicit different output formats. Instruction-tuned models may follow the `####` convention when explicitly prompted but deviate when the prompt is noisy or compressed. The noise injection itself may corrupt or remove format instructions, causing the model to free-form its answer.

**How to avoid:**
- Use a TWO-STAGE extraction: (1) regex for `####` pattern, (2) fallback regex for last number in response, (3) flag ambiguous cases for manual review.
- Normalize extracted numbers: strip commas, convert fractions/percentages, handle negative signs, treat "42.0" and "42" as equivalent.
- Include the answer format instruction in the PROTECTED portion of prompts (not subject to noise injection). If noise corrupts the format instruction, you are measuring "can the model follow a corrupted format instruction" not "can the model do math with a noisy prompt."
- Run a validation pass: for every prompt graded "fail," check if the correct numerical answer appears ANYWHERE in the response. Log the discrepancy rate. If it exceeds 5%, your grading is unreliable.
- Consider using the `math_verify` parser or an LLM-based answer extractor as a secondary check on a random sample.

**Warning signs:**
- Accuracy drops sharply on noisy prompts but manual inspection shows the model got the right answer in non-standard format
- One model scores much lower than expected because it uses a different answer format
- Compression intervention changes accuracy not because reasoning changed but because format instructions were compressed away

**Phase to address:**
Grading module implementation. Must be validated BEFORE the pilot run, not after. Build a test suite of 20+ known GSM8K responses in various formats and verify the extractor handles all of them.

---

### Pitfall 3: HumanEval Sandbox Security and Execution Reliability

**What goes wrong:**
HumanEval requires executing arbitrary LLM-generated code. Two failure modes: (1) Security -- generated code can perform file I/O, network calls, infinite loops, or fork bombs that escape or crash the sandbox. (2) Reliability -- generated code may have correct logic but fail due to missing imports, wrong function signatures, or environment differences (Python version, available libraries). The OpenAI HumanEval repo itself warns: "This program exists to run untrusted model-generated code. Users are strongly encouraged not to do so outside of a robust security sandbox."

**Why it happens:**
Noisy prompts may cause the model to generate code with unusual imports, system calls, or infinite loops that it would not produce with clean prompts. The 20% noise level especially may produce prompts ambiguous enough that the model generates exploratory or defensive code patterns. At scale (16,000+ code executions), even rare pathological outputs become likely.

**How to avoid:**
- Use Docker containers or `firejail` with restricted capabilities: no network, read-only filesystem except `/tmp`, memory limit (256MB), CPU time limit (10 seconds per test case).
- Use `subprocess` with `timeout` parameter rather than `exec()` in the main process. Never `eval()` or `exec()` LLM-generated code in the grading process itself.
- Pre-validate generated code before execution: check for obvious dangerous patterns (`os.system`, `subprocess`, `open(`, `import socket`, `while True`). Log but still execute in sandbox -- the check is for telemetry, not blocking.
- Set `ulimit` restrictions: max file size, max processes, max open files.
- Handle execution failures gracefully: timeout = fail (not crash), import error = fail (not crash), syntax error = fail (not crash). Every execution must produce a result row in SQLite.

**Warning signs:**
- Grading process hangs or crashes during batch execution
- Disk fills up from generated code writing files
- Memory usage spikes during code execution phases
- Some prompts consistently cause timeouts (may indicate the noisy prompt is triggering infinite-loop code)

**Phase to address:**
Grading module implementation. The sandbox must be built and stress-tested before pilot. Run the sandbox against 50 adversarial code snippets (infinite loops, fork bombs, large allocations) to verify containment.

---

### Pitfall 4: Multiple Comparisons Inflation Without Correction

**What goes wrong:**
The experiment design produces hundreds of statistical tests: 200 prompts x 8 cells x 2 models x multiple pairwise comparisons. At alpha=0.05 without correction, you expect ~5% false positives. With 500 tests, that is 25 spurious "significant" results. Researchers then cherry-pick the significant ones for the paper, producing claims that do not replicate. This is the most common statistical mistake in LLM evaluation papers.

**Why it happens:**
The RDD correctly specifies Benjamini-Hochberg correction (Section 7.6), but implementation is where it breaks. Common errors: (1) applying BH correction within each sub-analysis but not across the entire paper, (2) running BH on p-values from different test types (GLMM coefficients mixed with McNemar's), (3) reporting uncorrected p-values in tables with a footnote about correction rather than reporting corrected values.

**How to avoid:**
- Define the "family" of comparisons BEFORE running any tests. The RDD should specify: "All pairwise comparisons reported in the paper constitute a single family for BH correction."
- Use `statsmodels.stats.multitest.multipletests(method='fdr_bh')` on the FULL vector of p-values from ALL tests reported in the paper, not per-section.
- Report BOTH raw and adjusted p-values in supplementary tables. Main text uses adjusted only.
- For the GLMM, the fixed-effect p-values are already controlled within the model. BH correction applies to the post-hoc pairwise comparisons (McNemar's tests across prompts).
- Pre-register the analysis plan: which comparisons will be run, which correction method, what alpha level. This prevents post-hoc test shopping.

**Warning signs:**
- Many results are "significant at p<0.05" but marginal (p=0.03-0.05)
- After BH correction, most results lose significance (the original findings were noise)
- Different analysis scripts apply different correction scopes

**Phase to address:**
Statistical analysis module implementation. The correction must be built into the analysis pipeline, not applied manually after the fact.

---

### Pitfall 5: Noise Injection Corrupts Semantics, Not Just Surface Form

**What goes wrong:**
Character-level noise at 20% can change the MEANING of a prompt, not just its surface form. "Sort the list in ascending order" with noise might become "Sort the list in descending order" if mutations hit the right characters. Similarly, ESL patterns can introduce genuine ambiguity: "Write function that sort list" is ambiguous about whether to sort in-place or return a new list. The experiment then measures "model fails on ambiguous prompt" rather than "model fails on noisy prompt" -- a confound.

**Why it happens:**
The noise generator treats all non-keyword characters as equally mutable. But some characters carry more semantic weight than others. The RDD's keyword protection helps but does not fully solve the problem: "ascending" is not a programming keyword but is semantically critical.

**How to avoid:**
- After noise injection, run a semantic similarity check between the noisy prompt and the clean prompt. If similarity drops below a threshold (e.g., 0.90 by embedding cosine similarity), flag the prompt for manual review.
- For the 20% noise level especially, manually review a random sample of 20 noisy prompts to verify the INTENT is preserved even if the surface form is degraded.
- Consider protecting "semantically critical" non-keyword terms (directional words, quantifiers, negation words) from mutation. Document this as a design decision.
- In analysis, control for semantic drift: if a noisy prompt's intent has changed, the accuracy drop is not attributable to noise resilience but to specification change.

**Warning signs:**
- Accuracy at 20% noise drops dramatically more than the 5% and 10% curve would predict (the "cliff" may be a semantic corruption artifact, not a noise tolerance threshold)
- Manual review of failed 20% prompts reveals the model answered the mutated question correctly -- it just was not the original question anymore
- The noise generator produces prompts that a human would also answer differently from the clean version

**Phase to address:**
Noise generator implementation and validation. Must include a semantic preservation check before the pilot run.

---

### Pitfall 6: Pre-Processor Cost Accounting Ignores Hidden Costs

**What goes wrong:**
The ROI calculation for the Sanitize+Compress intervention only counts the pre-processor's input/output tokens. But API calls have additional costs: (1) per-request overhead and minimum charges, (2) retry costs when the pre-processor call fails or times out, (3) latency cost (wall-clock time doubles because you make two sequential API calls), (4) the pre-processor may INCREASE token count if it "helpfully" expands abbreviations or adds context. Research shows hidden costs account for 20-40% of total LLM operational expenses beyond raw token fees.

**Why it happens:**
The RDD's cost model (Section 6) focuses on token-level accounting. But the paper's headline claim -- "net positive ROI" -- requires total-cost accounting. Reviewers will immediately ask about latency, retry overhead, and edge cases where the optimizer makes things worse.

**How to avoid:**
- Log EVERYTHING for every pre-processor call: wall-clock time, TTFT, TTLT, input tokens, output tokens, HTTP status code, retry count, cost.
- Compute "optimizer overhead" as: pre-processor cost + retry costs + any cases where the optimized prompt is LONGER than the original.
- Report the DISTRIBUTION of overhead, not just the mean. If 95% of prompts save tokens but 5% increase token count, report both.
- Include a "break-even analysis": at what noise level does the optimizer's accuracy recovery justify its cost? Below that noise level, the optimizer is a net cost.
- Track latency separately: even if token cost is net positive, if latency doubles, that matters for the paper's practical recommendations.

**Warning signs:**
- Mean token savings looks great but median is near zero (skewed by a few very verbose prompts)
- Pre-processor retry rate exceeds 5% (cost model is wrong)
- Pre-processor occasionally returns a longer prompt than the input

**Phase to address:**
Experiment harness implementation. Cost logging must be comprehensive from the first API call. The analysis module must compute total cost, not just token cost.

---

### Pitfall 7: Data Contamination in HumanEval and GSM8K Benchmarks

**What goes wrong:**
Both HumanEval and GSM8K are widely known benchmarks that are almost certainly present in the training data of Claude and Gemini. Research shows all tested LLMs exhibit a 5-14 percentage point drop in pass@1 on decontaminated HumanEval variants compared to the original, strongly indicating memorization. This means your "clean prompt baseline" may be artificially HIGH because the model has memorized the answers. When you inject noise, you are not just testing noise resilience -- you are testing whether noise breaks the model's pattern-matching to memorized solutions.

**Why it happens:**
These benchmarks are public, widely reproduced in blog posts, GitHub repos, and training corpora. The models have seen them. This is a known issue in the field, and GSM8K-Platinum was specifically created to address GSM8K contamination by fixing label errors in the original dataset.

**How to avoid:**
- Acknowledge contamination risk explicitly in the paper. This is standard practice and reviewers will expect it.
- Frame the finding correctly: "We measure noise sensitivity on prompts where models achieve high baseline performance. Contamination may inflate baselines but does not invalidate the RELATIVE degradation under noise." The key metric is the DELTA, not the absolute level.
- Include the 20 real-world noisy prompts (Section 9.1 of the RDD) as a contamination-free validation set. These are novel prompts not in any training corpus.
- Consider testing on MBPP (less contaminated than HumanEval) as a robustness check. The RDD already includes MBPP.
- Report whether the noise sensitivity curve differs between "easy" prompts (likely memorized) and "hard" prompts (less likely memorized). If noise breaks memorized solutions more than genuine reasoning, that is itself an interesting finding.

**Warning signs:**
- Clean baseline accuracy is suspiciously high (>95% on HumanEval for both models)
- Noise sensitivity is HIGHER on "easy" prompts than "hard" ones (noise disrupts memorization pattern-matching)
- Models produce solutions that are character-for-character identical to known HumanEval solutions in the clean condition

**Phase to address:**
Benchmark curation and pilot analysis. Acknowledge in the paper from the start. Use pilot results to assess contamination severity.

---

### Pitfall 8: Seed Management Across the Full Pipeline

**What goes wrong:**
The project has multiple sources of randomness that all need deterministic seeds: noise generation, prompt sampling, experiment ordering, bootstrap resampling in analysis. A common mistake is seeding the noise generator but not the experiment scheduler, so prompts run in different orders across runs, hitting different API server states and potentially different model versions within an update window. Another mistake: using the same seed for all noise levels, producing correlated mutations across conditions.

**Why it happens:**
Python's random module uses a global state. Calling `random.seed(42)` in one module does not prevent another module from reseeding or consuming random numbers. NumPy and Python `random` have separate states. Researchers test seed behavior in unit tests (single-module) but not across the full pipeline.

**How to avoid:**
- Use INDEPENDENT `random.Random()` instances for each source of randomness, not the global state. The noise generator gets its own `Random(seed=noise_seed)`, the sampler gets `Random(seed=sample_seed)`, etc.
- Define a SEED REGISTRY in a config file: `{"noise_seed": 42, "sample_seed": 43, "bootstrap_seed": 44}`. Document why each seed exists.
- In unit tests, verify that calling the noise generator with the same seed and the same input produces byte-identical output, regardless of what other code runs before it.
- For NumPy operations in analysis, use `numpy.random.Generator(numpy.random.PCG64(seed))` (the modern API), not `numpy.random.seed()` (deprecated global state).
- Log the seed values in the SQLite results database alongside every experiment run.

**Warning signs:**
- Rerunning the pilot produces different noisy prompts than the first run
- Bootstrap confidence intervals differ between runs (analysis randomness is not seeded)
- Two noise levels produce suspiciously similar mutation patterns (seeds are correlated or identical)

**Phase to address:**
Core infrastructure (noise generator, experiment harness). Must be verified in pilot. The seed registry should be defined before any code is written.

---

### Pitfall 9: API Rate Limits and Retry Logic Introduce Systematic Bias

**What goes wrong:**
When hitting rate limits, naive retry logic introduces delays that change the experimental conditions. If Claude rate-limits at 60 RPM and Gemini at 300 RPM, Claude experiments run 5x slower with longer gaps between calls. If the retry logic backs off exponentially, later prompts in the batch may hit a different model checkpoint if the provider deploys an update mid-experiment. Worse: if retries are not logged, the cost accounting is wrong and some prompts have different latency profiles that contaminate timing analysis.

**Why it happens:**
Rate limits are documented but researchers plan for throughput, not for the interaction between rate limits and experimental design. A 20,000-call experiment at 60 RPM takes ~5.5 hours for Claude alone. Over 5+ hours, model updates, server-side changes, and network conditions vary.

**How to avoid:**
- Implement rate limiting PROACTIVELY, not reactively. Use a token bucket or leaky bucket rate limiter that stays below the API limit rather than hitting the limit and backing off.
- Log EVERY API call's timestamp, response time, HTTP status, and retry count. Make retry count a column in the SQLite schema.
- Randomize prompt order within each condition to prevent systematic bias from time-of-day effects.
- Run both models in INTERLEAVED fashion (not all Claude then all Gemini) to ensure both models experience similar time-of-day conditions.
- Set a maximum retry count (3) and mark prompts that exhaust retries as "API_FAILURE" not "FAIL." These are missing data, not negative results.
- Pin model versions via the API (e.g., `claude-sonnet-4-20250514`, not `claude-sonnet-4-latest`) to prevent mid-experiment model updates.

**Warning signs:**
- Experiment takes much longer than estimated (hitting rate limits constantly)
- Later conditions in the batch show different accuracy patterns than earlier ones
- Retry rate exceeds 10% for one provider but not the other
- Cost is 30%+ over budget (retries are consuming tokens)

**Phase to address:**
Experiment harness implementation. Rate limiting and retry logic must be built into the execution layer. Test against the API with a small batch before pilot.

---

### Pitfall 10: Prompt Repetition Doubles Input Cost, Not "Zero Cost"

**What goes wrong:**
The RDD describes prompt repetition as a "zero-cost intervention" based on the Leviathan et al. claim that it "adds no output tokens or meaningful latency." But it DOUBLES input tokens, and input tokens are priced. For Claude Sonnet, input is $3/MTok. Doubling 200-token prompts across 2,000 calls adds ~$1.20 -- small for research, but the paper cannot claim "zero cost" without qualification. More importantly, for the cost-benefit analysis comparing interventions, prompt repetition has a non-zero token cost that must be compared to the Sanitize+Compress cost.

**Why it happens:**
The Google paper focuses on accuracy improvement and frames "zero cost" as "no external model call." This is true but incomplete for a cost-benefit analysis.

**How to avoid:**
- Track input token count for the repeated prompt and compute the additional cost.
- In the paper, distinguish "zero engineering cost" (no optimizer needed) from "zero inference cost" (still doubles input tokens).
- Include prompt repetition in the same cost-benefit framework as other interventions. Its cost is `2x input tokens` with no pre-processor call. Compare this to Sanitize+Compress, which has a pre-processor call but potentially FEWER total tokens.
- For the "break-even" analysis: at what prompt length does repetition become more expensive than sanitization?

**Warning signs:**
- Paper claims "zero cost" and a reviewer points out the doubled input tokens
- Cost comparison table excludes input token cost for the repetition condition

**Phase to address:**
Analysis module implementation. Cost accounting must treat all interventions uniformly.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Flat JSON results instead of SQLite | Faster to implement | Cannot query across conditions, no ACID, analysis scripts become fragile | Never -- the RDD mandates SQLite for good reason |
| `print()` instead of `logging` | Quick debugging | Cannot filter log levels, no timestamps, cannot redirect to file for long runs | Never -- 5+ hour experiment runs need structured logging |
| Global `random.seed()` instead of instance seeds | Fewer lines of code | Non-reproducible when modules interact, impossible to debug seed issues | Never -- use `random.Random(seed)` instances |
| Hardcoded model version strings | Faster initial development | Model string appears in 10+ places, one missed update invalidates experiment | Only in pilot -- must centralize before full run |
| Skipping BH correction "for now" | Faster initial analysis | Every p-value in draft tables is wrong, rewriting the paper is expensive | Never -- build it into the analysis pipeline from day one |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Anthropic API | Using `claude-sonnet-4-latest` which auto-updates | Pin exact version: `claude-sonnet-4-20250514`. Check version string in first API response. |
| Anthropic API | Not handling `overloaded_error` (529) status | Implement exponential backoff with jitter. Log as retry, not failure. |
| Google Gemini API | Assuming `temperature=0` behaves identically to Anthropic | Gemini uses `temperature=0.0` in `generation_config`. Verify parameter name and behavior per SDK version. |
| Google Gemini API | Not handling safety filter blocks as distinct from failures | Gemini may refuse to process noisy prompts that trigger safety filters. Log as `SAFETY_BLOCK`, not `FAIL`. Exclude from accuracy analysis but report the count. |
| SQLite | Writing results from multiple threads/processes simultaneously | Use WAL mode (`PRAGMA journal_mode=WAL`) or serialize writes through a single connection. Python `sqlite3` module is not thread-safe by default. |
| HumanEval sandbox | Running generated code in the same Python process as the grading harness | Use `subprocess` with `timeout`. Never `exec()` in the main process. |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Sequential API calls with no parallelism | Full experiment takes 20+ hours | Use async HTTP with rate-limited concurrency (e.g., `asyncio.Semaphore(10)`) | At ~2,000 calls per model (pilot is fine sequential; full run is not) |
| Loading full SQLite DB into pandas for every analysis query | Analysis script takes minutes, OOM on large result sets | Use SQL queries with WHERE clauses, only load needed columns | At ~20,000 rows with full response text (several GB) |
| Storing full response text in SQLite without compression | Database grows to multiple GB | Store responses in a separate table, compress with zlib if needed, or use TEXT with lazy loading | At ~20,000 responses averaging 500 tokens each |
| Running all 5 repetitions before checking any results | Discover grading bug after 10,000 calls and $50 spent | Run 1 repetition of all conditions first, verify grading, then run remaining 4 | Immediately -- catch bugs in pilot |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| API keys in code or git history | Key exposure, unauthorized charges | `.env` file with `.gitignore`, `os.environ.get()` only. Run `git log --all -p -- '*.py' | grep -i 'key'` before any push. |
| Executing LLM-generated code without sandboxing | Arbitrary code execution, data loss, network exfiltration | Docker/firejail with no-network, memory limits, timeout. Never `exec()` in main process. |
| Storing raw LLM responses without sanitization in analysis notebooks | Notebook rendering could execute injected HTML/JS in response text | Escape all LLM response text before rendering in notebooks or HTML reports. |

## "Looks Done But Isn't" Checklist

- [ ] **Noise generator:** Often missing protection for format instructions (e.g., "Answer with ####") -- verify noise does not corrupt the answer format directive
- [ ] **GSM8K grading:** Often missing normalization for number formats (commas, decimals, negative signs, percentages) -- verify against 20+ format variants
- [ ] **HumanEval grading:** Often missing timeout handling for infinite loops -- verify sandbox kills after 10 seconds and records FAIL
- [ ] **Cost tracking:** Often missing pre-processor retry costs -- verify total cost includes ALL API calls, not just successful ones
- [ ] **Stability measurement:** Often missing baseline CR for clean prompts -- verify you report noise-induced CR change RELATIVE to clean baseline
- [ ] **Bootstrap CIs:** Often missing seed management -- verify rerunning analysis produces identical confidence intervals
- [ ] **GLMM convergence:** Often missing convergence checks -- verify the model actually converged (check warnings from `statsmodels`)
- [ ] **Experiment matrix:** Often missing the clean baseline condition -- verify clean prompts x 2 models x 5 reps are in the matrix, not assumed from a separate run

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Grading bug discovered after full run | LOW | Regrading from stored responses is cheap if full response text is logged. Rerun `grade_results.py` on existing data. No new API calls needed. |
| Seed inconsistency discovered mid-experiment | HIGH | Must rerun affected conditions from scratch. If noise was non-deterministic, ALL noisy conditions are suspect. |
| Missing BH correction in submitted paper | MEDIUM | Recompute all p-values with correction. Some findings may lose significance. Rewrite affected claims. |
| API model version changed mid-experiment | HIGH | Data from before and after the change cannot be combined. Must rerun the shorter segment with the new version, or discard and rerun entirely. Pin versions to prevent. |
| Sandbox escape during HumanEval execution | HIGH | Assess damage (file changes, network activity). Rebuild execution environment. Add the escaped code pattern to the pre-execution filter. Rerun affected prompts. |
| Cost overrun (budget exceeded before full run completes) | MEDIUM | Pause execution. Analyze partial results to determine if sufficient statistical power exists. If not, prioritize conditions by importance and run remaining budget on highest-priority cells. |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Temperature non-determinism | Experiment harness design | Pilot run shows expected CR variance on clean prompts |
| GSM8K regex extraction | Grading module implementation | Test suite of 20+ answer format variants all pass |
| HumanEval sandbox security | Grading module implementation | Adversarial code test suite (loops, forks, I/O) all contained |
| Multiple comparisons inflation | Analysis module implementation | All reported p-values pass through BH correction in a single call |
| Noise corrupts semantics | Noise generator implementation | Semantic similarity check on sample of 20% noise prompts |
| Pre-processor cost accounting | Experiment harness implementation | Cost log includes pre-processor calls, retries, and failures |
| Data contamination | Benchmark curation / paper writing | Paper includes contamination acknowledgment and delta-focused framing |
| Seed management | Core infrastructure (first phase) | Rerunning pilot produces byte-identical noisy prompts |
| API rate limits and bias | Experiment harness implementation | Prompt order is randomized; retry count logged; models interleaved |
| Prompt repetition cost | Analysis module implementation | Cost comparison table includes input token cost for all interventions |

## Sources

- [Pitfalls of Evaluating Language Models with Open Benchmarks (ArXiv 2507.00460)](https://arxiv.org/abs/2507.00460) -- benchmark gaming, data leakage, context truncation
- [Non-Determinism of "Deterministic" LLM Settings (ArXiv 2408.04667)](https://arxiv.org/html/2408.04667v5) -- temperature=0 non-determinism
- [GSM8K-Platinum: Revealing Performance Gaps (gradient science)](https://gradientscience.org/gsm8k-platinum/) -- GSM8K label errors and contamination
- [Investigating Reproducibility Challenges in LLM Bugfixing on HumanEvalFix](https://www.mdpi.com/2674-113X/4/3/17) -- HumanEval reproducibility
- [Reflections on Reproducibility of Commercial LLM Performance](https://arxiv.org/html/2510.25506v3) -- API version changes, reproducibility
- [A Statistical Approach to Model Evals (Anthropic)](https://www.anthropic.com/research/statistical-approach-to-model-evals) -- statistical rigor in LLM evaluation
- [Does Temperature 0 Guarantee Deterministic Outputs?](https://www.vincentschmalbach.com/does-temperature-0-guarantee-deterministic-llm-outputs/) -- floating-point non-determinism
- [How to Get Consistent LLM Outputs in 2025](https://www.keywordsai.co/blog/llm_consistency_2025) -- practical determinism strategies
- [OpenAI HumanEval repo security warning](https://github.com/openai/human-eval) -- sandbox execution risks
- [Simulating Training Data Leakage in Multiple-Choice Benchmarks](https://arxiv.org/html/2505.24263v1) -- 5-14% score inflation from contamination
- RDD v4.0 (`docs/RDD_Linguistic_Tax_v4.md`) -- project-specific experimental design

---
*Pitfalls research for: LLM prompt noise/optimization benchmarking research*
*Researched: 2026-03-19*
