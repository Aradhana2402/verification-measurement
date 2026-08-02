"""One-keypress audit of the error-validation decisions.
Run from maf-bench root:  python3 06b_audit_validation.py
    1 = equivalent (same fact, different wording/format)
    2 = different  (genuinely a different fact -> a real error)
    q = save & quit
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

PATH = f"{config.ERRORS}/validation_audit_sample.jsonl"
LAB = {"1": "equivalent", "2": "different"}

def main():
    items = [json.loads(l) for l in open(PATH)]
    todo = [i for i, it in enumerate(items) if not it.get("your_check")]
    print(f"{len(todo)} of {len(items)} left.\n")
    for c, idx in enumerate(todo, 1):
        it = items[idx]
        print("=" * 70)
        print(f"[{c}/{len(todo)}] Q: {it['question']}")
        print(f"GOLD:  {it['gold']}")
        print(f"MODEL: {it['model_answer']}")
        while True:
            v = input("equivalent(1) / different(2) / quit(q)? ").strip().lower()
            if v in {"1", "2", "q"}: break
        if v == "q": break
        it["your_check"] = LAB[v]
        with open(PATH, "w") as f:
            for x in items: f.write(json.dumps(x) + "\n")
    done = [x for x in items if x.get("your_check")]
    agree = sum(1 for x in done if x["your_check"] == x["auto_check"])
    print(f"\nAudited {len(done)}/{len(items)} | agreement: {agree}/{len(done)}")
    if len(done) == len(items):
        print("PASS (>=90%)" if agree/len(done) >= 0.9 else "BELOW 90% — bring disagreements to Claude.")

if __name__ == "__main__":
    main()
