---
phase: 22-experiment-all-caps-and-emphasis-formatting-effects-on-llm-attention
verified: 2026-03-26T20:52:18Z
status: passed
score: 14/14 must-haves verified
re_verification: false
---

# Phase 22: Emphasis Formatting Effects on LLM Attention — Verification Report

**Phase Goal:** Implement emphasis conversion infrastructure and generate experiment-ready prompt variants for three clusters: (A) key-term emphasis with bold/CAPS/quotes per AQ-NH-05, (B) instruction-word emphasis testing the "shouting confound", and (C) sentence-initial capitalization effects — producing 1,100 total experiment matrix items across all clusters.
**Verified:** 2026-03-26T20:52:18Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                             | Status     | Evidence                                                                                     |
|----|---------------------------------------------------------------------------------------------------|------------|----------------------------------------------------------------------------------------------|
| 1  | All 8 emphasis conversion functions exist and produce correct output                              | VERIFIED   | `src/emphasis_converter.py` defines: apply_bold_emphasis, apply_caps_emphasis, apply_quotes_emphasis, apply_instruction_caps, apply_instruction_bold, apply_mixed_emphasis, apply_aggressive_caps, lowercase_sentence_initial — all tested, 34 passing unit tests |
| 2  | Code blocks inside prompts are not modified by any conversion function                            | VERIFIED   | `_split_code_and_text` + `_apply_to_text_only` helpers enforce code-block protection; fenced and docstring-aware detection; tests: `test_bold_skips_fenced_code`, `test_instruction_caps_skips_indented_code`, et al. |
| 3  | 8 new intervention types are registered in INTERVENTIONS tuple (13 total)                        | VERIFIED   | `src/config.py` INTERVENTIONS has 13 entries: 5 original + 8 emphasis (emphasis_bold, emphasis_caps, emphasis_quotes, emphasis_instruction_caps, emphasis_instruction_bold, emphasis_lowercase_initial, emphasis_mixed, emphasis_aggressive_caps) |
| 4  | run_experiment.py routes all 8 emphasis interventions to their handlers                           | VERIFIED   | `apply_intervention` match/case has: Cluster A/B cache group (`emphasis_bold | emphasis_caps | emphasis_quotes | emphasis_mixed | emphasis_aggressive_caps`), plus direct-dispatch cases for emphasis_instruction_caps, emphasis_instruction_bold, emphasis_lowercase_initial |
| 5  | load_emphasis_variant handles both flat (Cluster A) and nested (Cluster B) JSON schemas           | VERIFIED   | Intervention-to-file map at line 430-434; schema auto-detection by checking if "prompts" key values are dicts vs strings; tested in test_load_emphasis_variant_schema_detection |
| 6  | 20 HumanEval/MBPP prompts selected with 3 key terms each for Cluster A                           | VERIFIED   | `data/emphasis/cluster_a_key_terms.json` has 20 prompts; all have exactly 3 key_terms; sources: HumanEval and Mbpp |
| 7  | Each Cluster A prompt has bold, CAPS, and quotes variants stored as reproducible JSON             | VERIFIED   | cluster_a_bold.json (20 entries, all contain `**`), cluster_a_caps.json (20 entries, uppercase key terms confirmed), cluster_a_quotes.json (20 entries); idempotent generation script at scripts/generate_emphasis_cluster_a.py |
| 8  | Cluster A experiment matrix contains 400 items (20 prompts x 4 conditions x 5 reps)              | VERIFIED   | `data/emphasis_matrix_a.json` has exactly 400 items; interventions = {raw, emphasis_bold, emphasis_caps, emphasis_quotes} |
| 9  | 20 prompts selected for Cluster B with instruction verbs/negations present                        | VERIFIED   | `data/emphasis/cluster_b_variants.json` has 20 prompts in nested schema; selected by instruction verb count in docstrings via _extract_natural_language |
| 10 | Cluster B has 5 conditions: raw, instruction_caps, instruction_bold, mixed_emphasis, aggressive_caps | VERIFIED | `data/emphasis_matrix_b.json` has 500 items; interventions = {raw, emphasis_instruction_caps, emphasis_instruction_bold, emphasis_mixed, emphasis_aggressive_caps} |
| 11 | 20 prompts selected for Cluster C with multiple sentences                                         | VERIFIED   | `data/emphasis/cluster_c_variants.json` has 20 prompts in nested schema; selected by sentence boundary count |
| 12 | Cluster C has 2 conditions: raw and lowercase_initial                                             | VERIFIED   | `data/emphasis_matrix_c.json` has 200 items; interventions = {raw, emphasis_lowercase_initial} |
| 13 | Total experiment matrix across all clusters = 1,100 items                                         | VERIFIED   | 400 (Cluster A) + 500 (Cluster B) + 200 (Cluster C) = 1,100 items |
| 14 | All 121 tests pass                                                                                 | VERIFIED   | `pytest tests/test_emphasis_converter.py tests/test_emphasis_clusters_bc.py tests/test_run_experiment.py tests/test_config.py` — 121 passed in 1.28s |

**Score:** 14/14 truths verified

---

### Required Artifacts

| Artifact                                         | Expected                                               | Status     | Details                                                     |
|--------------------------------------------------|--------------------------------------------------------|------------|-------------------------------------------------------------|
| `src/emphasis_converter.py`                      | All emphasis conversion functions                      | VERIFIED   | 507 lines; 8 conversion functions + helpers; type hints + docstrings throughout |
| `tests/test_emphasis_converter.py`               | Unit tests, min 100 lines                              | VERIFIED   | 349 lines; 34 test methods covering all functions, code protection, overlapping terms, both cache schemas |
| `src/config.py`                                  | INTERVENTIONS with 13 entries including emphasis_bold  | VERIFIED   | Contains all 8 emphasis entries; total 13 interventions confirmed by import test |
| `src/run_experiment.py`                          | match/case routing for all emphasis interventions      | VERIFIED   | Import at line 44; prompt_id param at line 91; 3 case groups covering all 8 emphasis interventions |
| `data/emphasis/cluster_a_key_terms.json`         | 20 prompts with 3 key terms each                       | VERIFIED   | 20 entries, all with exactly 3 key_terms and 3 term_types |
| `data/emphasis/cluster_a_bold.json`              | 20 prompts with `**bold**` key terms                   | VERIFIED   | 20 entries, all contain `**` markers |
| `data/emphasis/cluster_a_caps.json`              | 20 prompts with ALL CAPS key terms                     | VERIFIED   | 20 entries, uppercase terms confirmed |
| `data/emphasis/cluster_a_quotes.json`            | 20 prompts with 'quoted' key terms                     | VERIFIED   | 20 entries |
| `data/emphasis_matrix_a.json`                    | 400-item experiment matrix for Cluster A               | VERIFIED   | 400 items; model=nvidia/nemotron-3-super-120b-a12b:free; experiment=emphasis_cluster_a; all required fields present |
| `scripts/generate_emphasis_cluster_a.py`         | Reproducible generation script                         | VERIFIED   | Contains `if __name__ == "__main__":` guard; imports from src.emphasis_converter |
| `data/emphasis/cluster_b_variants.json`          | 20 prompts x 4 treatment variants, nested schema       | VERIFIED   | 20 prompts; all have emphasis_mixed and emphasis_aggressive_caps; metadata key present |
| `data/emphasis/cluster_c_variants.json`          | 20 prompts x 1 treatment variant                       | VERIFIED   | 20 prompts in nested schema |
| `data/emphasis_matrix_b.json`                    | 500-item experiment matrix for Cluster B               | VERIFIED   | 500 items; experiment=emphasis_cluster_b; all 5 conditions; all required fields present |
| `data/emphasis_matrix_c.json`                    | 200-item experiment matrix for Cluster C               | VERIFIED   | 200 items; experiment=emphasis_cluster_c; 2 conditions (raw + emphasis_lowercase_initial) |
| `scripts/generate_emphasis_clusters_bc.py`       | Reproducible generation script for Clusters B and C   | VERIFIED   | Contains `if __name__ == "__main__":` guard; imports from src.emphasis_converter |
| `tests/test_emphasis_clusters_bc.py`             | Validation tests for generated variants                | VERIFIED   | 30 test methods; covers variant counts, code preservation, matrix format, routing integration, new conversion functions |

---

### Key Link Verification

| From                                  | To                         | Via                                                   | Status   | Details                                                                                     |
|---------------------------------------|----------------------------|-------------------------------------------------------|----------|---------------------------------------------------------------------------------------------|
| `src/run_experiment.py`               | `src/emphasis_converter.py` | `from src.emphasis_converter import` at line 44      | WIRED    | Imports load_emphasis_variant, apply_instruction_caps, apply_instruction_bold, lowercase_sentence_initial |
| `src/config.py` INTERVENTIONS         | `src/run_experiment.py`    | match/case strings matching INTERVENTIONS values      | WIRED    | All 8 emphasis INTERVENTIONS entries have corresponding match/case branches |
| `data/emphasis/cluster_a_bold.json`   | `src/emphasis_converter.py` | load_emphasis_variant file map at lines 430-434      | WIRED    | "emphasis_bold" -> "cluster_a_bold.json"; same for caps and quotes |
| `data/emphasis_matrix_a.json`         | `src/run_experiment.py`    | matrix intervention values match case strings         | WIRED    | interventions in matrix = {raw, emphasis_bold, emphasis_caps, emphasis_quotes} all have routes |
| `data/emphasis_matrix_b.json`         | `src/run_experiment.py`    | matrix intervention values match case strings         | WIRED    | emphasis_instruction_caps and emphasis_instruction_bold confirmed in matrix and routed |
| `data/emphasis_matrix_c.json`         | `src/run_experiment.py`    | matrix intervention=emphasis_lowercase_initial        | WIRED    | emphasis_lowercase_initial confirmed in matrix and routed |
| `data/emphasis/cluster_b_variants.json` | `src/emphasis_converter.py` | load_emphasis_variant reads nested schema           | WIRED    | "emphasis_mixed" and "emphasis_aggressive_caps" map to cluster_b_variants.json; nested schema auto-detected |

---

### Requirements Coverage

| Requirement | Source Plan | Description                                                                              | Status    | Evidence                                                                                                           |
|-------------|-------------|------------------------------------------------------------------------------------------|-----------|-------------------------------------------------------------------------------------------------------------------|
| INFRA       | 22-01-PLAN  | Emphasis conversion infrastructure: module, config, routing                              | SATISFIED | emphasis_converter.py created with 8 functions; INTERVENTIONS expanded to 13; apply_intervention fully routed     |
| AQ-NH-05    | 22-02-PLAN  | Emphasis markers on key terms (Bold, CAPS, Quotes) — HumanEval/MBPP, 400 matrix items   | SATISFIED | 20 prompts selected; 3 variant JSONs generated; 400-item matrix with correct fields and conditions                |
| CLUSTER-B   | 22-03-PLAN  | Instruction-word emphasis experiment: 5 conditions, 500-item matrix                      | SATISFIED | 20 prompts selected by instruction verb count; cluster_b_variants.json with nested schema; 500-item matrix        |
| CLUSTER-C   | 22-03-PLAN  | Sentence-initial capitalization experiment: 2 conditions, 200-item matrix                | SATISFIED | 20 prompts selected by sentence count; cluster_c_variants.json; 200-item matrix                                   |

Note: Requirement IDs INFRA, AQ-NH-05, CLUSTER-B, CLUSTER-C are project-internal labels defined in ROADMAP.md for Phase 22. They do not appear as named entries in REQUIREMENTS.md (which tracks v1.0 and v2.0 requirements for the configurable-models milestone). The requirement IDs are the phase's own experimental design specs, confirmed satisfied by the artifact and truth verification above.

---

### Anti-Patterns Found

None detected. Scanned `src/emphasis_converter.py`, `scripts/generate_emphasis_cluster_a.py`, `scripts/generate_emphasis_clusters_bc.py` for TODO/FIXME/PLACEHOLDER/empty returns. All clear.

---

### Human Verification Required

None. All verifiable truths are data-structural or programmatic. Experiment has not yet been executed (that is a future phase), so no LLM output quality assessment is needed at this stage.

---

### Gaps Summary

No gaps. All 14 must-have truths verified. Phase goal fully achieved.

The phase produced:
- A complete emphasis conversion library (8 functions, 507 lines, 34 unit tests)
- 13 registered intervention types (up from 5)
- Full routing through the existing apply_intervention pipeline
- Three experiment datasets totaling 1,100 matrix items:
  - Cluster A: 400 items (20 prompts x 4 conditions x 5 reps)
  - Cluster B: 500 items (20 prompts x 5 conditions x 5 reps)
  - Cluster C: 200 items (20 prompts x 2 conditions x 5 reps)
- Reproducible generation scripts and 30 validation tests

One notable design decision documented in SUMMARY.md: the generation scripts use `_replace_terms` directly (bypassing the public apply_*_emphasis API) because HumanEval/MBPP prompts place natural language inside indented docstrings that were initially misclassified as code blocks. The docstring-awareness fix was applied to `_split_code_and_text` and the generation scripts use the correct approach. All 121 tests pass.

---

_Verified: 2026-03-26T20:52:18Z_
_Verifier: Claude (gsd-verifier)_
