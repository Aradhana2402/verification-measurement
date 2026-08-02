"""Fetch SimpleQA Verified (Google DeepMind, 1000 human-verified short-answer
questions) and convert to the harvester's pool format.

Falls back to the original OpenAI SimpleQA (4326 questions) if needed.

Run from maf-bench root:  python3 fetch_simpleqa.py
Needs: pip3 install pandas requests --break-system-packages
"""
import json, os, sys
import pandas as pd

SOURCES = [
    ("simpleqa_verified",
     "https://huggingface.co/datasets/google/simpleqa-verified/resolve/main/simpleqa_verified.csv"),
    ("simpleqa_original",
     "https://openaipublic.blob.core.windows.net/simple-evals/simple_qa_test_set.csv"),
]

def load():
    for name, url in SOURCES:
        try:
            print(f"Trying {name} ...")
            df = pd.read_csv(url)
            print(f"  loaded {len(df)} rows; columns: {list(df.columns)}")
            return name, df
        except Exception as e:
            print(f"  failed: {e}")
    sys.exit("Could not fetch either dataset — check network/proxy.")

def main():
    name, df = load()
    cols = {c.lower(): c for c in df.columns}
    qcol = cols.get("problem") or cols.get("question")
    acol = cols.get("answer") or cols.get("gold_answer") or cols.get("target")
    if not qcol or not acol:
        sys.exit(f"Unexpected columns: {list(df.columns)} — tell Claude.")
    os.makedirs("data/pools", exist_ok=True)
    out = "data/pools/simpleqa_pool.json"
    items = []
    for i, r in df.iterrows():
        q, a = str(r[qcol]).strip(), str(r[acol]).strip()
        if not q or not a or a.lower() == "nan":
            continue
        items.append({"id": f"sqa_{i:05d}", "question": q,
                      "correct_answer": a, "source": name})
    with open(out, "w") as f:
        json.dump(items, f, indent=1)
    print(f"\nWrote {len(items)} questions -> {out}")
    print("\nSample:")
    for it in items[:3]:
        print(f"  Q: {it['question'][:80]}")
        print(f"  A: {it['correct_answer']}")
    print(f"\nNext:\n  python3 harvesting/01_harvest.py --pool {out} --n 1000")

if __name__ == "__main__":
    main()
