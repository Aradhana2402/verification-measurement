# Verification Measurement — Code & Data (Anonymous Release)

Reproduces the results in *Four Silent Failure Modes in Measuring Multi-Agent
LLM Verification*.

## Pipeline
1. `deliberate/00b_direct.py` — easy-query baseline (direct injection)
2. `harvesting/01_harvest.py` — harvest organic errors from SimpleQA Verified
3. `06_validate_errors.py` — validate errors (LLM equivalence + human audit)
4. `harvesting/02_tag_confidence.py` — confidence tagging
5. `trials/03_run_trials.py` — 3x3 verification grid
6. `grading/04_grade_v2.py` — gold-blind grading
7. `analysis/05_analysis.py` — beta_M, CIs, H1/H2/H3
8. `07_token_sweep.py` + `07b_sweep_analysis.py` — token-budget confound

## Pre-registration
OSF: 10.17605/OSF.IO/ARZET (original) and 10.17605/OSF.IO/R2EUC (addendum)

## Data
- `data/errors/validated_errors.jsonl` — 335 human-validated errors
- `data/graded/graded_trials_*.jsonl` — 900 primary trials, gold-blind graded
- `data/results/*_FINAL.csv` — result tables matching the paper

## Cost
Full pipeline: inference-only API calls, total < US$100.

Requires OPENAI/ANTHROPIC/TOGETHER API keys as environment variables.
