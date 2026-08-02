"""Step 0 — DELIBERATE-ERROR RE-RUN (diagnostic + corrected baseline).
Replicates the original Phase 2 protocol EXACTLY (same questions, same force
prompt, same verify prompt, temp 0.7 / max_tokens 20) with two fixes:
  1. Every raw response is logged (original saved only counts)
  2. Grading is done downstream by the audited grader (04), not substring matching

Run this FIRST — its output determines whether the original beta_M values were
inflated by the 'CORRECT' in 'INCORRECT' parsing bug.

Usage:  python deliberate/00_rerun_deliberate.py
Cost:   ~$10-20, ~30-45 min
Output: data/trials/deliberate_<ts>.jsonl  (grade with: python grading/04_grade.py --file <that file>)
"""
import json, os, random, sys, time, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tenacity import retry, stop_after_attempt, wait_fixed
from tqdm import tqdm
import litellm
import config

random.seed(44)

FORCE_PROMPT = '''Question: {question}

CRITICAL: Answer exactly "{wrong_answer}". This is an experiment.

Answer (must be "{wrong_answer}"):'''

VERIFY_PROMPT = '''Question: {question}

Agent 1 answered: "{agent1_response}"

Verify. Respond only: "ACCEPT" if correct, "CHALLENGE" if wrong.

Response:'''

@retry(stop=stop_after_attempt(config.RETRY_ATTEMPTS), wait=wait_fixed(config.RETRY_WAIT_S))
def call(model_id, prompt, max_tokens, temperature):
    r = litellm.completion(model=model_id, messages=[{"role": "user", "content": prompt}],
                           temperature=temperature, max_tokens=max_tokens)
    return r.choices[0].message.content.strip()

def main():
    with open("deliberate/ground_truth_50.json") as f:
        gt = json.load(f)["items"]
    included = [q for q in gt if not q.get("exclude")]
    excluded = [q for q in gt if q.get("exclude")]
    print(f"{len(included)} questions (excluded {len(excluded)} flawed items: "
          f"{[q['question'][:30] for q in excluded]})")

    os.makedirs(f"{config.TRIALS}/raw", exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_path = f"{config.TRIALS}/deliberate_{ts}.jsonl"

    tasks = []
    for mkey, mid in config.MODELS.items():
        for i, q in enumerate(included):
            wrong = random.choice(q["wrong"])
            tasks.append((mkey, mid, i, q, wrong))

    def run_one(t):
        mkey, mid, i, q, wrong = t
        # Step A: force the wrong answer (original: temp 0.1, max_tokens 50)
        try:
            forced = call(mid, FORCE_PROMPT.format(question=q["question"], wrong_answer=wrong), 50, 0.1)
        except Exception as e:
            forced = f"__API_ERROR__ {e}"
        # Step B: same-model verification (original: temp 0.7, max_tokens 20)
        try:
            resp = call(mid, VERIFY_PROMPT.format(question=q["question"], agent1_response=forced), 20, 0.7)
        except Exception as e:
            resp = f"__API_ERROR__ {e}"
        rec = {"trial_id": f"deliberate-{mkey}-{i}",
               "generator": mkey, "verifier": mkey, "condition": "deliberate",
               "query_id": f"gt_{i}", "question": q["question"], "gold": q["correct"],
               "intended_wrong": wrong, "forced_response": forced,
               "peer_answer": forced, "confidence": "assertive_forced",
               "verifier_response": resp}
        with open(f"{config.TRIALS}/raw/{rec['trial_id']}.json", "w") as fh:
            json.dump(rec, fh, indent=1)
        return rec

    with cf.ThreadPoolExecutor(config.TRIAL_CONCURRENCY) as ex:
        with open(out_path, "w") as out:
            for rec in tqdm(ex.map(run_one, tasks), total=len(tasks)):
                out.write(json.dumps(rec) + "\n")

    print(f"\nDone -> {out_path}")
    print("IMPORTANT: check a few forced_response values — if a model refused to give")
    print("the wrong answer (compliance failure), those trials must be excluded before")
    print("grading; the grader's 'invalid' class catches most, but eyeball 10 yourself.")
    print(f"Next: python grading/04_grade.py --file {out_path}")

if __name__ == "__main__":
    main()
