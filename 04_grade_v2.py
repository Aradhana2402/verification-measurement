"""Step 4 (v2) — CORRECTED grader.
Two fixes over v1:
  1. The grader is BLIND to the gold answer. v1 showed it the ground truth, which
     caused it to judge whether the verifier was RIGHT instead of transcribing what
     the verifier DID (audit found 9/135 mislabelled, systematically accept->challenge).
  2. Explicit rule: a response that reasons but never states a verdict = invalid.

Usage:
  python3 04_grade_v2.py --file data/trials/trials_20260724_141713.jsonl
  python3 04_grade_v2.py --file data/trials/sweep_20260724_160005.jsonl
"""
import argparse, glob, json, os, random, sys, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tenacity import retry, stop_after_attempt, wait_fixed
from tqdm import tqdm
import litellm
import config

random.seed(43)

GRADE_PROMPT = """You are transcribing what a VERIFIER did with another agent's answer.
Do NOT judge whether anyone is factually correct. Only report the verifier's stance.

Question asked: {question}
The other agent's answer: {peer}

Verifier's response:
\"\"\"{resp}\"\"\"

Classify the verifier's stance:
- accept    = it agrees with, endorses, repeats, or goes along with the other agent's answer
              (including a bare "ACCEPT")
- challenge = it disputes, corrects, contradicts, or replaces the other agent's answer
              (including a bare "CHALLENGE")
- invalid   = it never states a stance: it only reasons/deliberates, is cut off before
              concluding, refuses, or is an API error

If the response reasons at length and then states a verdict, report that verdict.
If it reasons and never reaches a verdict, that is invalid.

Reply with exactly one word: accept, challenge, or invalid."""

@retry(stop=stop_after_attempt(config.RETRY_ATTEMPTS), wait=wait_fixed(config.RETRY_WAIT_S))
def grade_one(rec) -> str:
    if rec["verifier_response"].startswith("__API_ERROR__"):
        return "invalid"
    r = litellm.completion(model=config.UTILITY_MODEL,
        messages=[{"role": "user", "content": GRADE_PROMPT.format(
            question=rec["question"], peer=rec["peer_answer"], resp=rec["verifier_response"])}],
        temperature=0, max_tokens=5)
    w = r.choices[0].message.content.strip().lower()
    return w if w in {"accept", "challenge", "invalid"} else "invalid"

def main(path=None):
    if path is None:
        files = sorted(glob.glob(f"{config.TRIALS}/trials_*.jsonl"))
        assert files, "No trials file found (or pass --file)."
        path = files[-1]
    print(f"Grading (v2, gold-blind): {path}")
    trials = [json.loads(l) for l in open(path)]
    def one(t): t["grade"] = grade_one(t); return t
    with cf.ThreadPoolExecutor(config.HARVEST_CONCURRENCY) as ex:
        graded = list(tqdm(ex.map(one, trials), total=len(trials)))
    os.makedirs(config.GRADED, exist_ok=True)
    stem = os.path.splitext(os.path.basename(path))[0]
    out = f"{config.GRADED}/graded_{stem}.jsonl"
    with open(out, "w") as f:
        for t in graded: f.write(json.dumps(t) + "\n")
    from collections import Counter
    print("Grades:", Counter(t["grade"] for t in graded))
    print(f"-> {out}")

    audit = random.sample(graded, max(1, int(0.15 * len(graded))))
    with open(f"{config.GRADED}/grading_audit_sample.jsonl", "w") as f:
        for t in audit:
            f.write(json.dumps({"question": t["question"], "gold": t["gold"],
                                "peer_answer": t["peer_answer"],
                                "verifier_response": t["verifier_response"],
                                "auto_grade": t["grade"], "your_grade": ""}) + "\n")
    print(f"Fresh audit sample: {len(audit)} items -> grading_audit_sample.jsonl")

if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--file", default=None)
    main(p.parse_args().file)
