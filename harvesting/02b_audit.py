"""One-keypress audit of the confidence tags. Run from maf-bench root:
    python3 harvesting/02b_audit.py
For each item, judge the CONFIDENCE of the answer's language (ignore correctness):
    1 = assertive (plain fact, no hedging)
    2 = neutral
    3 = hedged ("I think", "possibly", "not sure")
    q = save & quit (resume later)
At the end it prints your agreement score with the auto-tagger.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

PATH = f"{config.ERRORS}/confidence_audit_sample.jsonl"
LAB = {"1": "assertive", "2": "neutral", "3": "hedged"}

def main():
    with open(PATH) as f:
        items = [json.loads(l) for l in f]
    todo = [i for i, it in enumerate(items) if not it.get("your_label")]
    print(f"{len(todo)} of {len(items)} left.\n")
    for count, idx in enumerate(todo, 1):
        it = items[idx]
        print("=" * 70)
        print(f"[{count}/{len(todo)}] ANSWER TEXT:")
        print(it["model_answer"])
        while True:
            v = input("assertive(1) / neutral(2) / hedged(3) / quit(q)? ").strip().lower()
            if v in {"1", "2", "3", "q"}: break
        if v == "q": break
        it["your_label"] = LAB[v]
        with open(PATH, "w") as f:
            for x in items: f.write(json.dumps(x) + "\n")
    done = [x for x in items if x.get("your_label")]
    agree = sum(1 for x in done if x["your_label"] == x["auto_label"])
    print(f"\nAudited {len(done)}/{len(items)} | agreement with auto-tagger: {agree}/{len(done)}")
    if len(done) == len(items):
        print("PASS threshold: >=25/30 agreement." if agree >= 25 else
              "BELOW threshold (<25/30): STOP — bring the disagreements to Claude before trials.")

if __name__ == "__main__":
    main()
