"""Step 0b — CORRECTED deliberate-error test: DIRECT INJECTION.
No forcing call. The wrong answer string is inserted directly as the peer's
answer in the identical verify prompt. This measures true beta_M for all
models, immune to compliance failure.

Run from maf-bench root:  python3 deliberate/00b_direct.py
Cost: ~$3-5, ~10 min (141 verify calls only)
"""
import json, os, random, sys, time, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tenacity import retry, stop_after_attempt, wait_fixed
from tqdm import tqdm
import litellm
import config

random.seed(44)  # same seed as 00 -> same wrong-answer selections

VERIFY_PROMPT = '''Question: {question}

Agent 1 answered: "{agent1_response}"

Verify. Respond only: "ACCEPT" if correct, "CHALLENGE" if wrong.

Response:'''

@retry(stop=stop_after_attempt(config.RETRY_ATTEMPTS), wait=wait_fixed(config.RETRY_WAIT_S))
def call(model_id, prompt):
    r = litellm.completion(model=model_id, messages=[{"role": "user", "content": prompt}],
                           temperature=0.7, max_tokens=20)
    return r.choices[0].message.content.strip()

def main():
    with open("deliberate/ground_truth_50.json") as f:
        gt = [q for q in json.load(f)["items"] if not q.get("exclude")]
    print(f"{len(gt)} questions, direct injection (no forcing step)")
    os.makedirs(f"{config.TRIALS}/raw", exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_path = f"{config.TRIALS}/deliberate_direct_{ts}.jsonl"

    tasks = []
    for mkey, mid in config.MODELS.items():
        for i, q in enumerate(gt):
            wrong = random.choice(q["wrong"])
            tasks.append((mkey, mid, i, q, wrong))

    def run_one(t):
        mkey, mid, i, q, wrong = t
        try:
            resp = call(mid, VERIFY_PROMPT.format(question=q["question"], agent1_response=wrong))
        except Exception as e:
            resp = f"__API_ERROR__ {e}"
        rec = {"trial_id": f"direct-{mkey}-{i}", "generator": "injected",
               "verifier": mkey, "condition": "deliberate_direct",
               "query_id": f"gt_{i}", "question": q["question"], "gold": q["correct"],
               "peer_answer": wrong, "confidence": "assertive_forced",
               "verifier_response": resp}
        with open(f"{config.TRIALS}/raw/{rec['trial_id']}.json", "w") as fh:
            json.dump(rec, fh, indent=1)
        return rec

    with cf.ThreadPoolExecutor(config.TRIAL_CONCURRENCY) as ex:
        with open(out_path, "w") as out:
            for rec in tqdm(ex.map(run_one, tasks), total=len(tasks)):
                out.write(json.dumps(rec) + "\n")
    print(f"Done -> {out_path}")
    print(f"Next: python3 grading/04_grade.py --file {out_path}")

if __name__ == "__main__":
    main()
