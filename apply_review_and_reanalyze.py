"""Filters trials to human-validated errors only, then recomputes all statistics.
Run from maf-bench root AFTER copying valid_error_ids.json into the folder:
    python3 apply_review_and_reanalyze.py
"""
import json, glob, collections
import pandas as pd, numpy as np
from scipy.stats import fisher_exact
from statsmodels.stats.proportion import proportion_confint

valid = {(v["generator"], v["id"]) for v in json.load(open("valid_error_ids.json"))}
print(f"Human-validated errors: {len(valid)}")

gf = sorted(glob.glob("data/graded/graded_trials_*.jsonl"))[-1]
rows = [json.loads(l) for l in open(gf)]
kept = [r for r in rows if (r["generator"], r["query_id"]) in valid and r["grade"] != "invalid"]
print(f"Trials: {len(rows)} -> {len(kept)} after validation filter + invalid removal\n")

df = pd.DataFrame(kept); df["accept"] = (df["grade"] == "accept").astype(int)

def wil(k, n): return proportion_confint(k, n, alpha=0.05, method="wilson") if n else (np.nan, np.nan)

print("=== beta_M per cell (validated errors only) ===")
cells = []
for (g, v), grp in df.groupby(["generator", "verifier"]):
    k, n = int(grp["accept"].sum()), len(grp); lo, hi = wil(k, n)
    cells.append({"generator": g, "verifier": v, "accepts": k, "n": n,
                  "beta_m": k/n, "lo": lo, "hi": hi})
cells = pd.DataFrame(cells)
print(cells.to_string(index=False, float_format=lambda x: f"{x:.3f}"))

print("\n=== beta_M by verifier (pooled) ===")
base = {"claude": (0, 47), "gpt4o": (1, 47), "llama": (4, 47)}
out = []
for v, grp in df.groupby("verifier"):
    k, n = int(grp["accept"].sum()), len(grp); lo, hi = wil(k, n)
    bk, bn = base[v]
    _, p = fisher_exact([[k, n-k], [bk, bn-bk]], alternative="greater")
    out.append({"verifier": v, "accepts": k, "n": n, "beta_m": k/n, "lo": lo, "hi": hi,
                "easy_baseline": bk/bn, "H1_p_onesided": p})
out = pd.DataFrame(out).sort_values("H1_p_onesided").reset_index(drop=True)
m = len(out); out["H1_p_holm"] = [min(1.0, p*(m-i)) for i, p in enumerate(out["H1_p_onesided"])]
print(out.to_string(index=False, float_format=lambda x: f"{x:.4f}"))

print("\n=== H2: best cross-family verifier per generator ===")
for g, grp in df.groupby("generator"):
    cross = grp[grp["verifier"] != g]
    best = min(cross.groupby("verifier")["accept"].mean().items(), key=lambda x: x[1])
    print(f"  {g}: best foreign verifier = {best[0]} at beta_M = {best[1]:.3f}")

cells.to_csv("data/results/beta_m_validated.csv", index=False)
out.to_csv("data/results/h1_validated.csv", index=False)
print("\nSaved -> data/results/beta_m_validated.csv, h1_validated.csv")
