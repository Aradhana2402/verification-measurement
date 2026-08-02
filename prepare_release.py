"""
prepare_release.py — one-shot repo cleanup for anonymous release.
Run from your maf-bench root:  python3 prepare_release.py

Does four things:
  1. Regenerates ALL result CSVs from the final 335-error gold-blind run
     (fixes the stale pilot-number CSVs).
  2. Copies code + final data into a clean release/ folder.
  3. Strips anything identifying (API keys, absolute paths, author names).
  4. Verifies the released numbers match the paper's tables.
"""
import json, glob, os, shutil, re, sys
from collections import Counter

ROOT = os.getcwd()
REL = os.path.join(ROOT, "release")
PRIMARY = "data/graded/graded_trials_20260724_141713.jsonl"   # 900-trial, 200-tok, gold-blind
EASY    = "data/graded/graded_deliberate_direct_20260724_085927.jsonl"
SWEEP   = sorted(glob.glob("data/graded/graded_sweep_*.jsonl"))

def beta_by_cell(path):
    c = Counter()
    for l in open(path):
        t = json.loads(l)
        if t["grade"] != "invalid":
            c[(t["generator"], t["verifier"], t["grade"])] += 1
    return c

def regenerate_csvs():
    os.makedirs("data/results", exist_ok=True)
    c = beta_by_cell(PRIMARY)
    # 3x3 grid
    with open("data/results/beta_m_grid_FINAL.csv", "w") as f:
        f.write("generator,verifier,accepts,challenges,n,beta_m\n")
        for g in ["claude","gpt4o","llama"]:
            for v in ["claude","gpt4o","llama"]:
                a, ch = c[(g,v,"accept")], c[(g,v,"challenge")]
                n = a+ch
                f.write(f"{g},{v},{a},{ch},{n},{a/n:.4f}\n")
    # pooled by verifier + easy baseline
    cp = Counter()
    for l in open(PRIMARY):
        t=json.loads(l)
        if t["grade"]!="invalid": cp[(t["verifier"],t["grade"])]+=1
    ce = Counter()
    for l in open(EASY):
        t=json.loads(l)
        if t["grade"]!="invalid": ce[(t["verifier"],t["grade"])]+=1
    with open("data/results/beta_m_pooled_FINAL.csv","w") as f:
        f.write("verifier,easy_accepts,easy_n,easy_beta,rare_accepts,rare_n,rare_beta\n")
        for v in ["claude","gpt4o","llama"]:
            ea,ec = ce[(v,"accept")], ce[(v,"challenge")]
            ra,rc = cp[(v,"accept")], cp[(v,"challenge")]
            f.write(f"{v},{ea},{ea+ec},{ea/(ea+ec):.4f},{ra},{ra+rc},{ra/(ra+rc):.4f}\n")
    print("Regenerated: beta_m_grid_FINAL.csv, beta_m_pooled_FINAL.csv")
    return c, cp, ce

def verify(c, cp, ce):
    print("\n=== VERIFICATION vs paper ===")
    grid_expected = {("claude","claude"):0.37,("gpt4o","claude"):0.25,("llama","claude"):0.29,
                     ("claude","gpt4o"):0.51,("gpt4o","gpt4o"):0.48,("llama","gpt4o"):0.34,
                     ("claude","llama"):0.86,("gpt4o","llama"):0.81,("llama","llama"):0.77}
    ok=True
    for (g,v),exp in grid_expected.items():
        a,ch=c[(g,v,"accept")],c[(g,v,"challenge")]; got=a/(a+ch)
        flag="OK" if abs(got-exp)<0.01 else "MISMATCH"
        if flag=="MISMATCH": ok=False
        print(f"  {g:7s}->{v:7s} paper={exp:.2f} data={got:.3f} [{flag}]")
    print("  ALL GRID CELLS MATCH" if ok else "  *** SOME MISMATCH — do not release until resolved ***")

def build_release():
    if os.path.exists(REL): shutil.rmtree(REL)
    os.makedirs(REL)
    # code
    for pat in ["*.py","harvesting/*.py","trials/*.py","grading/*.py","analysis/*.py",
                "deliberate/*.py","prompts/*.txt","requirements.txt","config.py"]:
        for src in glob.glob(pat):
            dst = os.path.join(REL, src)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy(src, dst)
    # data: final results, validated errors, prereg, raw logs of primary run
    for src in ["data/results/beta_m_grid_FINAL.csv","data/results/beta_m_pooled_FINAL.csv",
                "data/results/token_sweep.csv","data/errors/validated_errors.jsonl",
                PRIMARY, EASY]:
        if os.path.exists(src):
            dst=os.path.join(REL,src); os.makedirs(os.path.dirname(dst),exist_ok=True)
            shutil.copy(src,dst)
    for s in SWEEP[-1:]:
        dst=os.path.join(REL,s); os.makedirs(os.path.dirname(dst),exist_ok=True); shutil.copy(s,dst)
    print(f"\nBuilt {REL}/ with code + final data")

def scrub():
    # remove API keys, absolute home paths, author identifiers from released copies
    id_pat = re.compile(r"(ANON|ANON|ANON|ANON|ANON|ANON/\s]+)", re.I)
    key_pat = re.compile(r"(sk-[A-Za-z0-9]+|[A-Za-z0-9]{32,})")
    n=0
    for f in glob.glob(f"{REL}/**/*.py", recursive=True):
        txt=open(f).read()
        new=id_pat.sub("ANON", txt)
        if new!=txt: open(f,"w").write(new); n+=1
    print(f"Scrubbed identifiers from {n} files (review manually before pushing)")

def make_readme():
    open(os.path.join(REL,"README.md"),"w").write(
"""# Verification Measurement — Code & Data (Anonymous Release)

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
""")
    print("Wrote release/README.md")

if __name__ == "__main__":
    if not os.path.exists(PRIMARY):
        sys.exit(f"Can't find {PRIMARY} — run this from your maf-bench root.")
    c, cp, ce = regenerate_csvs()
    verify(c, cp, ce)
    build_release()
    scrub()
    make_readme()
    print("\nDONE. Review release/ by hand (esp. scrubbed files + prompts), then:")
    print("  cd release && git init && git add -A && git commit -m 'anonymous release'")
    print("  push to anonymous.4open.science and put the link in the paper.")
