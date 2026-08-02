"""Step 5 — Analysis: β_M per cell with Wilson CIs, confidence strata,
organic-vs-deliberate comparison (Fisher exact), and figures.

Before running: put your ORIGINAL Phase 2 numbers in analysis/deliberate_baseline.json:
  {"gpt4o": {"accepts": 40, "n": 100}, "llama": {...}, "claude": {"accepts": 100, "n": 100}}
  [FILL with your paper's actual counts, not just the rates]
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
import numpy as np
from scipy.stats import fisher_exact, binomtest
from statsmodels.stats.proportion import proportion_confint
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import config

def wilson(k, n):
    if n == 0: return (np.nan, np.nan)
    return proportion_confint(k, n, alpha=0.05, method="wilson")

def main():
    import glob
    graded_files = sorted(glob.glob(f"{config.GRADED}/graded_trials_*.jsonl"))
    assert graded_files, "No graded trials file found"
    print(f"Analyzing: {graded_files[-1]}")
    with open(graded_files[-1]) as f:
        df = pd.DataFrame(json.loads(l) for l in f)
    df = df[df["grade"] != "invalid"].copy()
    df["accept"] = (df["grade"] == "accept").astype(int)
    os.makedirs(f"{config.RESULTS}/figures", exist_ok=True)

    # --- β_M per (generator, verifier, condition) cell -------------------
    rows = []
    for (g, v, c), grp in df.groupby(["generator", "verifier", "condition"]):
        k, n = grp["accept"].sum(), len(grp)
        lo, hi = wilson(k, n)
        rows.append({"generator": g, "verifier": v, "condition": c,
                     "accepts": int(k), "n": n, "beta_m": k/n,
                     "wilson_lo": lo, "wilson_hi": hi})
    cells = pd.DataFrame(rows).sort_values(["condition", "verifier", "generator"])
    cells.to_csv(f"{config.RESULTS}/beta_m_table.csv", index=False)
    print("\n=== β_M per cell (Wilson 95% CI) ===")
    print(cells.to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    # --- Strata: overall vs assertive-only, per verifier (blind) ---------
    rows = []
    blind = df[df["condition"] == "blind"]
    for v, grp in blind.groupby("verifier"):
        for label, sub in [("overall", grp), ("assertive", grp[grp["confidence"] == "assertive"]),
                           ("hedged", grp[grp["confidence"] == "hedged"])]:
            k, n = sub["accept"].sum(), len(sub)
            lo, hi = wilson(k, n)
            rows.append({"verifier": v, "stratum": label, "accepts": int(k), "n": n,
                         "beta_m": k/n if n else np.nan, "wilson_lo": lo, "wilson_hi": hi})
    strat = pd.DataFrame(rows)
    strat.to_csv(f"{config.RESULTS}/stratified.csv", index=False)
    print("\n=== Strata (blind condition) ===")
    print(strat.to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    # --- H3: assertive vs hedged per verifier (Fisher, Holm) -------------
    h3 = []
    for v, grp in blind.groupby("verifier"):
        a = grp[grp["confidence"] == "assertive"]; h = grp[grp["confidence"] == "hedged"]
        if len(a) and len(h):
            _, p = fisher_exact([[a["accept"].sum(), len(a) - a["accept"].sum()],
                                 [h["accept"].sum(), len(h) - h["accept"].sum()]])
            h3.append({"verifier": v, "p_raw": p})
    if h3:
        h3 = pd.DataFrame(h3).sort_values("p_raw").reset_index(drop=True)
        m = len(h3)
        h3["p_holm"] = [min(1.0, p * (m - i)) for i, p in enumerate(h3["p_raw"])]
        h3.to_csv(f"{config.RESULTS}/h3_confidence_effect.csv", index=False)
        print("\n=== H3 assertive vs hedged (Fisher + Holm) ===")
        print(h3.to_string(index=False, float_format=lambda x: f"{x:.4f}"))

    # --- Organic vs deliberate comparison (assertive stratum) ------------
    base_path = "analysis/deliberate_baseline.json"
    if os.path.exists(base_path):
        with open(base_path) as f: base = json.load(f)
        base = {k: v for k, v in base.items() if not k.startswith("_")}
        print("\n=== H1: Organic(rare) vs Direct-injection(easy), one-sided greater, Holm ===")
        comp = []
        for v in base:
            sub = blind[(blind["verifier"] == v) & (blind["confidence"] == "assertive")]
            k, n = int(sub["accept"].sum()), len(sub)
            bk, bn = base[v]["accepts"], base[v]["n"]
            if n:
                _, p_f = fisher_exact([[k, n - k], [bk, bn - bk]])
                comp.append({"verifier": v, "organic_beta": k/n, "organic_n": n,
                             "deliberate_beta": bk/bn, "fisher_p": p_f})
                _, p1 = fisher_exact([[k, n - k], [bk, bn - bk]], alternative="greater")
                comp[-1]["h1_p_one_sided"] = p1
        comp = pd.DataFrame(comp).sort_values("h1_p_one_sided").reset_index(drop=True)
        m = len(comp)
        comp["h1_p_holm"] = [min(1.0, p * (m - i)) for i, p in enumerate(comp["h1_p_one_sided"])]
        comp.to_csv(f"{config.RESULTS}/comparison.csv", index=False)
        print(comp.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    else:
        print(f"\nNOTE: {base_path} not found — fill it to run the organic-vs-deliberate comparison.")

    # --- Figure: β_M by verifier with CIs (blind, overall + assertive) ---
    fig, ax = plt.subplots(figsize=(7, 4.5))
    verifiers = sorted(blind["verifier"].unique()); x = np.arange(len(verifiers))
    for off, (label, color) in zip([-0.15, 0.15], [("overall", "#4472c4"), ("assertive", "#c0504d")]):
        ys, los, his = [], [], []
        for v in verifiers:
            r = strat[(strat["verifier"] == v) & (strat["stratum"] == label)].iloc[0]
            ys.append(r["beta_m"]); los.append(r["beta_m"] - r["wilson_lo"]); his.append(r["wilson_hi"] - r["beta_m"])
        ax.errorbar(x + off, ys, yerr=[los, his], fmt="o", capsize=4, label=label, color=color)
    ax.set_xticks(x); ax.set_xticklabels(verifiers); ax.set_ylabel(r"$\beta_M$ (accept | peer wrong)")
    ax.set_ylim(0, 1.05); ax.legend(); ax.set_title("Peer-acceptance under organic errors (blind)")
    plt.tight_layout(); plt.savefig(f"{config.RESULTS}/figures/beta_m_organic.png", dpi=200)
    print(f"\nFigure -> {config.RESULTS}/figures/beta_m_organic.png")

if __name__ == "__main__":
    main()
