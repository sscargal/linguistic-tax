# Paper Outline Reference

Source: RDD Section 15

## Title
"The Linguistic Tax: Quantifying Prompt Noise and Bloat in LLM Reasoning, and the Case for Automated Prompt Optimization"

## Sections

### I. Abstract (0.5 pages)
- Problem: Natural language interfaces punish imperfect input
- Method: 2x4 factorial + compression study on 200 prompts, 2 models, 5 reps
- Key finding: Combined sanitize+compress recovers >80% accuracy AND reduces tokens >25%
- Implication: Native prompt optimization layer should be standard in LLM interfaces

### II. Introduction (1.5 pages)
- The Two-Headed Problem: Noise (linguistic tax) + Bloat (token tax)
- ESL equity angle: non-native speakers pay a higher tax
- Hidden cost: users unaware of degradation
- Research questions mapping to H1-H5
- Contributions: (1) quantify noise cliff, (2) measure ESL penalty, (3) discover stability illusion, (4) demonstrate compression dividend, (5) build and evaluate prompt optimizer

### III. Related Work (2.0 pages)
Key papers from RDD Section 20:
- PromptRobust (Zhu et al., 2023) — character-level robustness
- R2ATA (Zhao & Xu, 2024) — adversarial typos as attention attacks
- MulTypo (Yang et al., 2025) — multilingual typo robustness
- LLMLingua (Jiang et al., 2023) — prompt compression
- Gan et al. (2024) — GSM8K character edits
- Leviathan et al. (2025) — prompt repetition (Google)
- Gap: no combined study of noise + compression + cost on frontier models

### IV. Methodology (3.0 pages)
- Type A noise: character-level mutations (adjacent-key 40%, omission 25%, doubling 20%, transposition 15%)
- Type B noise: L1 transfer patterns (Mandarin, Spanish, Japanese, Mixed ESL)
- Compression: dedup + condensation with semantic similarity threshold >0.95
- 5 interventions: Raw, Self-Correct, Sanitize, Sanitize+Compress, Prompt Repetition
- Experiment matrix: 200 prompts x 8 noise x 5 interventions x 2 models x 5 reps

### V. Statistical Framework (1.5 pages)
- GLMM with 3-level fallback (Bayesian mixed → reduced → GEE)
- Bootstrap CIs (10,000 resamples, 95%)
- McNemar's test for fragile/recoverable prompts
- Kendall's tau for rank-order stability
- BH correction for FDR at 5%
- Effect sizes alongside all p-values

### VI. Experimental Setup (1.0 pages)
- Models: Claude Sonnet (claude-sonnet-4-20250514), Gemini 1.5 Pro
- Benchmarks: HumanEval (164), MBPP (200 subset), GSM8K (200 subset)
- Grading: execution sandbox (code), regex match (math)
- Temperature: 0.0, 5 repetitions per condition
- Pre-processor: Haiku for Claude, Flash for Gemini

### VII. Results (4.0 pages)
7 findings, each with claim + evidence + statistical test + interpretation:
1. The Robustness Curve (noise vs accuracy — H1)
2. The ESL Penalty (Type B > Type A — H4)
3. The Stability Illusion (silent failures — H5)
4. The Compression Dividend (token savings — H2)
5. The Combined Win (sanitize+compress ROI — H3)
6. The Break-Even Curve (when optimizer pays for itself)
7. Optional: The Persona Effect (Grammarly integration)

### VIII. Cost-Benefit Analysis (1.0 pages)
- Full cost accounting with real token prices
- Break-even surface: noise level where optimizer saves more than it costs
- Enterprise projection: annual savings at scale

### IX. Discussion (1.5 pages)
- Case for native prompt optimization in LLM UIs
- Coding assistant integration (CLAUDE.md, .cursorrules)
- Browser middleware / MCP gateway concept
- AI Prompt Persona (Grammarly-style)

### X. Limitations (0.5 pages)
- 2-model selection bias
- English focus (American only)
- Synthetic vs. real noise
- Self-Correct confound
- Agent execution reproducibility

### XI. Conclusion & Future Work (0.5 pages)
- Global Robustness Score proposal
- Multi-language expansion
- Real user study
- Browser extension product

### Appendices
A. Noise generation algorithms
B. Full results tables
C. Prompt compression examples
D. research_program.md
E. GLMM specification & code
F. Break-even analysis details
G. Full literature review table
