# Four Silent Failure Modes in Measuring Multi-Agent LLM Verification

Code, data, and audit trails for:

> Aradhana Krishnasare Rai and Vijay Krishna Madisetti. **Four Silent Failure Modes in Measuring Multi-Agent LLM Verification.** NeurIPS 2026 Workshop: *Who Verifies the Agents? Toward Reliable Agent Development*. Sydney, 2026. (Non-archival; [OpenReview](https://openreview.net/group?id=NeurIPS.cc/2026/Workshop/Verify-Agents), Submission 63.)

We measure peer-resistance, β_M = P(verifier accepts | peer answer is wrong), for three verifiers (GPT-4o, Claude Sonnet 4.6, Llama-3.3-70B) across all nine generator × verifier pairs. The paper documents four ways this measurement fails silently, each surfaced only by logging and auditing raw responses:

1. **Forcing prompts that safety-trained models refuse**, silently replacing wrong answers with correct ones.
2. **Invalid error sets**: 66% of string-matched "errors" were not errors.
3. **Token-budget truncation** that cuts deliberative verifiers off before a verdict, shifting one verifier's score by 47% relative.
4. **Gold-contaminated grading**, where a grader shown the gold answer judges correctness instead of transcribing the verifier's verdict.

After correcting all four, a pre-registered study on SimpleQA Verified finds that verifiers which catch 91–100% of injected errors on easy queries accept 30–81% of organic errors on rare ones, with a 51-percentage-point spread between verifiers.

## Pipeline

Run in order from the repository root. Model IDs and generation settings are in `config.py`.

| Step | Script | What it does |
|---|---|---|
| 0 | `fetch_simpleqa.py` | Download SimpleQA Verified |
| 1 | `deliberate/00b_direct.py` | Easy-query baseline: wrong answer injected directly into the verification prompt (47 questions × 3 verifiers, `max_tokens=20`) |
| 2 | `harvesting/01_harvest.py` | Harvest organic errors from SimpleQA Verified |
| 3 | `06_validate_errors.py` | Validate errors (LLM equivalence check + human audit) |
| 4 | `harvesting/02_tag_confidence.py` | Confidence tagging (for H3) |
| 5 | `trials/03_run_trials.py` | 3 × 3 generator × verifier grid, 100 errors per generator (900 trials, `max_tokens=200`) |
| 6 | `04_grade_v2.py` | Gold-blind grading of verifier responses |
| 7 | `analysis/05_analysis.py` | β_M, Wilson 95% CIs, Fisher's exact tests with Holm correction (H1–H3) |
| 8 | `07_token_sweep.py`, `07b_sweep_analysis.py` | Token-budget sweep: 60 errors × 3 verifiers × 5 budgets (Section 3.3, Figure 2) |

`grading/04_grade.py` is the original grader, which was shown the gold answer. It is kept to document failure mode 4; use `04_grade_v2.py` for all grading. Verifiers run at temperature 0.7. Grading, equivalence checks, and confidence tagging use GPT-4o-mini at temperature 0. The verification prompt is `prompts/verify_template.txt`.

## Data

| Path | Contents |
|---|---|
| `data/errors/validated_errors.jsonl` | 335 human-validated organic errors (GPT-4o 105, Claude 114, Llama 116) |
| `data/graded/graded_trials_20260724_141713.jsonl` | 900 primary trials (300 errors × 3 verifiers), gold-blind graded, with raw verifier responses |
| `data/graded/graded_deliberate_direct_20260724_085927.jsonl` | 141 easy-query baseline trials |
| `data/graded/graded_sweep_20260724_160005.jsonl` | 900 token-sweep trials |
| `data/results/beta_m_grid_FINAL.csv` | Table 2 |
| `data/results/beta_m_pooled_FINAL.csv` | Table 1 |
| `data/results/token_sweep.csv` | Figure 2 |

SimpleQA Verified is public; see Haas et al., [arXiv:2509.07968](https://arxiv.org/abs/2509.07968). It is used under its released license.

## Pre-registration

- Original protocol: [10.17605/OSF.IO/ARZET](https://doi.org/10.17605/OSF.IO/ARZET)
- Deviations addendum: [10.17605/OSF.IO/R2EUC](https://doi.org/10.17605/OSF.IO/R2EUC)

Pre-registered hypotheses that were not confirmed (H2; H3 for Claude and Llama) are reported in the paper as registered.

## Requirements and cost

All experiments are inference-only API calls. The full pipeline costs under US$100. Set these environment variables:

```
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
TOGETHER_API_KEY=...
```

## Relation to earlier work

This study began as an extension of our earlier pipeline ([multi-agent-llm-reliability](https://github.com/Aradhana2402/multi-agent-llm-reliability)). That pipeline generated wrong peer answers with a forcing prompt ("Answer exactly X"), which is failure mode 1 above. Peer-resistance results from that pipeline are superseded by the corrected measurements here.

## Citation

```bibtex
@inproceedings{rai2026silent,
  title     = {Four Silent Failure Modes in Measuring Multi-Agent {LLM} Verification},
  author    = {Rai, Aradhana Krishnasare and Madisetti, Vijay Krishna},
  booktitle = {NeurIPS 2026 Workshop: Who Verifies the Agents? Toward Reliable Agent Development},
  year      = {2026},
  note      = {Non-archival}
}
```

## License

MIT
