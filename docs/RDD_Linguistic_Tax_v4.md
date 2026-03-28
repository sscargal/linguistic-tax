# Research Design Document (RDD)

## Quantifying the "Linguistic Tax": Prompt Noise, Prompt Bloat, and the Case for Automated Prompt Optimization in LLM Reasoning

**Version:** 4.0  
**Date:** 2026-03-19  
**Status:** Final  
**Target Publication:** ArXiv (cs.CL / cs.AI)

### Changelog (v3.0 -> v4.0)
    - ADDED Section 5.4: Prompt Repetition as Intervention (Google paper)
    - ADDED Section 6 addendum: Meta-Prompting / AI-Written Prompts
    - ADDED Section 10.6: Skill-Creator Evaluation Pattern
    - ADDED Section 22: Execution Platform (Claude Code CLI vs API)
    - ADDED Section 23: Expanded Future Work Catalog
    - ADDED 5th control intervention to experimental matrix (Section 4.1)
    - ADDED 20 real-world noisy prompts to data collection (Section 9.1)
    - ADDED Google "Prompt Repetition" paper to literature review
    - ADDED noise level justification (why cap at 20%)
    - UPDATED Section 7.3: added paper citation for stability research
    - UPDATED Section 21: Adversarial review with new mitigations
    - CLARIFIED: Research uses American English; British English
      variations noted as future work

### Changelog (v2.0 -> v3.0)
    - ADDED Section 8.3: Latency & Cost Instrumentation (TTFT, TTLT,
      full cost-benefit accounting for the optimizer itself)
    - ADDED Section 12: Grammarly Personas & the "AI Prompt Persona"
      Opportunity (browser extension concept, commercial angle)
    - ADDED Section 19: Literature Review (real ArXiv papers, surveys,
      benchmarks with citations)
    - ADDED Section 20: Adversarial Review (red-team critique of the
      entire RDD, weaknesses, and mitigations)
    - UPDATED Execution log schema with TTFT, TTLT, pre-proc cost fields
    - UPDATED Cost-benefit model to account for overhead vs. savings
      threshold ("break-even noise level")
    - UPDATED Whitepaper outline with Grammarly and cost sections
    - UPDATED Risk register with optimizer-overhead risks

### Changelog (v1.0 -> v2.0)
    - ADDED Section 7: Statistical Analysis Framework (replaces v1.0 s8.3)
    - ADDED Section 10: Autonomous Execution Strategy (Karpathy Loop)
    - ADDED Stability vs. Correctness separation throughout
    - ADDED GLMM, bootstrap, Kendall's tau, McNemar's, BH correction
    - ADDED research_program.md concept for overnight agent runs
    - UPDATED Roadmap to three-phase hybrid (human -> semi-auto -> auto)
    - UPDATED Execution log schema with repetition & stability fields
    - UPDATED Whitepaper outline with new statistical methods section
    - UPDATED Risk register with agent-execution risks
    - UPDATED Tools & infrastructure with agent tooling

---

## 1. Problem Statement

Large Language Models (LLMs) are deployed as reasoning engines for coding,
mathematics, logic, and decision-making. Their interface is natural language —
but "natural" language is messy. Users produce prompts that are noisy (typos,
grammatical errors, L1 transfer artifacts) and bloated (redundant context,
duplicated instructions, verbose phrasing).

Both problems impose hidden costs:

    +------------------------------------------------------------------+
    |                     THE TWO-HEADED PROBLEM                       |
    +------------------------------------------------------------------+
    |                                                                   |
    |   NOISE (Linguistic Tax)         BLOAT (Token Tax)               |
    |   ~~~~~~~~~~~~~~~~~~~~~~~~       ~~~~~~~~~~~~~~~~~~~~~~~~        |
    |   - Character-level typos        - Duplicated instructions       |
    |   - Grammatical errors           - Redundant context             |
    |   - L1 transfer patterns         - Verbose phrasing              |
    |   - Ambiguous phrasing           - Copy-pasted repetition        |
    |                                                                   |
    |   Impact: Degrades reasoning     Impact: Wastes tokens/cost,     |
    |   accuracy; widens gap for       dilutes attention, increases    |
    |   non-native speakers            latency                         |
    |                                                                   |
    +-------------------+------------------+---------------------------+
                        |                  |
                        v                  v
               +--------+------------------+---------+
               |  COMBINED EFFECT ON LLM OUTPUT      |
               |  - Lower accuracy on hard tasks      |
               |  - Higher inference cost              |
               |  - Increased hallucination risk       |
               |  - Inequitable access (ESL penalty)   |
               +--------------------------------------+

Current LLM interfaces (chat UIs, coding assistants, CLI tools) provide no
native "prompt sanitization" or compression layer. Users bear full
responsibility for prompt quality, and most are unaware of the cost.

**This study asks three questions:**

1. How much does prompt noise degrade reasoning accuracy, and does the
   degradation follow a linear or threshold curve?
2. How much can automated prompt compression reduce token count while
   preserving semantic intent and output quality?
3. Can a lightweight "prompt optimizer" (sanitizer + compressor) recover
   lost accuracy AND reduce cost simultaneously?


---

## 2. Hypotheses

**H1 — The Noise Cliff:**
Reasoning accuracy degrades non-linearly as character-level and syntactic
noise increases. Below a threshold (~5% character error rate), models are
resilient. Above it, accuracy drops sharply — a "cliff" rather than a slope.

    Accuracy
    100% |*****
         |      ****
         |          **
         |            *
     50% |             *
         |              **
         |                ****
         |                    *****
      0% +-----|------|------|-------> Noise Level
              5%    10%    15%   20%
                    ^
                    |
              "The Cliff"
              (Hypothesized threshold where
               reasoning breaks down)

**H2 — The Compression Dividend:**
User prompts contain 20-40% redundant or duplicated content. Automated
compression can reduce token count by at least 25% with no measurable
loss in output accuracy (semantic similarity > 0.95 vs. original output).

**H3 — The Recovery Rate:**
An automated two-stage "prompt optimizer" (Stage 1: sanitize noise;
Stage 2: compress bloat) can recover >80% of accuracy lost to noise
AND reduce token cost by >25%, yielding a net positive ROI even after
accounting for the optimizer's own token overhead.

**H4 — The ESL Penalty:**
Syntactic noise from L1 transfer patterns (e.g., article omission,
preposition confusion) causes greater accuracy degradation than
equivalent character-level noise from native-speaker typos, because
syntactic errors disrupt the model's attention at a higher level of
abstraction.

**H5 — The Stability Illusion (NEW in v2.0):**
Models may exhibit high run-to-run stability (consistency) on noisy
prompts while producing systematically WRONG answers. Stability and
correctness must be measured independently; stability alone is not
evidence of robustness.

    +-----------------------------------------------------------+
    |  THE STABILITY-CORRECTNESS MATRIX                         |
    +-----------------------------------------------------------+
    |                                                           |
    |               Correct          Incorrect                  |
    |             +--------------+--------------+               |
    |   Stable    | ROBUST       | CONFIDENTLY  |               |
    |             | (ideal)      | WRONG        |               |
    |             |              | (dangerous)  |               |
    |             +--------------+--------------+               |
    |   Unstable  | LUCKY        | BROKEN       |               |
    |             | (unreliable) | (obvious)    |               |
    |             +--------------+--------------+               |
    |                                                           |
    |   Noise may push models from "Robust" into               |
    |   "Confidently Wrong" — stable but incorrect.            |
    |   This is WORSE than "Broken" because users              |
    |   won't notice the failure.                              |
    +-----------------------------------------------------------+


---

## 3. Key Definitions

**Prompt Noise:**
Any deviation from "clean" English in the user's input. We distinguish
two types:

    TYPE A: CHARACTER-LEVEL NOISE          TYPE B: SYNTACTIC NOISE
    (Native-speaker typos)                 (L1 transfer patterns)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    - Adjacent key hits (teh -> the)       - Article omission (Mandarin)
    - Character omission (acount)            "Please write function"
    - Character doubling (helllo)          - Preposition confusion (Spanish)
    - Character transposition (form/from)    "Depend of the input"
                                           - Tense/aspect errors (Yoruba)
                                             "I am work on this since May"

**Prompt Bloat:**
Redundant or unnecessarily verbose content in a prompt that consumes
tokens without adding semantic value. Categories:

    BLOAT TYPE              EXAMPLE
    ~~~~~~~~~~~~~~~~~~~~    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Exact duplication       Same instruction repeated verbatim
    Paraphrase duplication  Same intent restated in different words
    Verbose phrasing        "I would like you to please go ahead and"
                            vs. "Please"
    Unnecessary hedging     "If possible, could you maybe try to..."
    Redundant context       Pasting the same background in every turn

**Prompt Optimizer:**
A two-stage automated pre-processor:

    +------------------+     +------------------+     +-----------+
    |  User's Raw      | --> |  STAGE 1:        | --> | STAGE 2:  |
    |  Prompt          |     |  SANITIZE        |     | COMPRESS  |
    |  (noisy, bloated)|     |  (fix noise)     |     | (cut fat) |
    +------------------+     +------------------+     +-----------+
                                                            |
                                                            v
                                                  +------------------+
                                                  |  Optimized       |
                                                  |  Prompt          |
                                                  |  (clean, lean)   |
                                                  +------------------+
                                                            |
                                                            v
                                                  +------------------+
                                                  |  LLM             |
                                                  |  (reasoning)     |
                                                  +------------------+

**Stability (NEW in v2.0):**
The degree to which a model produces the same output across repeated
runs of the same prompt. Measured separately from correctness.

**Correctness:**
Whether the model's output matches the ground-truth answer, regardless
of whether the output is stable across runs.


---

## 4. Experimental Design

### 4.1 Overview: 2x4 Factorial + Compression Study

We use a focused design with TWO independent experiments that share
the same prompt dataset.

    EXPERIMENT 1: NOISE & RECOVERY (3x5 Factorial)
    ================================================

    Noise Type (rows) x Intervention (columns)

                      | Raw      | Self-     | Pre-Proc  | Pre-Proc   | Prompt     |
                      | (no fix) | Correct   | Sanitize  | Sanitize + | Repetition |
                      |          | ("Fix my  | (external | Compress   | (x2 input) |
                      |          |  prompt") | LLM call) |            | (NEW v4.0) |
    ==================+=========+===========+===========+============+============+
    Clean:            |         |           |           |            |            |
    (no noise)        | Cell 0  | Cell 0a   | Cell 0b   | Cell 0c    | Cell 0d    |
    ------------------+---------+-----------+-----------+------------+------------+
    Type A:           |         |           |           |            |            |
    Character Noise   |  Cell 1 |  Cell 2   |  Cell 3   |  Cell 4    |  Cell 5    |
    (5%, 10%, 20%)    |         |           |           |            |            |
    ------------------+---------+-----------+-----------+------------+------------+
    Type B:           |         |           |           |            |            |
    Syntactic Noise   |  Cell 6 |  Cell 7   |  Cell 8   |  Cell 9    |  Cell 10   |
    (L1 patterns)     |         |           |           |            |            |
    ------------------+---------+-----------+-----------+------------+------------+

    Cell 0 (Raw + Clean) is the PRIMARY BASELINE. All other cells are
    compared against it to measure degradation or improvement.

    Cells 0a-0d measure INTERVENTION OVERHEAD on clean text. If an
    intervention scores lower than Cell 0, it has an inherent cost
    even when there's nothing to fix. This is important for real-world
    deployment where not all user prompts are noisy.

    NOTE (v4.0): Prompt Repetition is inspired by Leviathan et al.
    (2025), "Prompt Repetition Improves Non-Reasoning LLMs" (ArXiv:
    2512.14982). The input is simply duplicated: <QUERY><QUERY>.
    This is a ZERO-COST intervention (no external model call) that
    exploits causal attention by allowing all prompt tokens to attend
    to all other prompt tokens. It doubles input tokens but Google
    reports no increase in output tokens or latency. We include it
    as a fascinating control: does naive repetition recover as much
    accuracy as intelligent sanitization?

    EXPERIMENT 2: COMPRESSION STUDY (via compress_only intervention)
    ================================================================

    Takes CLEAN prompts and applies compression only (no sanitization).
    Implemented as the `compress_only` intervention in the experiment
    matrix, which only runs on clean noise conditions. Measures:
    - Token reduction (%)
    - Accuracy preservation (delta vs. uncompressed)
    - Semantic similarity of outputs (BERTScore)


### 4.2 Models Under Test

We test two frontier models to check generalizability:

    +-------------------+--------------------+
    |  Model A          |  Model B           |
    |  Claude Sonnet    |  Gemini 1.5 Pro    |
    +-------------------+--------------------+
    |  Why: Strong       |  Why: Strong       |
    |  reasoning, widely |  reasoning,        |
    |  used in coding    |  different arch    |
    |  assistants        |  (MoE vs. dense)   |
    +-------------------+--------------------+

NOTE: We deliberately limit to two models. Adding more models
multiplies the experiment matrix without adding proportional
insight for a first paper. Model breadth is future work.

IMPORTANT: Pin exact model version strings (e.g.,
"claude-sonnet-4-20250514") and document them. If a model
updates mid-study, the baseline is invalidated.


### 4.3 Benchmark Selection

We select tasks where CORRECTNESS IS VERIFIABLE (not subjective):

    BENCHMARK       DOMAIN          SIZE    WHY
    ~~~~~~~~~~~~    ~~~~~~~~~~~~~~  ~~~~    ~~~~~~~~~~~~~~~~~~~~~~~~
    HumanEval       Code generation  164    Industry standard, auto-
                                            graded pass/fail
    MBPP            Code generation  974    Broader Python coverage
                    (subset: 200)
    GSM8K           Math reasoning   ~1300  Tests chain-of-thought;
                    (subset: 200)           auto-gradable

    Total prompts per condition: ~200 (sampled subset)
    Total experimental runs (updated for stability measurement):

    200 prompts x 8 cells x 2 models x 5 repetitions = 16,000  (Exp 1)
    200 prompts x 2 models x 5 repetitions             =  2,000  (Exp 2)
    200 prompts x 2 models x 5 repetitions             =  2,000  (Baseline)
                                                         -------
                                              TOTAL:    ~20,000 LLM calls

    NOTE: Repetition count increased from 3 to 5 in v2.0 to enable
    meaningful stability measurement and bootstrap analysis.


---

## 5. Noise Injection Methodology

### 5.1 Type A: Character-Level Noise Generator

A Python module that applies controlled, reproducible mutations:

    INPUT: "Please write a function that sorts a list"
                            |
                            v
              +----------------------------+
              |  MUTATION ENGINE           |
              |                            |
              |  Parameters:               |
              |    error_rate: 0.05-0.20   |
              |    seed: (reproducible)     |
              |                            |
              |  Operations (weighted):    |
              |    40% Adjacent key swap   |
              |    25% Character omission  |
              |    20% Character doubling  |
              |    15% Transposition       |
              +----------------------------+
                            |
                            v
    5%:  "Please write a functiom that sorts a list"
    10%: "Please wrte a functiom taht sorts a lsit"
    20%: "Pleas wrte a functiom taht srots a lsit"

    KEY CONSTRAINT: Mutations apply ONLY to non-keyword tokens.
    Technical terms (function names, operators, benchmark-specific
    vocabulary) are protected to isolate the effect of "human"
    typos from "broken specifications."

    WHY CAP AT 20%? (v4.0)

    We test 5%, 10%, and 20% character error rates. We deliberately
    do NOT test 30%, 40%, 50%, or higher for three reasons:

    1. ECOLOGICAL VALIDITY: Real human typo rates rarely exceed
       10-15% even for fast, careless typists. A 20% error rate
       means roughly 1 in 5 characters is wrong — this is already
       at the extreme end of what a human would actually produce
       without noticing. At 40%+, the text becomes essentially
       unreadable even to humans, making it an unrealistic test
       of "robustness to human noise."

    2. PRIOR ART: Gan et al. (2024) showed that 8 character edits
       in a GSM8K prompt (roughly 5-8% error rate) drops Mistral-7B
       accuracy from 43.7% to 19.2%. MulTypo (2025) tested 10%
       and 40% — at 40%, performance collapses so completely that
       the measurement becomes uninformative. The interesting
       science is in the 5-20% range where the degradation curve
       has diagnostic shape.

    3. DIMINISHING RETURNS: If a model fails at 20%, showing it
       also fails at 40% adds no actionable insight. The paper's
       value is in finding the THRESHOLD, not proving that
       eventually everything breaks.

    EXCEPTION: We include 30% as an OPTIONAL additional data
    point if the 5-10-20% curve suggests the cliff falls between
    20-30%. This decision is made after pilot results.


### 5.2 Type B: Syntactic Noise Generator

Based on documented L1 transfer error patterns from second-language
acquisition research:

    L1 SOURCE     ERROR PATTERN              EXAMPLE TRANSFORMATION
    ~~~~~~~~~~~~  ~~~~~~~~~~~~~~~~~~~~~~~~   ~~~~~~~~~~~~~~~~~~~~~~~~
    Mandarin      Article omission           "Write function that
                                              sorts list"
    Spanish       Preposition confusion      "Write a function for
                                              sort a list"
    Japanese      Topic-comment structure     "List, please write
                                              function that sorts"
    Mixed ESL     Tense/aspect errors        "Please writing function
                                              that sort a list"

    Implementation: Rule-based transformation templates applied
    to clean prompts. Each L1 pattern is a separate configuration
    file to ensure linguistic accuracy.

    CRITICAL: These patterns MUST be validated against published
    L2 English error corpora (e.g., Cambridge Learner Corpus
    categories) to withstand peer review.


### 5.3 Prompt Compression Module

Operates on CLEAN prompts to isolate the compression effect:

    INPUT PROMPT (142 tokens):
    "I need you to write a Python function. The function should
     take a list as input. The function should sort the list.
     Please make sure the function sorts the list in ascending
     order. The function should return the sorted list. Can you
     write this function for me? I need it to handle edge cases.
     Make sure it handles empty lists and single-element lists."

                            |
                            v
              +----------------------------+
              |  COMPRESSION ENGINE        |
              |                            |
              |  Step 1: Deduplication     |
              |    Identify semantically   |
              |    equivalent sentences    |
              |                            |
              |  Step 2: Condensation      |
              |    Merge remaining intent  |
              |    into minimal phrasing   |
              |                            |
              |  Step 3: Validation        |
              |    Embedding similarity    |
              |    vs. original > 0.95     |
              +----------------------------+
                            |
                            v
    COMPRESSED PROMPT (47 tokens):
    "Write a Python function that sorts a list in ascending
     order and returns it. Handle edge cases: empty lists
     and single-element lists."

    Token reduction: 67%
    Semantic similarity: 0.97


### 5.4 Prompt Repetition: A Zero-Cost Intervention (NEW v4.0)

Leviathan, Kalman, and Matias (Google Research, 2025) demonstrated
that simply repeating the input prompt — transforming <QUERY> into
<QUERY><QUERY> — improves non-reasoning LLM performance across
Gemini, GPT, Claude, and Deepseek models (47 wins out of 70 tests,
zero losses).

    MECHANISM:

    In causal (left-to-right) language models, early tokens
    CANNOT attend to later tokens. This means token ordering
    in the prompt matters:

    Original:    [A] [B] [C] [D] [E] --> [response]
                  A sees nothing before it
                  B sees only A
                  E sees A,B,C,D

    Repeated:    [A] [B] [C] [D] [E] [A'] [B'] [C'] [D'] [E'] --> [resp]
                  A' sees A,B,C,D,E (full context!)
                  B' sees A,B,C,D,E,A'
                  Every token in the 2nd copy attends to ALL tokens

    RELEVANCE TO OUR STUDY:

    Prompt repetition is a ZERO-COST intervention (no external
    model call, no sanitization logic). It doubles input tokens
    but adds no output tokens or meaningful latency (the extra
    tokens are processed in the parallelizable prefill stage).

    CRITICAL QUESTION: If a noisy prompt is repeated, does the
    model's ability to attend to all tokens in the second copy
    HELP it "self-correct" the noise? If so, this is the cheapest
    possible robustness intervention — no optimizer needed, just
    echo the prompt.

    We add Prompt Repetition as a 5th intervention column in our
    experimental matrix to directly compare against our sanitize/
    compress interventions.


---

## 6. Intervention Definitions

Each "intervention" is a distinct prompt-processing strategy:

    INTERVENTION        MECHANISM                   TOKEN OVERHEAD
    ~~~~~~~~~~~~~~~~~~  ~~~~~~~~~~~~~~~~~~~~~~~~~~  ~~~~~~~~~~~~~~
    Raw                 No processing. Noisy        0
                        prompt goes directly to
                        the model.

    Self-Correct        Prepend instruction:         ~15 tokens
                        "First, correct any          (added to every
                        spelling/grammar errors       prompt)
                        in my prompt, then
                        execute it."

    Pre-Proc Sanitize   External LLM call to a       ~50-100 tokens
                        fast model (e.g., Haiku       (separate API call)
                        or Flash) that returns a
                        cleaned version of the
                        prompt before the main
                        model sees it.

    Pre-Proc Sanitize   Same as above, PLUS the      ~50-100 tokens
    + Compress          fast model also removes       (separate API call,
                        redundancy and compresses     but output is
                        the prompt.                   SHORTER)

    THE KEY QUESTION FOR THE PAPER:

    Does the combined Sanitize+Compress intervention produce
    a NET TOKEN SAVINGS even after accounting for its own
    overhead?

    +--------------------------------------------------+
    |  NET COST CALCULATION                            |
    |                                                  |
    |  Overhead = tokens consumed by pre-processor     |
    |  Savings  = tokens reduced in main prompt        |
    |                                                  |
    |  If Savings > Overhead:                          |
    |    --> Net positive ROI                          |
    |    --> Users get BETTER results AND pay LESS     |
    |    --> This is the headline finding              |
    +--------------------------------------------------+


### 6.2 Meta-Prompting: Can AI Write the Perfect Prompt? (NEW v4.0)

An alternative intervention: instead of fixing the USER'S noisy prompt,
have the LLM generate an OPTIMAL prompt from the user's noisy intent.

    USER'S NOISY PROMPT:
    "pleas writ a python funciton taht sorts a list
     in ascendng order and retunrs it handle edge cases"

                        |
                        v
    META-PROMPT INSTRUCTION:
    "The following prompt was written by a user. It may contain
     typos, grammatical errors, or unclear phrasing. Rewrite it
     as the IDEAL prompt that would produce the best possible
     response from an LLM. Be precise, concise, and unambiguous."

                        |
                        v
    AI-GENERATED OPTIMAL PROMPT:
    "Write a Python function that accepts a list of comparable
     elements, sorts it in ascending order, and returns the
     sorted list. Handle edge cases: empty list (return []),
     single element (return as-is), already sorted (no-op),
     and None/mixed types (raise TypeError)."

    The AI-generated prompt is BETTER than the original clean
    prompt because it adds implicit requirements the user likely
    intended. This is not just "correction" — it is "enhancement."

    EXPERIMENTAL QUESTION: Does a meta-prompted version of a
    noisy prompt outperform even the CLEAN original? If so,
    the optimizer is not just recovering lost accuracy —
    it is EXCEEDING the user's original capability.

    We test this as a VARIANT of the Pre-Proc Sanitize intervention,
    using a meta-prompt instruction instead of a simple "fix errors"
    instruction. This is measured in the pilot phase and added to
    the full experiment if results are promising.

### 6.3 Language Variant: American vs. British English (NEW v4.0)

This research uses AMERICAN ENGLISH throughout — in prompts,
in noise generation, in evaluation criteria. This is a deliberate
choice: both benchmark datasets (HumanEval, GSM8K) and the
majority of LLM training data skew American English.

    DOES THE ENGLISH VARIANT MATTER?

    Potentially yes. Differences include:
    - Spelling: "optimize" vs "optimise", "color" vs "colour"
    - Vocabulary: "array" vs "list" (technical context varies)
    - Date formats: MM/DD/YYYY vs DD/MM/YYYY
    - Tokenization: "optimise" may tokenize differently than
      "optimize" and could produce different attention patterns

    We flag this as FUTURE WORK (Section 23) rather than a
    variable in the current study. Mixing English variants
    would introduce an uncontrolled variable.


---

## 7. Statistical Analysis Framework (NEW in v2.0)

This section replaces the brief "Statistical Requirements" paragraph
from v1.0 with a comprehensive framework informed by current best
practices in LLM evaluation methodology.

### 7.1 Why Simple t-Tests Are Insufficient

The v1.0 design proposed paired t-tests and Cohen's d. These are
necessary but not sufficient for three reasons:

    PROBLEM                         CONSEQUENCE
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    1. Prompts vary in difficulty.  A prompt that is hard when
       t-tests treat all prompts    clean is even harder with
       as exchangeable.             noise. Averaging masks this.

    2. LLM outputs are stochastic.  The same prompt can produce
       A single run per condition   different answers on
       conflates noise effects      different runs. We need
       with sampling variance.      multiple runs per cell.

    3. Multiple comparisons.        With 8+ cells x 2 models,
       Unadjusted p-values          we are running dozens of
       inflate false positives.     tests. Must correct.


### 7.2 Primary Analysis: Generalized Linear Mixed Models (GLMMs)

NIST AI 800-3 (February 2026) recommends GLMMs as the foundation
for principled LLM evaluation statistics. GLMMs properly account
for the fact that some prompts are inherently harder than others
and that models behave differently across prompt types.

    MODEL SPECIFICATION:

    Response:      Y_ijk ~ Bernoulli(p_ijk)   [pass/fail]

    Fixed effects: Noise_Type (A vs B)
                   Noise_Level (0%, 5%, 10%, 20%)
                   Intervention (Raw, Self-Corr, PreProc, PreProc+Comp)
                   Model (Claude, Gemini)
                   All 2-way interactions

    Random effects: (1 | Prompt_ID)          [prompt difficulty]
                    (1 | Prompt_ID:Model)    [prompt-model interaction]

    Link function:  logit

    WHY THIS MATTERS:

    +----------------------------------------------------------+
    |  SIMPLE APPROACH (t-test)                                |
    |  "Average accuracy dropped 8% under 10% noise"          |
    |  --> But was this driven by 5 very hard prompts          |
    |      failing, or a uniform 8% drop across all?           |
    |      We cannot tell.                                     |
    +----------------------------------------------------------+
    |  GLMM APPROACH                                           |
    |  "Noise reduced the log-odds of correct response by      |
    |   0.43 (SE=0.08, p<0.001) after accounting for prompt    |
    |   difficulty and model effects."                          |
    |  --> We CAN tell. The random effect for Prompt_ID         |
    |      absorbs the difficulty variation.                    |
    +----------------------------------------------------------+

    Implementation: Python `statsmodels` (MixedLM) or R `lme4` (glmer).
    We report both fixed-effect coefficients and variance components
    for the random effects.


### 7.3 Stability Analysis (NEW in v2.0)

Recent research — Riasat (March 2026), "When Stability Fails:
Hidden Failure Modes of LLMs" (ArXiv: 2603.15840) — demonstrates
that LLMs can exhibit near-perfect run-to-run stability while
systematically diverging from ground truth. We therefore measure stability and correctness
as INDEPENDENT dimensions.

    STABILITY METRICS:

    Consistency Rate (CR):
      For each prompt, run the model K=5 times.
      CR = (number of agreeing output pairs) / (total pairs)
      CR ranges from 0 (every run different) to 1 (all identical).

      For K=5 runs, there are C(5,2) = 10 pairwise comparisons.

    Stability-Correctness Decomposition:
      For each prompt under each condition, classify into one
      of four quadrants:

      +---------------------------+---------------------------+
      |  STABLE + CORRECT         |  STABLE + INCORRECT       |
      |  (CR >= 0.8, majority     |  (CR >= 0.8, majority     |
      |   answer is correct)      |   answer is WRONG)        |
      |                           |                           |
      |  --> Model is ROBUST      |  --> Model is CONFIDENTLY |
      |      to this noise level  |      WRONG. Most dangerous|
      |                           |      failure mode.        |
      +---------------------------+---------------------------+
      |  UNSTABLE + CORRECT       |  UNSTABLE + INCORRECT     |
      |  (CR < 0.8, majority      |  (CR < 0.8, majority      |
      |   answer is correct)      |   answer is WRONG)        |
      |                           |                           |
      |  --> Model is LUCKY.      |  --> Model is BROKEN.     |
      |      Correct by chance.   |      Obvious failure.     |
      +---------------------------+---------------------------+

    KEY HYPOTHESIS TO TEST:
    As noise increases, do prompts migrate from
    "Stable+Correct" to "Stable+Incorrect" (hidden failure)
    or to "Unstable+Incorrect" (visible failure)?

    If the migration is toward "Stable+Incorrect," this is a
    MAJOR FINDING: noise creates silent failures that users
    cannot detect from the model's behavior.


### 7.4 Rank-Order Stability: Kendall's Tau

We test whether the RELATIVE difficulty of prompts is preserved
under noise. If prompt #42 is hardest when clean, is it still
hardest at 10% noise?

    METHOD:
    1. Rank all 200 prompts by pass rate under CLEAN condition.
    2. Rank all 200 prompts by pass rate under each NOISY condition.
    3. Compute Kendall's tau (rank correlation) between rankings.

    tau close to 1.0 --> Noise affects all prompts equally
                         (a "uniform tax").
    tau significantly < 1.0 --> Noise disproportionately
                                breaks SOME prompts
                                (a "targeted tax").

    The "targeted tax" finding would be more interesting and
    actionable: it would mean certain prompt STRUCTURES are
    more vulnerable to noise, which the optimizer could learn
    to prioritize.


### 7.5 Pairwise Prompt-Level Tests: McNemar's Test

For each individual prompt, we have a 2x2 table:

    Prompt P under condition A vs condition B:

                          Condition B
                        Pass    Fail
    Condition A  Pass  [ a       b  ]
                 Fail  [ c       d  ]

    McNemar's test asks: is the off-diagonal (b vs c) significant?
    This tells us whether the intervention CHANGED the outcome
    for specific prompts, not just on average.

    We apply McNemar's to every prompt across:
    - Clean vs. each noise level (to find "fragile" prompts)
    - Noisy-raw vs. noisy-intervened (to find "recoverable" prompts)


### 7.6 Multiple Comparison Correction: Benjamini-Hochberg

With ~200 prompts x multiple conditions x 2 models, we run
hundreds of statistical tests. Without correction, a 5% false
positive rate produces dozens of spurious "significant" results.

    CORRECTION METHOD: Benjamini-Hochberg (BH) procedure
    - Controls the False Discovery Rate (FDR) at 5%
    - Less conservative than Bonferroni (which would be
      too aggressive for our test count)
    - Applied to ALL pairwise comparisons reported in the paper

    Implementation: scipy.stats.false_discovery_control()
    or statsmodels.stats.multitest.multipletests(method='fdr_bh')


### 7.7 Bootstrap Confidence Intervals

Rather than relying solely on parametric CIs, we use bootstrap
resampling to construct non-parametric confidence intervals for
all aggregate metrics (R, RR, TR).

    PROCEDURE:
    1. From our 200 prompts, resample WITH REPLACEMENT 200 prompts.
    2. Recompute the metric (e.g., R) on the resampled set.
    3. Repeat 10,000 times.
    4. Report the 2.5th and 97.5th percentiles as the 95% CI.

    WHY: Bootstrap CIs are robust to non-normal distributions,
    which is likely for our pass/fail binary outcomes. They also
    let us answer: "If we had tested a DIFFERENT set of 200
    prompts from the same benchmark, would our conclusions hold?"

    An ICLR 2026 paper on LLM evaluation robustness found that
    many evaluation rankings are fragile to small data drops.
    Bootstrap analysis directly addresses this concern.


### 7.8 Effect Size Reporting

For ALL comparisons, we report effect sizes alongside p-values:

    TEST TYPE              EFFECT SIZE MEASURE
    ~~~~~~~~~~~~~~~~~~~~~  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    GLMM fixed effects     Odds ratios (OR) with 95% CI
    Binary outcomes        Risk difference (RD) = P(pass|A) - P(pass|B)
    Continuous outcomes    Cohen's d (for BERTScore, token counts)
    Rank correlations      Kendall's tau (already an effect size)

    We follow the principle: "A significant p-value tells you
    something happened. The effect size tells you whether anyone
    should care."


### 7.9 Complete Statistical Analysis Pipeline

    +------------------+
    |  Raw Results     |
    |  (20,000 runs)   |
    +--------+---------+
             |
             v
    +------------------+     +---------------------------+
    | Per-Prompt       |     | Aggregate Metrics         |
    | Analysis         |     |                           |
    | ~~~~~~~~~~~~~~~~ |     | ~~~~~~~~~~~~~~~~~~~~~~~~~ |
    | - Consistency    |     | - R, RR, TR per cell      |
    |   Rate (5 runs)  |     | - GLMM coefficients       |
    | - Majority vote  |     | - Bootstrap 95% CIs       |
    |   correctness    |     | - BH-corrected p-values   |
    | - Quadrant       |     |                           |
    |   classification |     |                           |
    +--------+---------+     +-------------+-------------+
             |                             |
             v                             v
    +------------------+     +---------------------------+
    | Prompt-Level     |     | Model-Level               |
    | Tests            |     | Comparisons               |
    | ~~~~~~~~~~~~~~~~ |     | ~~~~~~~~~~~~~~~~~~~~~~~~~ |
    | - McNemar's per  |     | - Claude vs Gemini        |
    |   prompt (clean  |     |   per condition           |
    |   vs noisy)      |     | - Interaction effects     |
    | - Identify       |     |   (model x noise type)    |
    |   "fragile" set  |     |                           |
    +--------+---------+     +-------------+-------------+
             |                             |
             +-----------------------------+
                             |
                             v
                +---------------------------+
                | Rank-Order Analysis        |
                | ~~~~~~~~~~~~~~~~~~~~~~~~~ |
                | - Kendall's tau (clean     |
                |   vs noisy rankings)       |
                | - Identify "targeted"      |
                |   vs "uniform" tax         |
                +---------------------------+
                             |
                             v
                +---------------------------+
                | Final Reporting            |
                | ~~~~~~~~~~~~~~~~~~~~~~~~~ |
                | - All CIs are bootstrap   |
                | - All p-values are BH-    |
                |   corrected               |
                | - All effects have OR/d   |
                | - Stability reported      |
                |   alongside correctness   |
                +---------------------------+


---

## 8. Metrics & Measurement

### 8.1 Primary Metrics

    METRIC                  FORMULA / METHOD                  TARGET
    ~~~~~~~~~~~~~~~~~~~~~~  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  ~~~~~~
    Pass Rate (Code)        % of test cases passed            Auto-
                            (HumanEval/MBPP execution)        graded

    Accuracy (Math)         % of correct final answers        Auto-
                            (GSM8K numerical match)           graded

    Robustness Ratio (R)    R = Accuracy_Noisy /              0-1.0
                                Accuracy_Clean                (1.0 =
                                                              immune)

    Recovery Rate (RR)      RR = (Acc_Intervened -            0-1.0
                                  Acc_Noisy) /                (1.0 =
                                 (Acc_Clean -                 full
                                  Acc_Noisy)                  recovery)

    Token Reduction (TR)    TR = 1 - (Tokens_Compressed /     0-1.0
                                      Tokens_Original)

    Consistency Rate (CR)   CR = (agreeing pairs) /            0-1.0
      (NEW in v2.0)              C(K, 2)                      (1.0 =
                                 where K = 5 runs             perfectly
                                                              stable)


### 8.2 Secondary Metrics

    METRIC                  METHOD                            PURPOSE
    ~~~~~~~~~~~~~~~~~~~~~~  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  ~~~~~~~
    BERTScore               Semantic similarity between       Verify
                            outputs from clean vs. noisy      meaning
                            prompts                           preserved

    Reasoning Entropy       Measure divergence point in       Locate
                            chain-of-thought (CoT) traces     WHERE
                            between clean and noisy runs      noise
                                                              breaks
                                                              logic

    Confidence Delta        Compare logit probabilities       Measure
                            of top token under clean vs.      internal
                            noisy conditions                  "doubt"

    Net Token Cost          (Pre-proc overhead +              The ROI
                            compressed prompt tokens) -       metric
                            original prompt tokens

    Kendall's Tau           Rank correlation of prompt        Uniform
      (NEW in v2.0)         difficulty (clean vs noisy)       vs targeted

    Quadrant Distribution   % of prompts in each cell of     Failure
      (NEW in v2.0)         the Stability-Correctness         mode
                            matrix per condition              analysis


### 8.3 Measurement Architecture

    +------------------+
    |  Prompt Dataset  |
    |  (200 clean      |
    |   prompts)       |
    +--------+---------+
             |
             +----------+----------+-----------+
             |          |          |           |
             v          v          v           v
        +---------+ +--------+ +--------+ +--------+
        | Clean   | | Noise  | | Noise  | | Noise  |
        |         | | 5%     | | 10%    | | 20%    |
        +---------+ +--------+ +--------+ +--------+
             |          |          |           |
             |     +----+----+----+----+------+
             |     |         |         |
             |     v         v         v
             |  +------+  +------+  +------+  +----------+
             |  | Raw  |  | Self |  | Pre- |  | Pre-Proc |
             |  |      |  | Corr |  | Proc |  | Sanitize |
             |  |      |  |      |  | San. |  | +Compress|
             |  +--+---+  +--+---+  +--+---+  +----+-----+
             |     |         |         |            |
             +-----+---------+---------+------------+
                                  |
                                  v
                        +---------+---------+
                        |  EXECUTION ENGINE |
                        |                   |
                        |  For each prompt: |
                        |  1. Send to LLM   |
                        |  2. REPEAT x5     | <-- v2.0: 5 reps
                        |  3. Capture output |
                        |  4. Capture CoT   |
                        |  5. Log tokens    |
                        |  6. Grade result  |
                        |  7. Compute CR    | <-- v2.0: stability
                        +---------+---------+
                                  |
                                  v
                        +-------------------+
                        |  RESULTS DATABASE |
                        |                   |
                        |  - Pass/Fail x5   |
                        |  - Token counts   |
                        |  - CoT traces     |
                        |  - Logit scores   |
                        |  - Latency        |
                        |  - CR (stability) | <-- v2.0
                        |  - Quadrant class | <-- v2.0
                        +-------------------+


---

## 9. Data Collection Plan

### 9.1 Dataset Generation Pipeline

    PHASE    ACTION                                   OUTPUT
    ~~~~~~~  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  ~~~~~~~~~~~~~~~~~~~
    Phase 0  Select 200 prompts from HumanEval,      200 clean prompts
             MBPP, GSM8K (stratified by difficulty)   (JSON)

    Phase 1  Run Type A noise generator at 3 levels   600 noisy prompts
             (5%, 10%, 20%) with fixed random seeds    (JSON + metadata)

    Phase 2  Run Type B syntactic noise generator      200 ESL prompts
             (4 L1 patterns x 50 prompts each)         (JSON + metadata)

    Phase 3  Run compression module on all 200         200 compressed
             clean prompts                             prompts + token
                                                       counts

    Phase 4  Run Grammarly personas (Professional,     400 persona
             Casual) on 100 clean prompts              variants
             (OPTIONAL - scope-dependent)              (manual export)

    Phase 5  Collect 20 real-world "noisy" prompts     20 real prompts
    (NEW v4)  from public sources (StackOverflow,       (JSON + source
             Reddit r/learnprogramming, GitHub          attribution)
             issues from ESL contributors).
             Run as VALIDATION set alongside
             synthetic noise to address
             Adversarial Review concern #2.


### 9.2 Execution Log Schema (UPDATED in v3.0)

Every LLM call produces a structured log entry. Note the
additions for stability tracking (v2.0) and latency/cost
instrumentation (v3.0):

    {
      "run_id":           "uuid",
      "prompt_id":        "humaneval_042",
      "benchmark":        "HumanEval",
      "noise_type":       "type_a_10pct",
      "intervention":     "pre_proc_sanitize_compress",
      "model":            "claude-sonnet-4-20250514",
      "repetition":       3,              // v2.0: which of 5 runs
      "prompt_tokens":    142,
      "optimized_tokens": 47,
      "completion_tokens": 210,
      "pass_fail":        true,
      "raw_output":       "...",          // v2.0: for CR computation
      "cot_trace":        "...",
      "temperature":      0.0,           // v2.0: document sampling

      // --- v3.0: LATENCY INSTRUMENTATION ---
      "ttft_ms":          320,           // Time to First Token
      "ttlt_ms":          1840,          // Time to Last Token (end-to-end)
      "generation_ms":    1520,          // ttlt - ttft (pure generation)

      // --- v3.0: PRE-PROCESSOR COST TRACKING ---
      "preproc_model":    "claude-haiku-4-5",  // null if Raw/Self-Correct
      "preproc_input_tokens":   180,     // tokens sent TO pre-processor
      "preproc_output_tokens":  47,      // tokens returned (cleaned prompt)
      "preproc_ttft_ms":        95,      // pre-processor time to first token
      "preproc_ttlt_ms":        420,     // pre-processor total latency

      // --- v3.0: COST ACCOUNTING ---
      "main_model_input_cost_usd":   0.00042,  // actual $ for main call
      "main_model_output_cost_usd":  0.00063,
      "preproc_cost_usd":            0.00005,  // actual $ for pre-proc
      "total_cost_usd":              0.00110,  // sum of all costs
      "timestamp":        "2026-03-18T..."
    }

    DERIVED FIELDS (computed per prompt after all 5 runs):
    {
      "prompt_id":            "humaneval_042",
      "condition":            "type_a_10pct_raw",
      "consistency_rate":     0.80,       // CR across 5 runs
      "majority_pass":        true,       // majority vote of 5 runs
      "pass_count":           4,          // how many of 5 passed
      "quadrant":             "stable_correct",
      "mean_ttft_ms":         335,        // v3.0
      "mean_ttlt_ms":         1920,       // v3.0
      "mean_total_latency_ms": 2340,      // v3.0: includes pre-proc
      "mean_total_cost_usd":  0.00112,    // v3.0
      "token_savings":        95,         // v3.0: original - optimized
      "net_token_cost":       -48,        // v3.0: savings minus overhead
      "std_latency_ms":       145
    }


### 9.3 Statistical Requirements (UPDATED in v2.0)

    - Minimum 200 prompts per condition for statistical power
    - All noise injection uses FIXED SEEDS for reproducibility
    - Each condition run 5 TIMES (increased from 3) for stability
    - Temperature set to 0.0 for all runs (minimize sampling noise;
      remaining variation comes from model non-determinism)
    - Primary analysis: GLMM with prompt and model as random effects
    - Pairwise tests: McNemar's per prompt, BH-corrected
    - Confidence intervals: 10,000-iteration bootstrap on all metrics
    - Effect sizes: odds ratios (GLMM), Cohen's d, Kendall's tau
    - All p-values reported with BH correction for FDR < 0.05
    - Pre-registration: methodology deposited on OSF before Phase 2


---

## 10. Autonomous Execution Strategy: The "Karpathy Loop" (NEW in v2.0)

### 10.1 Inspiration: Autoresearch

Andrej Karpathy's `autoresearch` project (March 2026) demonstrates
a pattern where an AI agent autonomously runs experiments overnight,
guided by a markdown instruction file (`program.md`). The key insight:
the human's role shifts from "running experiments" to "designing the
search." The durable artifact is the instruction file, not the code
changes.

    KARPATHY'S PATTERN:                OUR ADAPTATION:
    ~~~~~~~~~~~~~~~~~~~~~~~~           ~~~~~~~~~~~~~~~~~~~~~~~~
    train.py (agent modifies)     -->  Noise params, compression
                                       strategies (agent varies)
    val_bpb (scalar metric)       -->  R, RR, TR, CR (metrics)
    5-minute time budget          -->  ~30s per API call
    program.md (human writes)     -->  research_program.md
    Git commit if improved        -->  Log result, advance matrix


### 10.2 Why Not Use Autoresearch Directly

    AUTORESEARCH IS FOR:               OUR RESEARCH NEEDS:
    ~~~~~~~~~~~~~~~~~~~~~~~~           ~~~~~~~~~~~~~~~~~~~~~~~~
    Modifying a training script        Varying INPUT prompts
    One GPU, local compute             External API calls
    One scalar metric (val_bpb)        Multiple metrics (R, TR, CR)
    Optimizing a single file           Sweeping a parameter matrix
    Keep-or-discard decisions          Log everything (no discard)

    The LOOP PATTERN transfers. The REPO does not.


### 10.3 The Three-Phase Hybrid Approach

We do NOT go fully autonomous from day one. The research proceeds
in three phases, with increasing agent autonomy:

    PHASE 1: HUMAN-DRIVEN (Weeks 1-2)
    ===================================
    The researcher (you) and Claude build all tooling manually.
    You must UNDERSTAND the pipeline before handing it to an agent.

    +----------+     +-----------+     +----------+     +--------+
    | Human    | --> | Build     | --> | Test on  | --> | Verify |
    | designs  |     | scripts   |     | 20       |     | grading|
    | pipeline |     | manually  |     | prompts  |     | works  |
    +----------+     +-----------+     +----------+     +--------+

    Deliverables:
    - noise_generator.py (tested, validated)
    - prompt_compressor.py (tested, validated)
    - run_experiment.py (execution harness)
    - grade_results.py (auto-grader)
    - research_program.md (the agent instructions)

    PHASE 2: SEMI-AUTONOMOUS (Weeks 3-4)
    ======================================
    The research_program.md tells Claude Code:
    "Here is the experiment matrix. For each cell, run the prompt
    through the pipeline, grade it, log the result. If a run
    crashes, log the error and skip. Do not stop until the matrix
    is complete."

    You kick this off, go to sleep, wake up to data.

    +----------+     +-----------------+     +-----------+
    | Human    | --> | Agent executes  | --> | Human     |
    | writes   |     | matrix          |     | reviews   |
    | program  |     | overnight       |     | results   |
    +----------+     | (~20,000 calls) |     | next day  |
                     +-----------------+     +-----------+

    This is the Karpathy loop for EVALUATION rather than training.
    The agent does not make creative decisions; it executes the
    plan mechanically. The human reviews and adjusts.

    PHASE 3: EXPLORATORY AUTONOMOUS (Weeks 5-6)
    =============================================
    Given baseline results, write a SECOND program.md:
    "Given these results, explore whether different compression
    strategies, noise distributions, or intervention prompts
    improve the recovery rate. Propose a modification, test it
    on 20 prompts, keep if RR improves."

    Now the agent is doing the CREATIVE part of the research.

    +----------+     +-----------------+     +-----------+
    | Human    | --> | Agent proposes  | --> | Human     |
    | defines  |     | + tests new     |     | curates   |
    | search   |     | interventions   |     | best      |
    | space    |     | autonomously    |     | findings  |
    +----------+     +-----------------+     +-----------+

    This phase is OPTIONAL for the first paper but could
    yield surprising findings (e.g., the agent discovers that
    a specific compression prompt wording recovers 95% of
    accuracy — something we would not have tried manually).


### 10.4 The research_program.md Structure

The instruction file follows Karpathy's design principles:
unambiguous, actionable, with clear success criteria.

    research_program.md (outline):
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    ## Objective
    Execute the experiment matrix defined in experiment_matrix.json.
    Minimize: reasoning errors. Maximize: data completeness.

    ## Setup
    1. Read experiment_matrix.json for the full list of conditions.
    2. Read prompts.json for the 200 clean prompts.
    3. Verify API keys are configured for Claude and Gemini.
    4. Initialize results.db (SQLite) with the schema from schema.sql.

    ## Experiment Loop
    For each row in experiment_matrix.json:
      1. Load the clean prompt.
      2. Apply the specified noise (call noise_generator.py).
      3. Apply the specified intervention (call intervene.py).
      4. Send the processed prompt to the specified model.
      5. Repeat 5 times (repetitions for stability).
      6. Grade each output (call grade_results.py).
      7. Log all fields to results.db.
      8. Print progress: "[342/20000] humaneval_042 | type_a_10pct |
         raw | claude | 4/5 pass | CR=0.80"

    ## Error Handling
    - If an API call fails, retry 3 times with exponential backoff.
    - If it still fails, log the error and skip to the next row.
    - Never stop the loop for a single failure.
    - If >10% of rows fail, pause and alert the human.

    ## Completion
    When all rows are processed, run compute_derived.py to populate
    the derived fields (CR, quadrant, majority vote).
    Print a summary table of R, RR, TR, CR per condition.
    Commit results.db to git.

    ## Constraints
    - Do NOT modify any Python scripts.
    - Do NOT skip rows or change the order.
    - Do NOT interpret results or draw conclusions.
    - Your job is DATA COLLECTION, not analysis.


### 10.5 Skill-Creator Evaluation Pattern (NEW v4.0)

Claude's built-in `skill-creator` skill uses an evaluation loop
that maps well onto our research methodology:

    SKILL-CREATOR PATTERN:        OUR ADAPTATION:
    ~~~~~~~~~~~~~~~~~~~~~~~~      ~~~~~~~~~~~~~~~~~~~~~~~~
    evals.json (test cases        experiment_matrix.json
    with assertions)              (prompt x noise x intervention)

    Subagent runs each test       Agent runs each matrix cell
    case independently            independently

    Grading: assertions +         Grading: pass/fail +
    human review via              automated + BERTScore
    eval-viewer HTML

    Iteration: rewrite skill      Iteration: explore new
    based on failures             intervention strategies

    60/40 train/test split        Bootstrap resampling for
    to avoid overfitting          robustness of findings

    The key insight from skill-creator is the ASSERTION-BASED
    EVALUATION pattern: define expected outcomes in JSON, run
    prompts through the system, grade automatically, and present
    failures for human review. We can adapt this directly:

    Our "evals.json" equivalent:
    {
      "prompt_id": "humaneval_042",
      "clean_prompt": "Write a function...",
      "expected": "passes all test cases",
      "noise_variants": ["type_a_5pct", "type_a_10pct", ...],
      "assertions": [
        {"type": "pass_rate", "threshold": 0.8},
        {"type": "bertscore", "threshold": 0.95},
        {"type": "token_reduction", "min": 0.20}
      ]
    }

    This gives us structured, machine-readable success criteria
    for every experimental cell — enabling the autonomous
    execution loop to flag anomalies without human intervention.


### 10.6 Cost Estimate for Autonomous Execution

    ~20,000 LLM calls
    Average prompt: ~200 tokens input, ~300 tokens output
    Input:  20,000 x 200 = 4M tokens
    Output: 20,000 x 300 = 6M tokens

    Pre-processor calls (for Sanitize/Compress conditions):
    ~10,000 calls to fast model (Haiku/Flash)
    ~10,000 x 300 = 3M tokens

    TOTAL: ~13M tokens
    Estimated cost: $15-40 depending on model pricing
    Estimated time: 8-12 hours (with rate limiting)

    This fits comfortably in an "overnight run" budget.


---

## 11. The Compression Study: Design Details

This is the NOVEL CONTRIBUTION that distinguishes our paper from
prior robustness work.

### 11.1 Compression Strategies

    STRATEGY              METHOD                          EXPECTED
                                                          REDUCTION
    ~~~~~~~~~~~~~~~~~~~~  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  ~~~~~~~~~~
    Exact Dedup           Remove verbatim repeated         5-15%
                          sentences/phrases

    Semantic Dedup        Identify paraphrase pairs        10-25%
                          (embedding cosine > 0.90)
                          and merge into one statement

    Condensation          Rewrite remaining content         15-30%
                          to minimize token count
                          while preserving all intent

    Combined Pipeline     All three in sequence             25-50%


### 11.2 Compression Validation Protocol

To ensure compression does not lose meaning:

    ORIGINAL PROMPT -----> LLM -----> OUTPUT_A (x5 runs)
                                         |
    COMPRESSED PROMPT ---> LLM -----> OUTPUT_B (x5 runs)
                                         |
                                         v
                               +-----------------+
                               | COMPARE:        |
                               | 1. Pass/Fail    |
                               |    (must match) |
                               | 2. BERTScore    |
                               |    (> 0.95)     |
                               | 3. CR preserved |  <-- v2.0
                               |    (stability   |
                               |     not worse)  |
                               | 4. Human eval   |
                               |    (sample of   |
                               |     50 pairs)   |
                               +-----------------+


### 11.3 Cost-Benefit Model

    THE FINANCIAL ARGUMENT FOR PROMPT OPTIMIZATION

    Scenario: Enterprise with 1M prompts/month
    Average prompt: 500 tokens
    Average redundancy: 30%

    WITHOUT optimizer:
      1M x 500 tokens = 500M input tokens/month

    WITH optimizer (pre-proc overhead: 100 tokens/call):
      Pre-proc cost:    1M x 100 = 100M tokens
      Compressed prompt: 1M x 350 = 350M tokens
      Total:            450M tokens/month
      SAVINGS:          50M tokens/month (10%)

    BUT if compression also IMPROVES accuracy (fewer retries):
      Estimated retry reduction: 15-20%
      Adjusted savings: 15-25% total cost reduction

    This is the business case for "Prompt Optimization as
    a Service" -- and the hook for industry attention.


---

## 12. Optimizer Overhead Analysis (NEW in v3.0)

### 12.1 The Core Question: When Does Fixing Cost More Than It Saves?

The "fix my prompt" step is NOT free. It consumes tokens, adds latency,
and incurs API costs. If the user's prompt is already clean and concise,
the optimizer is pure overhead. The paper MUST quantify the break-even
point.

    THE OVERHEAD PARADOX:

    +-----------------------------------------------------------+
    |  SCENARIO A: User prompt has many errors and bloat        |
    |                                                           |
    |  Original: 500 tokens, noisy, redundant                   |
    |  Pre-proc: 100 tokens overhead to analyze + clean         |
    |  Output:   280 tokens (clean, compressed)                 |
    |                                                           |
    |  Net savings: 500 - 280 - 100 = 120 tokens SAVED          |
    |  Accuracy:  +15% improvement                              |
    |  Verdict:   WORTH IT                                      |
    +-----------------------------------------------------------+
    |  SCENARIO B: User prompt is already clean and concise     |
    |                                                           |
    |  Original: 200 tokens, clean, minimal                     |
    |  Pre-proc: 100 tokens overhead to analyze (finds nothing) |
    |  Output:   195 tokens (barely changed)                    |
    |                                                           |
    |  Net savings: 200 - 195 - 100 = -95 tokens WASTED         |
    |  Accuracy:  +0% (was already fine)                        |
    |  Verdict:   NOT WORTH IT                                  |
    +-----------------------------------------------------------+

    THIS MEANS: The optimizer needs a GATING FUNCTION that decides
    WHETHER to activate, not just HOW to optimize. This is a key
    finding for the paper.


### 12.2 Latency Instrumentation

We capture four distinct latency measurements per call:

    TIMELINE OF A SINGLE OPTIMIZED REQUEST:

    User hits Enter
    |
    |--[preproc_ttft]-->  Pre-processor starts generating
    |--[preproc_ttlt]-->  Pre-processor returns cleaned prompt
    |                     |
    |                     |--[main_ttft]-->  Main model starts
    |                     |--[main_ttlt]-->  Main model finishes
    |
    |--[total_latency]--> User sees complete response

    total_latency = preproc_ttlt + main_ttlt

    FOR RAW (no optimizer):
    total_latency = main_ttlt only

    THE LATENCY TAX:
    preproc_ttlt adds 200-800ms depending on prompt length.
    This is the "price of cleanliness."

    KEY METRICS TO REPORT:
    - Mean preproc_ttlt per intervention type
    - Latency overhead as % of total request time
    - Correlation between prompt length and preproc latency
    - Break-even point: at what noise level does the accuracy
      gain justify the latency cost?


### 12.3 Full Cost-Benefit Accounting

For every experimental condition, we compute:

    COST COMPONENT              HOW MEASURED
    ~~~~~~~~~~~~~~~~~~~~~~~~~~  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    C_preproc_in                preproc_input_tokens x model rate
    C_preproc_out               preproc_output_tokens x model rate
    C_main_in                   optimized_tokens x model rate
    C_main_out                  completion_tokens x model rate
    C_total                     Sum of all above

    COMPARISON:
    C_raw = (original_tokens x model rate) + (completion_tokens x rate)
    C_optimized = C_preproc_in + C_preproc_out + C_main_in + C_main_out

    DELTA = C_optimized - C_raw

    If DELTA < 0: optimizer saves money (prompt compression > overhead)
    If DELTA > 0: optimizer costs money (overhead > compression)
    If DELTA ~ 0: break-even (benefit is accuracy, not cost)


### 12.4 The Break-Even Analysis

We plot a "break-even surface" across two dimensions:

    Cost Delta ($)
         ^
     +$  |          * * * *     (Short, clean prompts:
         |        *              optimizer costs more)
     $0  |------*-----------    BREAK-EVEN LINE
         |    *
     -$  |  *                   (Long, noisy prompts:
         | *                     optimizer saves money)
         +-----|------|-------> Prompt Length (tokens)
              100    300   500

    We expect the break-even to shift based on:
    - Noise level (more noise = more to fix = more savings)
    - Prompt length (longer = more compression opportunity)
    - Pre-proc model choice (cheaper model = lower overhead)

    THIS SURFACE IS A KEY DELIVERABLE for the paper. It tells
    practitioners: "If your average prompt is >X tokens and your
    user base has >Y% noise rate, deploy the optimizer."


### 12.5 Pre-Processor Model Selection Study

We test three pre-processor models at different cost/quality points:

    PRE-PROC MODEL      COST         SPEED    EXPECTED QUALITY
    ~~~~~~~~~~~~~~~~~~  ~~~~~~~~~~~  ~~~~~~~  ~~~~~~~~~~~~~~~~~~
    Claude Haiku        Very cheap   Fast     Good for typos,
                                              may miss subtle
                                              syntactic issues

    Gemini Flash        Very cheap   Fast     Good general-
                                              purpose cleaning

    Claude Sonnet       Moderate     Slower   Best quality,
    (same as main)                            but doubles cost

    For each, measure: correction quality (did it fix the errors?),
    compression quality (did it reduce tokens effectively?), and
    cost/latency overhead.


---

## 13. Grammarly Personas & the "AI Prompt Persona" (NEW in v3.0)

### 13.1 The Grammarly Question

Grammarly is a browser extension that rewrites user text according
to "personas" (Professional, Casual, Academic, etc.). This raises
two research questions:

    Q1: Do different Grammarly personas produce different LLM
        outputs when applied to the same underlying intent?

    Q2: Could a purpose-built "AI Prompt Persona" — optimized
        specifically for LLM input rather than human readers —
        outperform Grammarly's general-purpose rewriting?


### 13.2 Scope Decision: Browser-Only Limitation

    Grammarly is a BROWSER EXTENSION. It is NOT available in:
    - CLI environments (Claude Code, terminal)
    - API calls (programmatic access)
    - Mobile apps (limited)

    This means:
    - Grammarly is relevant ONLY for browser-based AI chat
      (claude.ai, gemini.google.com, chatgpt.com)
    - For CLI/API users, the "Pre-Proc Sanitize" intervention
      from our main experiment is the equivalent solution
    - The Grammarly study is therefore a BROWSER-SPECIFIC
      sub-experiment, not a core finding

    RECOMMENDATION: Include as OPTIONAL Section in the paper
    (Section VII.B in the whitepaper). If results are strong,
    it becomes its own follow-up paper.


### 13.3 The "AI Prompt Persona" Concept

This is the COMMERCIAL OPPORTUNITY you identified. The idea:

    CURRENT STATE:
    +----------+     +------------------+     +----------+
    | User     | --> | Grammarly        | --> | AI Chat  |
    | types    |     | rewrites for     |     | (Claude, |
    | prompt   |     | HUMAN readers    |     |  Gemini) |
    +----------+     | (formal, casual) |     +----------+
                     +------------------+

    PROPOSED STATE:
    +----------+     +------------------+     +----------+
    | User     | --> | AI Prompt Persona| --> | AI Chat  |
    | types    |     | rewrites for     |     | (Claude, |
    | prompt   |     | LLM CONSUMPTION  |     |  Gemini) |
    +----------+     | (optimized for   |     +----------+
                     |  tokens, clarity, |
                     |  reasoning)      |
                     +------------------+

    KEY DIFFERENCES from Grammarly:
    - Optimizes for TOKEN EFFICIENCY, not readability
    - Removes hedging, politeness padding, redundancy
    - Preserves technical precision over stylistic elegance
    - Activates ONLY on AI chat sites (claude.ai, etc.)
    - Could measure and display: "Saved 45 tokens ($0.002)"

    IMPLEMENTATION OPTIONS:
    1. Browser extension (like Grammarly, but for AI prompts)
    2. MCP server (middleware proxy)
    3. Tampermonkey/userscript (lightweight)
    4. Native integration (vendor builds it in)


### 13.4 Commercial Viability

    WHY GRAMMARLY (OR A COMPETITOR) MIGHT PAY FOR THIS:
    - Grammarly already has 30M+ users
    - AI chat usage is exploding
    - "Save money on AI" is a compelling value proposition
    - Data on HOW users write prompts is extremely valuable
    - This could be a new Grammarly product tier:
      "Grammarly for AI" or "Grammarly Prompt Optimizer"

    WHAT THE PAPER NEEDS TO PROVE:
    1. Different writing styles produce measurably different
       LLM outputs (the "persona effect")
    2. A purpose-built "LLM-optimized" style outperforms
       all existing Grammarly personas on accuracy + cost
    3. The token savings are large enough to justify a
       subscription ($12/month Grammarly vs. $X/month savings)

    IF WE CAN SHOW #2 AND #3, this is a fundable product.


### 13.5 Experimental Protocol for Grammarly Study (OPTIONAL)

    1. Select 100 clean prompts from our benchmark
    2. Manually run each through Grammarly with:
       - Professional persona
       - Casual persona
       - Academic persona
       - No Grammarly (control)
    3. Run each variant through Claude + Gemini (5 reps each)
    4. Compare: accuracy, token count, latency, stability
    5. Then run the same prompts through our "AI Prompt Persona"
       (the Pre-Proc Sanitize+Compress intervention)
    6. Compare: does our optimizer beat all Grammarly personas?

    NOTE: This is labor-intensive (manual Grammarly step).
    Budget 2-3 days for 100 prompts x 4 personas = 400 manual
    rewrites. Consider automating via Grammarly's API if available.


---

## 14. Implementation Roadmap (UPDATED in v3.0)

### Phase 1: Tooling & Baseline — Human-Driven (Weeks 1-2)

    TASK                                    DELIVERABLE
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  ~~~~~~~~~~~~~~~~~~~~~~~~
    Build noise injection module (Python)   noise_generator.py
    Build compression module (Python)       prompt_compressor.py
    Build execution harness                 run_experiment.py
    Build auto-grader                       grade_results.py
    Write research_program.md               research_program.md
    Select and prepare prompt dataset       prompts.json (200 items)
    Build experiment matrix                 experiment_matrix.json
    PILOT: Run 20 prompts manually across   pilot_results.json
    all conditions to validate pipeline
    Validate grading, logging, stability    test_grader.py
    computation

### Phase 2: Noise Experiment — Semi-Autonomous (Weeks 3-4)

    TASK                                    DELIVERABLE
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  ~~~~~~~~~~~~~~~~~~~~~~~~
    Generate all noisy variants             noisy_prompts.json
    Agent executes full Experiment 1        results.db
    matrix overnight (~16,000 calls)        (via research_program.md)
    Human reviews completeness, errors      error_report.md
    Compute R, RR, CR, quadrant             exp1_analysis.csv
    distributions for all conditions
    Run GLMM analysis                       glmm_results.json
    Produce "Robustness Curve" plot         figures/robustness_curve
    Produce stability-correctness plots     figures/quadrant_migration

### Phase 3: Compression Experiment — Semi-Autonomous (Weeks 5-6)

    TASK                                    DELIVERABLE
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  ~~~~~~~~~~~~~~~~~~~~~~~~
    Agent executes Experiment 2 overnight   results.db (appended)
    (clean vs compressed, ~2,000 calls)
    OPTIONAL: Agent explores alternative    exploration_log.json
    compression strategies (Phase 3 auto)
    Compute TR, accuracy delta, BERTScore   exp2_analysis.csv
    Build cost-benefit model with real      figures/cost_model
    token counts
    Run bootstrap CIs on all metrics        bootstrap_results.json

### Phase 4: Analysis & Writing (Weeks 7-8)

    TASK                                    DELIVERABLE
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  ~~~~~~~~~~~~~~~~~~~~~~~~
    Full statistical analysis (GLMM,        stats_report.md
    McNemar's, bootstrap, Kendall's tau,
    BH correction)
    Draft whitepaper                        paper_v1.tex
    Produce all figures and tables          figures/
    Internal review and revision            paper_v2.tex
    ArXiv submission                        arxiv_submission


---

## 15. Whitepaper Outline (ArXiv Target) (UPDATED in v3.0)

**Working Title:** *The Linguistic Tax: Quantifying Prompt Noise and
Bloat in LLM Reasoning, and the Case for Automated Prompt Optimization*

    SECTION                   CONTENT                        EST. PAGES
    ~~~~~~~~~~~~~~~~~~~~~~~~  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  ~~~~~~~~~~
    I. Abstract               Problem, method, key finding   0.5
                              (compression saves cost AND
                              improves accuracy)

    II. Introduction          "Natural language" interfaces   1.5
                              that punish imperfect input.
                              The ESL equity angle.
                              The hidden cost of bloat.

    III. Related Work         LLM robustness: PromptRobust,  2.0
                              R2ATA, MulTypo. Prompt
                              compression: LLMLingua,
                              CompactPrompt, ProCut.
                              Evaluation: NIST AI 800-3,
                              stability vs. correctness.
                              Gap: no combined study of
                              noise + compression + cost.

    IV. Methodology           Noise injection (Type A/B).    3.0
                              Compression pipeline.
                              Intervention definitions.
                              Experimental design.

    V. Statistical            GLMM specification.            1.5
    Framework                 Stability-correctness
                              decomposition. Bootstrap
                              CIs. McNemar's. BH
                              correction. Power analysis.

    VI. Experimental Setup    Models, benchmarks, hardware,  1.0
                              hyperparameters, reproduction
                              instructions. Autonomous
                              execution (research_program.md).

    VII. Results              THE CORE FINDINGS:             4.0
                                                             (EXPANDED)
                              Finding 1: The Robustness
                              Curve (noise vs. accuracy).

                              Finding 2: The ESL Penalty
                              (Type B > Type A degradation).

                              Finding 3: The Stability
                              Illusion (noise causes silent
                              failures, not just errors).

                              Finding 4: The Compression
                              Dividend (tokens saved vs.
                              accuracy preserved).

                              Finding 5: The Combined Win
                              (sanitize + compress yields
                              better AND cheaper results).

                              Finding 6: The Break-Even     (NEW v3.0)
                              Curve (when optimizer overhead
                              exceeds savings; the decision
                              rule for deployment).

                              Finding 7 (OPTIONAL):          (NEW v3.0)
                              The Persona Effect (Grammarly
                              styles vs. AI Prompt Persona).

    VIII. Cost-Benefit        Full cost accounting with       1.0
    Analysis (NEW v3.0)       real token prices. Break-even  (NEW)
                              surface plot. Enterprise
                              projection model. Pre-proc
                              model selection comparison
                              (Haiku vs Flash vs Sonnet).

    IX. Discussion            Implications for LLM UI         1.5
                              design. The case for native
                              prompt optimization. Coding
                              assistant integration
                              (CLAUDE.md, AGENTS.md,
                              .cursorrules). Browser
                              middleware / MCP gateway.
                              "AI Prompt Persona" concept.
                              The autoresearch pattern for
                              evaluation (not just training).

    X. Limitations            Model selection bias. English   0.5
                              focus. Synthetic vs. real
                              noise. Compression may lose
                              nuance in edge cases. Agent
                              execution reproducibility.
                              Self-Correct confound.

    XI. Conclusion &          "Global Robustness Score"      0.5
    Future Work               proposal. Browser extension.
                              Multi-language expansion.
                              Real user study. Autonomous
                              intervention discovery.
                              "AI Prompt Persona" product.

    Appendix A                Noise generation algorithms    --
    Appendix B                Full results tables            --
    Appendix C                Prompt compression examples    --
    Appendix D                research_program.md (full)     --
    Appendix E                GLMM specification & code      --
    Appendix F (NEW)          Break-even analysis details    --
    Appendix G (NEW)          Full literature review table   --

    TOTAL ESTIMATED LENGTH: ~17 pages (increased from ~15)


---

## 16. Risk Register (UPDATED in v3.0)

    RISK                           LIKELIHOOD  IMPACT   MITIGATION
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  ~~~~~~~~~~  ~~~~~~~  ~~~~~~~~~~~~~~~~
    Noise injection is too         Medium      High     Validate against
    artificial; doesn't reflect                         real L2 error
    real user errors                                    corpora; include
                                                        human samples

    Compression loses critical     Medium      High     Strict semantic
    intent in edge cases                                similarity
                                                        threshold (0.95)
                                                        + human spot-check

    Models update mid-study,       Low         Medium   Pin model versions;
    changing baseline                                   document exact
                                                        model strings

    API costs exceed budget        Medium      Medium   Start with pilot
                                                        (20 prompts);
                                                        use cached results
                                                        where possible

    Grammarly persona variable     High        Low      Mark as OPTIONAL;
    is hard to isolate cleanly                          defer to follow-up
                                                        paper if messy

    Peer reviewers challenge       Medium      High     Pre-register
    ESL noise validity                                  methodology;
                                                        cite SLA literature;
                                                        consider linguist
                                                        co-author

    Agent hallucinates results     Low         CRITICAL Log raw API
    or skips conditions during                          responses; verify
    overnight autonomous run                            row counts match
    (v2.0)                                              expected matrix
                                                        size; checksums

    GLMM fails to converge on     Medium      Medium   Fall back to
    our data structure                                  logistic regression
    (v2.0)                                              with clustered
                                                        standard errors

    Rate limiting causes           Medium      Low      Build exponential
    incomplete overnight runs                           backoff + resume
    (v2.0)                                              logic into harness;
                                                        save checkpoint
                                                        after each row

    Bootstrap CIs too wide to      Low         Medium   Increase prompt
    support claims (N=200 may                           count to 300 if
    be insufficient)                                    pilot shows wide
    (v2.0)                                              intervals

    Optimizer overhead exceeds     Medium      High     Build break-even
    savings for short/clean                             analysis; add
    prompts, undermining the                            gating function
    cost-benefit argument                               that skips pre-proc
    (NEW in v3.0)                                       for short prompts

    Self-Correct intervention      Medium      High     Add 5th control
    confounds context-window                            condition: external
    load with correction quality                        sanitize but NO
    (NEW in v3.0)                                       compress, to
                                                        isolate effects

    Reviewer argues CompactPrompt  Medium      High     Emphasize: we test
    already solved compression;                         compression on
    our contribution is not novel                       NOISY prompts (they
    (NEW in v3.0)                                       tested clean only);
                                                        we add cost model

    Grammarly API unavailable or   High        Low      Manual process for
    changes; persona study cannot                       100 prompts (budget
    be automated                                        2-3 days); mark as
    (NEW in v3.0)                                       optional


---

## 17. Success Criteria (UPDATED in v2.0)

This study is successful if we can demonstrate ALL FOUR of the
following with statistical significance (BH-corrected FDR < 0.05):

    +-----------------------------------------------------------+
    |  CRITERION 1: NOISE DEGRADES REASONING                    |
    |  R < 0.90 for at least one noise level on hard tasks      |
    |  (GLMM odds ratio significantly < 1.0)                    |
    +-----------------------------------------------------------+
    |  CRITERION 2: COMPRESSION SAVES TOKENS                    |
    |  Token reduction > 20% with accuracy delta < 2%           |
    |  (bootstrap 95% CI for delta includes zero)               |
    +-----------------------------------------------------------+
    |  CRITERION 3: OPTIMIZER PROVIDES NET BENEFIT               |
    |  Sanitize+Compress yields BOTH higher accuracy AND lower  |
    |  token cost compared to raw noisy prompts                 |
    +-----------------------------------------------------------+
    |  CRITERION 4: STABILITY ILLUSION EXISTS                   |
    |  At least 10% of prompts migrate to "Stable+Incorrect"   |
    |  quadrant under noise (hidden failures detectable only    |
    |  by ground-truth comparison, not by output consistency)   |
    +-----------------------------------------------------------+
    |  CRITERION 5: BREAK-EVEN IS QUANTIFIABLE (NEW v3.0)       |
    |  We can define a clear threshold (prompt length x noise   |
    |  level) above which the optimizer's cost is justified,    |
    |  and below which it is not. This gives practitioners an   |
    |  actionable deployment decision rule.                     |
    +-----------------------------------------------------------+

    If Criteria 3, 4, AND 5 hold, the paper's headline is:

    "A lightweight prompt optimizer makes LLMs simultaneously
     MORE ACCURATE and CHEAPER for noisy prompts — catches
     silent failures users cannot detect — and we provide a
     decision rule for when to deploy it."

---

## 18. Tools & Infrastructure (UPDATED in v2.0)

    COMPONENT            TECHNOLOGY              NOTES
    ~~~~~~~~~~~~~~~~~~~  ~~~~~~~~~~~~~~~~~~~~~~  ~~~~~~~~~~~~~~~~~~~~
    Noise Generator      Python (custom)         Seeded randomness
    Compression Module   Python + LLM API        Uses fast model
                                                 (Haiku/Flash)
    Execution Harness    Python + API clients    Claude API, Gemini
                                                 API
    Grading              Python (HumanEval       Existing frameworks
                         sandbox, regex match)
    Statistical Analysis Python (statsmodels,    GLMMs, bootstrap,
      (UPDATED)          scipy, scikit-learn)    McNemar's, BH
                         OR R (lme4, boot)
    BERTScore            Python (bert-score      Pre-trained
                         library)
    Agent Orchestration  Claude Code with        Karpathy-style
      (NEW)              research_program.md     overnight execution
    Results Storage      SQLite                  Structured logs
                                                 (upgraded from JSON)
    Version Control      Git                     All code, data,
                                                 configs, program.md
    Pre-registration     OSF                     Deposit methodology
      (NEW)                                      before Phase 2


---

## 19. Ethical Considerations

- **ESL Representation:** We do not claim our synthetic L1 patterns
  represent the full diversity of non-native English. We acknowledge
  this as a simplification and call for real-user studies in future work.

- **No User Data:** All prompts are drawn from public benchmarks.
  No real user prompts are collected or analyzed.

- **Equity Framing:** The "Linguistic Tax" framing is intended to
  highlight inequity in AI access, not to pathologize non-native
  English. The goal is to build systems that accommodate all users.

- **Open Source:** All code, data, results, AND the research_program.md
  will be released publicly to enable reproduction and extension.

- **Agent Transparency:** When describing autonomous execution, we
  clearly document what the agent did vs. what the human designed.
  We do not attribute "insight" to the agent; it executed a plan.


---

## 20. Literature Review: Key Papers & Sources (NEW in v3.0)

This section catalogs the primary references for the whitepaper,
organized by topic. All entries are real, published works.

### 20.1 Prompt Robustness & Adversarial Attacks

    PAPER / SOURCE                          KEY FINDING FOR US
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Gan et al. (2024)                       ATA algorithm: 1 character edit
    "Reasoning Robustness of LLMs to        drops Mistral-7B accuracy from
    Adversarial Typographical Errors"        43.7% to 38.6% on GSM8K. With
    ArXiv: 2411.05345                       8 edits, drops to 19.2%.
                                            DIRECTLY supports H1.

    Zhu et al. (2024)                       PromptRobust benchmark: 4,788
    "PromptRobust: Towards Evaluating       adversarial prompts across
    the Robustness of LLMs on               character, word, sentence, and
    Adversarial Prompts"                    semantic levels. Word-level
    ArXiv: 2306.04528                       attacks cause 39% avg drop.
                                            KEY BENCHMARK to reference.

    Ngweta et al. (2025)                    Mixture of Formats (MOF):
    "Towards LLMs Robustness to Changes     diversifying prompt style
    in Prompt Format Styles"                reduces brittleness. Relevant
    ArXiv: 2504.06969                       to Grammarly persona study.

    (2025) "Small Edits, Big Consequences:  Frontier models pass 85% of
    Telling Good from Bad Robustness"       tests even after losing 90%
    ArXiv: 2507.15868                       of prompt, but FAIL to adapt
                                            when a single word changes
                                            semantics. "Over-robustness."

    Enterprise Robustness Benchmark (2026)  420 base issues, multilingual
    "Evaluating Robustness of LLMs in       perturbations. Up to 21.2%
    Enterprise Applications"                performance degradation from
    ArXiv: 2601.06341                       stylistic changes in code gen.

### 20.2 Multilingual & Non-Native Speaker Impact

    MulTypo (2025)                          Multilingual typo generation
    "Evaluating Robustness of LLMs          algorithm based on keyboard
    Against Multilingual Typographical      layouts. Instruction-tuned
    Errors"                                 models are as brittle as base
    ArXiv: 2510.09536                       models. DIRECTLY supports H4.
                                            KEY finding: "instruction-
                                            tuning improves performance
                                            but NOT robustness."

    CREME (2025)                            Layer-aware model editing to
    "Robustness Enhancement of Code LLMs    improve robustness. Shows that
    via Layer-Aware Model Editing"          misspelling "modulo" as
    ArXiv: 2507.16407                       "mmodulo" causes completely
                                            different code output.

### 20.3 Prompt Compression & Token Optimization

    LLMLingua (2023)                        Foundational prompt compression
    "Compressing Prompts for Accelerated    work. Up to 20x compression
    Inference of LLMs"                      with little performance loss.
    ArXiv: 2310.05736                       Uses perplexity-based token
                                            pruning. KEY BASELINE for
                                            our compression study.

    CompactPrompt (2025)                    End-to-end pipeline: hard
    "A Unified Pipeline for Prompt and      compression + data compression.
    Data Compression in LLM Workflows"      60% token reduction, <5%
    ArXiv: 2510.18043                       accuracy drop on Claude 3.5.
                                            DIRECTLY relevant to our
                                            compression methodology.

    ProCut (2025)                           Treats prompt compression as
    "LLM Prompt Compression via             feature selection. Uses
    Attribution Estimation"                 Shapley values to identify
    ArXiv: 2508.02053                       most impactful segments.
                                            Novel approach we should
                                            reference.

    LLM-DCP (2025)                          Models compression as MDP.
    "Dynamic Compressing Prompts for        17% improvement over Selective
    Efficient Inference of LLMs"            Context. Task-agnostic.
    ArXiv: 2504.11004

    Li et al. (2024)                        Comprehensive survey of hard
    "Prompt Compression for LLMs:           and soft compression methods.
    A Survey"                               Categories: token pruning,
    ArXiv: 2410.12388                       summarization, soft prompts.

    Lossless Meta-Tokens (2025)             Lossless compression via
    "Lossless Token Sequence Compression    LZ77-like technique. 27%
    via Meta-Tokens"                        reduction, no semantic loss.
    ArXiv: 2506.00307                       Shows lossy methods fail on
                                            tasks requiring precision.

### 20.4 LLM Evaluation Methodology

    NIST AI 800-3 (Feb 2026)               Recommends GLMMs for LLM
    "Expanding the AI Evaluation Toolbox    evaluation. Distinguishes
    with Statistical Models"                benchmark accuracy vs.
    nist.gov                                generalized accuracy.

    Riasat (Mar 2026)                       Stability != correctness.
    "When Stability Fails: Hidden           LLMs can be stable AND
    Failure Modes of LLMs"                  systematically wrong.
    ArXiv: 2603.15840                       DIRECTLY supports H5.

    ICLR 2026                               LLM evaluation rankings are
    "Robustness of Rankings from LLM        fragile to small data drops.
    Evaluation Systems"                     Motivates our bootstrap CIs.
    openreview.net

    NAACL 2025 Industry Track               SCORE framework: consistency
    "Systematic Consistency and Robustness  rate metric across prompt
    Evaluation"                             variations. We adopt their
    aclanthology.org                        CR metric.

    Robustness Survey (2025)                Comprehensive survey. Key:
    "Robustness in LLMs: A Survey of        instruction-tuned models may
    Mitigation Strategies and Evaluation    be MORE brittle than base.
    Metrics"                                Table 1 catalogs non-
    ArXiv: 2505.18658                       robustness sources.

### 20.5 Autonomous Research & Experimentation

    Karpathy (Mar 2026)                     Autonomous experiment loop.
    "autoresearch"                          program.md as "research org
    github.com/karpathy/autoresearch        code." 12 experiments/hour.
                                            Pattern for our Phase 2-3.


---

## 21. Adversarial Review: Red-Team Critique (NEW in v3.0)

The following is a deliberately critical assessment of this RDD,
written from the perspective of a skeptical ArXiv reviewer, a
competing research group, and a practitioner who would use the
results. The goal is to surface weaknesses BEFORE submission.

### 21.1 Reviewer #1: "The Novelty Is Thin"

    CRITIQUE:
    "Prior work (PromptRobust, MulTypo, R2ATA) has already shown
    that typos degrade LLM performance. Your Experiment 1 is
    confirmatory, not novel. The compression angle is more
    interesting but CompactPrompt (2025) already showed 60%
    token reduction with <5% accuracy drop. What's new here?"

    RESPONSE / MITIGATION:
    The novelty is the COMBINATION study: noise + compression +
    cost accounting in a single framework. No prior work measures
    all three simultaneously. Specifically:
    - CompactPrompt tested compression on clean prompts only.
      We test it on NOISY prompts (real-world condition).
    - PromptRobust measured degradation but NOT recovery.
      We measure the full cycle: degrade -> intervene -> recover.
    - No prior work includes the COST-BENEFIT ANALYSIS with
      real dollar figures and break-even curves.
    - The Stability Illusion (H5) is genuinely novel and
      supported by a paper published days ago.

    ACTION: Strengthen the "Related Work" section to explicitly
    state what each prior paper did NOT do that we do.


### 21.2 Reviewer #2: "Your Noise Is Fake"

    CRITIQUE:
    "Synthetic noise generators do not reflect real user errors.
    Your Type B 'ESL patterns' are based on stereotyped L1
    transfer rules, not actual non-native speaker data. A real
    Mandarin speaker's errors are far more varied and contextual
    than simply dropping articles."

    RESPONSE / MITIGATION:
    This is the BIGGEST vulnerability in the paper. Mitigations:
    1. Validate Type B patterns against the Cambridge Learner
       Corpus error categories (published, peer-reviewed).
    2. Acknowledge explicitly that synthetic noise is a
       simplification in the Limitations section.
    3. Include a SMALL set of real human-written noisy prompts
       (collected from public forums like StackOverflow,
       Reddit r/learnprogramming) as a validation check.
    4. Call for real-user studies as the primary Future Work.

    STATUS (v4.0): PARTIALLY ADDRESSED. Phase 5 in the Data
    Collection Plan now includes 20 real-world noisy prompts
    collected from public sources as a validation set.


### 21.3 Reviewer #3: "The Stats Are Overcomplicated"

    CRITIQUE:
    "You propose GLMMs, bootstrap, McNemar's, Kendall's tau,
    AND Benjamini-Hochberg. This is a kitchen-sink approach.
    For a 200-prompt study, most of these tests will be
    underpowered. A simple permutation test on the pass/fail
    matrix would be cleaner and more interpretable."

    RESPONSE / MITIGATION:
    Partially valid. The GLMM is the RIGHT primary analysis
    because it handles the crossed random effects (prompt x
    model) that simpler tests cannot. But the reviewer is right
    that McNemar's on individual prompts may be underpowered
    with only 5 reps per cell. Mitigations:
    1. Make GLMM the PRIMARY analysis. Everything else is
       supplementary.
    2. Report McNemar's only as exploratory (for identifying
       fragile prompts), not as confirmatory.
    3. Add a power analysis to the pilot phase: after 20
       prompts, estimate whether N=200 is sufficient for the
       GLMM effect sizes we observe.

    ACTION: Add a "Power Analysis" subsection to Section 7.


### 21.4 Practitioner: "Nice Paper, But Can I Use This?"

    CRITIQUE:
    "You show that a pre-processor helps. But your pre-processor
    IS ITSELF an LLM call. So you're telling me to make TWO LLM
    calls per request to get better results? That doubles my
    latency and my cost. How is this practical?"

    RESPONSE / MITIGATION:
    This is why Section 12 (Optimizer Overhead Analysis) exists.
    We MUST show:
    1. The pre-processor can be a CHEAP, FAST model (Haiku/Flash)
       that adds <500ms and <$0.001 per call.
    2. For noisy/verbose prompts, the NET cost is NEGATIVE
       (savings > overhead) because compression reduces the
       main model's input tokens.
    3. The break-even analysis gives practitioners a clear
       decision rule: "If your prompts average >300 tokens
       and your user base includes >20% ESL speakers, deploy."
    4. Long-term, the optimizer could run CLIENT-SIDE (browser
       extension) or be built into the LLM vendor's UI,
       eliminating the extra API call entirely.

    ACTION: Ensure the break-even surface plot is one of the
    paper's main figures. Make the decision rule actionable.


### 21.5 Competing Lab: "Your Design Has Confounds"

    CRITIQUE:
    "Your 'Self-Correct' intervention (prepending 'fix my
    grammar then execute') uses TOKENS from the main model.
    Your 'Pre-Proc Sanitize' uses an EXTERNAL model. These
    are not comparable because one increases the main model's
    context window load and the other doesn't. Any difference
    could be due to context window effects, not correction
    quality."

    RESPONSE / MITIGATION:
    Valid. This is a real confound. Mitigations:
    1. Report the ACTUAL token counts for each intervention
       (the main model sees different prompt lengths).
    2. Add a control: "Self-Correct" with a PRE-PROCESSED
       correction (fix grammar externally, then prepend
       "I have already corrected grammar" to the clean prompt,
       so the main model sees the same token count as Raw
       but with a clean prompt).
    3. Discuss this confound explicitly in Limitations.

    ACTION: Add a 5th intervention column to the matrix:
    "Pre-Proc Sanitize Only (no compress)" to isolate the
    sanitization effect from the compression effect.


### 21.6 Reviewer #6: "Prompt Repetition Kills Your Thesis" (NEW v4.0)

    CRITIQUE:
    "Leviathan et al. showed that simply doubling the prompt
    improves accuracy for free. If prompt repetition also helps
    with noisy prompts, your expensive sanitize+compress pipeline
    is unnecessary. Users should just paste their prompt twice."

    RESPONSE / MITIGATION:
    This is why we ADD prompt repetition as an intervention
    column rather than ignoring it. Possible outcomes:
    1. Repetition works on clean prompts but NOT noisy ones
       (noise is amplified by repetition) --> our optimizer wins
    2. Repetition works on noisy prompts too --> both approaches
       are valid; ours additionally saves tokens via compression
    3. Repetition + sanitization combined is best --> compound
       intervention is the recommendation

    The experiment MUST include prompt repetition to be credible.
    Omitting it would be a glaring reviewer target.


### 21.7 Summary: Top 6 Risks to Address Before Submission

    RANK  RISK                          MITIGATION STATUS
    ~~~~  ~~~~~~~~~~~~~~~~~~~~~~~~~~    ~~~~~~~~~~~~~~~~~~~
    1     Synthetic noise validity      ADDRESSED in v4.0
                                        (real samples added
                                        to Phase 5)
    2     Novelty vs. CompactPrompt     Mitigated (combined
                                        framework is new)
    3     Practitioner relevance         Mitigated (break-even
          (cost/latency overhead)       analysis added in v3.0)
    4     Prompt repetition as           ADDRESSED in v4.0
          simpler alternative            (added as 5th
                                        intervention column)
    5     Self-Correct confound          Mitigated (prompt
                                        repetition serves as
                                        zero-overhead control)
    6     Statistical power for          Add power analysis
          prompt-level tests             to pilot phase


---

## 22. Execution Platform: Claude Code CLI vs API (NEW v4.0)

### 22.1 The Question

Can you use a paid Claude Code CLI subscription for this research,
or must you use direct API calls with Python scripts?

### 22.2 Recommendation: API for Experiments, CLI for Development

    USE CASE                       PLATFORM        WHY
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  ~~~~~~~~~~~~~~  ~~~~~~~~~~~~~~~~~~~~
    Building tooling (noise gen,   Claude Code     Fast iteration,
    compressor, harness scripts)   CLI (Max plan)  interactive, use
                                                   your existing sub

    Running the 20,000-call        Python scripts  REQUIRED for
    experiment matrix               + Anthropic     precise measurement
                                   API directly    of TTFT, TTLT,
                                                   token counts, cost

    Autonomous overnight runs      Claude Code     Can orchestrate via
    (Karpathy loop Phase 2-3)      CLI in batch    research_program.md
                                   mode            but less precise

    WHY API IS REQUIRED FOR THE EXPERIMENT:

    1. MEASUREMENT PRECISION: The API returns exact token counts
       (input_tokens, output_tokens) and timing in the response
       headers/body. Claude Code CLI aggregates these internally
       and only exposes them via /cost (session-level, not
       per-call).

    2. TTFT/TTLT: The API with streaming enabled lets you measure
       time-to-first-token precisely by recording when the first
       chunk arrives. Claude Code CLI does not expose this.

    3. REPRODUCIBILITY: API calls with temperature=0.0 and a
       fixed model string are reproducible. CLI sessions include
       system prompts, CLAUDE.md, tool definitions, and other
       context that varies between sessions.

    4. COST ACCOUNTING: API usage is billed per-token with exact
       pricing. CLI subscriptions (Pro/Max) are flat-rate with
       usage limits — you cannot compute "cost per prompt" from
       a subscription.

    5. RATE CONTROL: API calls can be paced with explicit rate
       limiting and retry logic. CLI has its own rate limiting
       that you cannot control.

### 22.3 Hybrid Workflow

    PHASE 1 (Tooling):     Use Claude Code CLI to build scripts
    PHASE 2 (Experiments): Use Python + API for all 20,000 calls
    PHASE 3 (Exploration): Use Claude Code CLI for creative search
    PHASE 4 (Writing):     Use Claude Code CLI for paper drafting

    COST ESTIMATE (API portion only):
    ~20,000 calls x ~500 tokens avg input x ~300 tokens avg output
    Claude Sonnet: $3/M input, $15/M output
    Input:  20K x 500 = 10M tokens x $3/M  = $30
    Output: 20K x 300 = 6M tokens x $15/M  = $90
    Pre-proc (Haiku): ~$5-10
    TOTAL API COST: ~$125-130

    Your existing Claude Code CLI subscription covers all non-
    experiment work (tooling, analysis, writing). The API cost
    for the actual experiments is a separate, modest expense.

### 22.4 Tools for CLI Token Tracking (Informational)

    If you DO want to track CLI usage for non-experiment work:

    - /cost command: shows session-level token usage and cost
    - /context command: shows current context window fill
    - ccusage (github.com/ryoppippi/ccusage): CLI tool that
      analyzes Claude's local JSONL files for daily/monthly
      token reports
    - Claude-Code-Usage-Monitor: real-time terminal dashboard
      with burn rate analytics

    These are useful for budget management but NOT for
    scientific measurement of per-prompt metrics.


---

## 23. Expanded Future Work Catalog (NEW v4.0)

The following are research directions that extend this study.
They are deliberately OUT OF SCOPE for the first paper but
are documented here as a roadmap for follow-up work.

### 23.1 Coding Assistants & OpenClaw Integration

    How do our findings translate to coding assistant contexts
    where the prompt includes not just user instructions but
    also file context, error messages, and tool outputs?
    Coding assistants like Cursor, Claude Code, and OpenClaw
    could integrate the optimizer as a pre-processing step
    via CLAUDE.md, .cursorrules, or AGENTS.md files.

### 23.2 Non-English Languages

    Does our noise-degradation curve differ across languages?
    MulTypo (2025) showed that models are more robust to English
    typos than to typos in lower-resource languages. A follow-up
    study should test the full pipeline (noise + compression +
    recovery) in Spanish, Mandarin, Arabic, and Yoruba to
    measure the "Linguistic Tax" for each language.

    KEY QUESTION: Do specific languages suffer MORE from the
    same % error rate? Or do some languages IMPROVE MORE with
    the same intervention? This has equity implications.

### 23.3 Model Breadth & Generational Comparison

    Test additional models (Llama, Mistral, Qwen) and compare
    across model generations (e.g., GPT-4o vs GPT-5.0 vs 5.1).
    Does robustness improve with each generation, or does
    instruction tuning continue to make models more brittle?

### 23.4 Distilled Models

    Do smaller distilled models (e.g., DeepSeek-R1-Distill,
    Llama-3-8B vs 70B) retain robustness to noise, or does
    distillation preferentially discard the "noise tolerance"
    capability? If distilled models are more brittle, the
    optimizer becomes MORE valuable for cost-conscious
    deployments that use smaller models.

### 23.5 Model Architecture Types

    Extend beyond text-only causal LLMs to:
    - Mixture-of-Experts (MoE) models: do different experts
      handle noisy vs. clean input differently?
    - Speech-to-text pipelines: ASR errors compound with
      user noise (see 23.6)
    - Image generation: do typos in DALL-E/Midjourney prompts
      cause different failure modes?
    - Multi-modal models: does noise in text affect image
      understanding or vice versa?

### 23.6 Voice Input vs. Keyboard Input

    People speak differently from how they type. Voice input
    introduces unique noise: filler words ("um", "uh"),
    false starts, stuttering, self-corrections, and ASR
    transcription errors. A follow-up study should compare:
    - Typed prompt (with typos)
    - Voice-transcribed prompt (with ASR errors)
    - Voice-transcribed + optimizer

    This is increasingly relevant as voice-first AI interfaces
    grow (Siri, Alexa, voice-mode ChatGPT).

### 23.7 Regional English Dialects

    English is spoken natively in the UK, USA, Australia,
    New Zealand, South Africa, India, Singapore, and more.
    Each has distinct:
    - Spelling conventions (optimize/optimise, color/colour)
    - Vocabulary (boot/trunk, lift/elevator)
    - Idioms and phrasing patterns
    - Date/number formatting (DD/MM vs MM/DD)

    Do these variations affect LLM reasoning accuracy?
    Are models biased toward American English (likely, given
    training data distribution)? Does the optimizer need to
    be dialect-aware?

### 23.8 Case Syntax / Naming Conventions

    Programming uses specific multi-word identifier formats:

    STYLE                 EXAMPLE         CONTEXT
    ~~~~~~~~~~~~~~~~~~~~  ~~~~~~~~~~~~~~  ~~~~~~~~~~~~~~~~~~
    snake_case            user_name       Python, Rust, Ruby
    camelCase             userName        JavaScript, Java
    PascalCase            UserName        Classes, C#, Go
    kebab-case            user-name       URLs, CSS, CLI args
    SCREAMING_SNAKE       USER_NAME       Constants
    Sentence case         User name       Prose, headings

    RESEARCH QUESTION: When a user writes "username" but means
    "user_name" (Python context) or "userName" (JS context),
    does the LLM infer the correct convention from context?
    Do naming convention errors in code prompts cause more
    severe failures than natural language typos? Could the
    optimizer auto-detect the target language's convention
    and normalize identifiers?

    This is particularly relevant for coding assistants where
    convention violations can cause actual runtime errors.

### 23.9 English Variant Standardization

    Our study uses American English. Future work should test
    whether British English prompts produce measurably different
    results on the same benchmarks, and whether the optimizer
    should normalize to one variant or preserve the user's
    dialect.


---

## Appendix A: Comparison with Gemini RDD

The following table notes where this document AGREES with and
DIVERGES from the Gemini-proposed Research Design:

    ELEMENT              GEMINI RDD             THIS RDD (v4.0)
    ~~~~~~~~~~~~~~~~~~~  ~~~~~~~~~~~~~~~~~~~~   ~~~~~~~~~~~~~~~~~~~~
    Core thesis          Linguistic Tax         AGREES
    Noise types          Character + ESL        AGREES (but adds
                                                specific L1 patterns)
    Compression study    Not included           ADDED (novel
                                                contribution)
    Experimental design  3x3 Factorial          Simplified to 2x4
                                                + separate compression
    Models               Gemini + Claude        AGREES (2 models)
    Grammarly personas   Core variable          SCOPED: browser-only,
                                                optional; AI Prompt
                                                Persona concept added
    R=0.85 claim         Stated as fact         FLAGGED (unverified;
                                                needs citation)
    Benchmarks           HumanEval only         EXPANDED to HumanEval
                                                + MBPP + GSM8K
    Scope                Broad                  TIGHTENED for
                                                publishability
    Cost analysis        Not included           ADDED (full cost-
                                                benefit with TTFT,
                                                TTLT, break-even)
    Statistical methods  t-test / Cohen's d     EXPANDED to GLMM,
                                                bootstrap, McNemar's,
                                                Kendall's tau, BH
    Stability analysis   Not included           ADDED (stability vs
                                                correctness matrix)
    Execution strategy   Manual scripting       HYBRID: manual build
                                                + Karpathy-style
                                                autonomous execution
    Pre-registration     Not mentioned          ADDED (OSF deposit)
    Latency tracking     Not mentioned          ADDED (TTFT, TTLT,
      (NEW v3.0)                                preproc overhead)
    Break-even analysis  Not mentioned          ADDED (deployment
      (NEW v3.0)                                decision rule)
    Literature review    Not included           ADDED (15+ real ArXiv
      (NEW v3.0)                                papers cataloged)
    Adversarial review   Not included           ADDED (6 weaknesses
      (NEW v3.0, v4.0)                         identified + mitigated)
    Prompt repetition    Not considered         ADDED as 5th intervention
      (NEW v4.0)                                (Google paper ArXiv:
                                                2512.14982)
    Future work catalog  Brief                  EXPANDED to 9 topics
      (NEW v4.0)                                (voice, dialects, case
                                                syntax, distillation...)
    Execution platform   Not discussed          ADDED: API for experiments
      (NEW v4.0)                                CLI for development


---

## Appendix B: Key References Informing v2.0 and v3.0

    SOURCE                                  CONTRIBUTION TO THIS RDD
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  ~~~~~~~~~~~~~~~~~~~~~~~~
    NIST AI 800-3 (Feb 2026)               GLMMs for LLM evaluation;
    "Expanding the AI Evaluation Toolbox    benchmark vs. generalized
    with Statistical Models"                accuracy distinction

    Riasat (Mar 2026)                       Stability != correctness;
    "When Stability Fails: Hidden           LLMs can be stable and
    Failure Modes of LLMs"                  systematically wrong

    ICLR 2026                               LLM rankings are fragile
    "Robustness of Rankings from LLM        to small data drops;
    Evaluation Systems"                     need bootstrap analysis

    NAACL 2025 Industry Track               SCORE framework for
    "Systematic Consistency and             consistency rate metric;
    Robustness Evaluation"                  prompt robustness tasks

    Karpathy (Mar 2026)                     Autonomous experiment
    autoresearch                            loop pattern; program.md
                                            as "research org code"

    Survey: Robustness in LLMs             Instruction-tuned models
    (Nov 2025, ResearchGate)               may be MORE brittle to
                                            noise than base models

    Gan et al. (2024) R2ATA               1 char edit drops accuracy
    ArXiv: 2411.05345                      5-10% on GSM8K (v3.0)

    MulTypo (2025)                         Multilingual typo generation;
    ArXiv: 2510.09536                      instruction tuning doesn't
                                            help robustness (v3.0)

    PromptRobust (2024)                    4,788 adversarial prompts;
    ArXiv: 2306.04528                      39% avg drop from word-level
                                            attacks (v3.0)

    CompactPrompt (2025)                   60% token reduction, <5%
    ArXiv: 2510.18043                      accuracy drop; our direct
                                            compression baseline (v3.0)

    LLMLingua (2023)                       Foundational prompt
    ArXiv: 2310.05736                      compression; up to 20x
                                            compression (v3.0)

    ProCut (2025)                          Prompt compression via
    ArXiv: 2508.02053                      attribution / Shapley
                                            values (v3.0)

---

*End of Research Design Document v4.0*
