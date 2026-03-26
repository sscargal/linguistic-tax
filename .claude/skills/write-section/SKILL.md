---
name: write-section
description: Draft LaTeX sections for the Linguistic Tax ArXiv paper based on experiment results and the RDD whitepaper outline. Use this skill whenever the user wants to write part of the paper, draft a section, generate LaTeX for the paper, write the abstract, write methodology, write results, or assemble the paper. Also trigger when the user says "write the paper", "draft the intro", "write the results section", "generate LaTeX", "help me write section X", "draft the abstract", or "assemble the paper".
---

# Write Section

Draft publication-ready LaTeX sections for the ArXiv paper "The Linguistic Tax: Quantifying Prompt Noise and Bloat in LLM Reasoning, and the Case for Automated Prompt Optimization."

## Paper structure

The RDD (Section 15) defines the paper outline. Read `references/paper-outline.md` for the full structure with content guidance per section.

The paper has 11 main sections plus appendices, targeting ~17 pages:

| # | Section | Pages | Key content |
|---|---------|-------|-------------|
| I | Abstract | 0.5 | Problem, method, key finding |
| II | Introduction | 1.5 | The linguistic tax concept, ESL equity, hidden costs |
| III | Related Work | 2.0 | PromptRobust, MulTypo, LLMLingua, evaluation methods |
| IV | Methodology | 3.0 | Noise injection, compression, interventions, design |
| V | Statistical Framework | 1.5 | GLMM, bootstrap, McNemar's, BH correction |
| VI | Experimental Setup | 1.0 | Models, benchmarks, reproduction instructions |
| VII | Results | 4.0 | 7 findings (noise cliff, ESL penalty, stability illusion, etc.) |
| VIII | Cost-Benefit Analysis | 1.0 | Break-even curves, enterprise projections |
| IX | Discussion | 1.5 | Implications for LLM UI, prompt optimization case |
| X | Limitations | 0.5 | Model bias, English focus, synthetic noise |
| XI | Conclusion & Future Work | 0.5 | Global Robustness Score, browser extension, expansion |

## Process for drafting a section

### 1. Gather inputs

For each section, read the relevant sources:

- **RDD**: `docs/RDD_Linguistic_Tax_v4.md` — the spec for what goes in each section
- **Results data**: `results/results.db` and `results/analysis/` — actual numbers to cite
- **Figures**: `figures/` — reference figure filenames for `\includegraphics`
- **Literature**: RDD Section 20 — papers to cite with ArXiv IDs
- **Previous sections**: Maintain consistency in terminology and notation

### 2. Write LaTeX

Use the `article` document class with standard ArXiv formatting:
- `\usepackage{amsmath, amssymb, graphicx, booktabs, hyperref}`
- Tables use `booktabs` style (`\toprule`, `\midrule`, `\bottomrule`)
- Figures referenced as `\ref{fig:accuracy_curves}` etc.
- Citations use `\cite{author2025}` format

### 3. Data-driven content

For the Results section especially, pull actual numbers from the analysis output:

```python
# Read analysis results
import json
with open("results/analysis/glmm_results.json") as f:
    glmm = json.load(f)

with open("results/analysis/bootstrap_cis.json") as f:
    bootstrap = json.load(f)
```

Every claim must cite a specific number with confidence interval. Example:
> "At 20\% character noise, accuracy dropped to 45.2\% (95\% CI: [42.1, 48.3]), a Robustness Ratio of R=0.58 compared to the clean baseline of 78.0\%."

### 4. Section-specific guidance

**Abstract**: Write LAST (after all other sections). Lead with the problem ("LLM users bear a hidden 'linguistic tax'"), state the method, report the headline number, end with the implication.

**Introduction**: Frame around the Two-Headed Problem diagram from the RDD. Introduce the 5 hypotheses as research questions. End with contributions list.

**Methodology**: Must be reproducible. Include algorithm pseudocode for noise injection. Reference the exact model versions (from model registry configuration) and seeds. Note that models are configurable — the methodology should describe this as a feature of the toolkit.

**Results**: Organize by Finding 1-7. Each finding gets: claim, evidence (table/figure), statistical test result, interpretation. Use the hypothesis scorecard.

**Discussion**: Connect findings to practical implications. The "case for automated prompt optimization" is the paper's thesis — this is where you make it.

## LaTeX conventions

- American English throughout
- Numbers: spell out one through nine, use digits for 10+
- Percentages: "5\%" not "five percent" in running text
- Statistical values: $p < 0.05$, $\tau = 0.83$, OR = 2.4 (95\% CI: [1.8, 3.1])
- First use of acronyms: spell out with acronym in parentheses
- Table/figure captions should be self-contained (readable without body text)

## Output

Write LaTeX to `paper/` directory:
- `paper/main.tex` — master document with `\input{}` for each section
- `paper/sections/abstract.tex`
- `paper/sections/introduction.tex`
- `paper/sections/related_work.tex`
- `paper/sections/methodology.tex`
- etc.

## Important notes

- The RDD literature review (Section 20) contains real ArXiv paper citations with IDs — use these
- Every quantitative claim needs a source (analysis output, figure reference, or table)
- The paper targets cs.CL (Computation and Language) and cs.AI (Artificial Intelligence) categories
- Target length is ~17 pages including references
- The toolkit supports configurable models — methodology and setup sections should reflect this. Model versions come from model_registry, not hardcoded constants.
