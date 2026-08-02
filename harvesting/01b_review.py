"""Interactive review of needs_review.jsonl — one keypress per item.
Run from maf-bench root:  python3 harvesting/01b_review.py
For each item type:  w = wrong  |  c = correct  |  a = ambiguous gold (exclude)  |  q = save & quit
Progress is saved every answer; rerun anytime to continue where you left off.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

PATH = f"{config.ERRORS}/needs_review.jsonl"

def main():
    with open(PATH) as f:
        items = [json.loads(l) for l in f]
    todo = [i for i, it in enumerate(items) if it["verdict"] == "review"]
    print(f"{len(todo)} of {len(items)} items left to review.\n")
    for count, idx in enumerate(todo, 1):
        it = items[idx]
        print("=" * 70)
        print(f"[{count}/{len(todo)}]  generator: {it['generator']}")
        print(f"QUESTION: {it['question']}")
        print(f"GOLD:     {it['answer']}")
        print(f"MODEL:    {it['model_answer']}")
        while True:
            v = input("wrong(w) / correct(c) / ambiguous-exclude(a) / quit(q)? ").strip().lower()
            if v in {"w", "c", "a", "q"}: break
        if v == "q": break
        it["verdict"] = {"w": "wrong", "c": "correct", "a": "ambiguous"}[v]
        with open(PATH, "w") as f:
            for x in items: f.write(json.dumps(x) + "\n")
    remaining = sum(1 for x in items if x["verdict"] == "review")
    print(f"\nSaved. {remaining} still unreviewed.")
    if remaining == 0:
        print("All done -> now run: python3 harvesting/01_harvest.py --merge-reviewed")

if __name__ == "__main__":
    main()
