"""Analyse the token-budget sweep: beta_M and unparseable rate vs max_tokens,
per verifier. Produces the confound figure.
Run from maf-bench root:  python3 07b_sweep_analysis.py
"""
import glob, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd, numpy as np
from statsmodels.stats.proportion import proportion_confint
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import config

f = sorted(glob.glob(f"{config.GRADED}/graded_sweep_*.jsonl"))
assert f, "Grade the sweep first: python3 grading/04_grade.py --file data/trials/sweep_*.jsonl"
df = pd.DataFrame(json.loads(l) for l in open(f[-1]))
print(f"Analyzing: {f[-1]}  ({len(df)} trials)")

rows = []
for (v, b), grp in df.groupby(["verifier", "max_tokens"]):
    invalid = (grp["grade"] == "invalid").sum()
    valid = grp[grp["grade"] != "invalid"]
    k, n = (valid["grade"] == "accept").sum(), len(valid)
    lo, hi = proportion_confint(k, n, alpha=0.05, method="wilson") if n else (np.nan, np.nan)
    rows.append({"verifier": v, "max_tokens": b, "beta_m": k/n if n else np.nan,
                 "lo": lo, "hi": hi, "n_valid": n,
                 "unparseable_rate": invalid/len(grp)})
res = pd.DataFrame(rows).sort_values(["verifier", "max_tokens"])
print("\n=== beta_M and unparseable rate vs token budget ===")
print(res.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
os.makedirs(f"{config.RESULTS}/figures", exist_ok=True)
res.to_csv(f"{config.RESULTS}/token_sweep.csv", index=False)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))
colors = {"claude": "#c0504d", "gpt4o": "#4472c4", "llama": "#9bbb59"}
for v, grp in res.groupby("verifier"):
    grp = grp.sort_values("max_tokens")
    ax1.errorbar(grp["max_tokens"], grp["beta_m"],
                 yerr=[grp["beta_m"]-grp["lo"], grp["hi"]-grp["beta_m"]],
                 marker="o", capsize=3, label=v, color=colors.get(v))
    ax2.plot(grp["max_tokens"], grp["unparseable_rate"], marker="s", label=v, color=colors.get(v))
for ax, ylab, title in [(ax1, r"$\beta_M$", "Measured acceptance vs token budget"),
                        (ax2, "unparseable rate", "Truncated/unparseable responses")]:
    ax.set_xscale("log"); ax.set_xticks([20, 50, 100, 200, 400])
    ax.set_xticklabels([20, 50, 100, 200, 400]); ax.set_xlabel("max_tokens")
    ax.set_ylabel(ylab); ax.set_title(title); ax.legend()
plt.tight_layout(); plt.savefig(f"{config.RESULTS}/figures/token_sweep.png", dpi=200)
print(f"\nFigure -> {config.RESULTS}/figures/token_sweep.png")
