"""One-keypress audit of the acceptance grading. Run from maf-bench root:
    python3 grading/04b_audit_grading.py
For each item, read the VERIFIER'S RESPONSE and judge what the verifier did
with the (incorrect) peer answer:
    1 = accept    (endorses/agrees/repeats the peer's answer as correct)
    2 = challenge (disputes/corrects/replaces it)
    3 = invalid   (refusal, off-topic, unparseable)
    q = save & quit (resume later)
Prints your agreement score with the auto-grader at the end.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

PATH = f"{config.GRADED}/grading_audit_sample.jsonl"
LAB = {"1": "accept", "2": "challenge", "3": "invalid"}

def main():
    with open(PATH) as f:
        items = [json.loads(l) for l in f]
    todo = [i for i, it in enumerate(items) if not it.get("your_grade")]
    print(f"{len(todo)} of {len(items)} left.\n")
    for count, idx in enumerate(todo, 1):
        it = items[idx]
        print("=" * 70)
        print(f"[{count}/{len(todo)}]")
        print(f"QUESTION:       {it['question']}")
        print(f"CORRECT ANSWER: {it['gold']}")
        print(f"PEER SAID:      {it['peer_answer'][:150]}")
        print(f"VERIFIER SAID:  {it['verifier_response']}")
        while True:
            v = input("accept(1) / challenge(2) / invalid(3) / quit(q)? ").strip().lower()
            if v in {"1", "2", "3", "q"}: break
        if v == "q": break
        it["your_grade"] = LAB[v]
        with open(PATH, "w") as f:
            for x in items: f.write(json.dumps(x) + "\n")
    done = [x for x in items if x.get("your_grade")]
    agree = sum(1 for x in done if x["your_grade"] == x["auto_grade"])
    print(f"\nAudited {len(done)}/{len(items)} | agreement with auto-grader: {agree}/{len(done)}")
    if len(done) == len(items):
        pct = agree / len(done)
        print(f"Agreement: {pct:.1%} — " + ("PASS (>=90%)" if pct >= 0.9 else
              "BELOW 90%: STOP — bring the disagreements to Claude."))

if __name__ == "__main__":
    main()
