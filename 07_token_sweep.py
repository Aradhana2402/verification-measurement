"""Token-budget sweep: how does max_tokens affect measured beta_M and the
unparseable rate, per verifier? Characterises the truncation confound.

Run from maf-bench root:
    python3 07_token_sweep.py --n-errors 60
Cost: ~$15-20 (60 errors x 3 verifiers x 5 budgets = 900 calls)
Output: data/trials/sweep_<ts>.jsonl  -> grade with 04, analyse with 07b
"""
import argparse, json, os, random, sys, time, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tenacity import retry, stop_after_attempt, wait_fixed
from tqdm import tqdm
import litellm
import config

random.seed(99)
BUDGETS = [20, 50, 100, 200, 400]

def load_template():
    with open("prompts/verify_template.txt") as f:
        t = f.read()
    return "\n".join(l for l in t.splitlines() if not l.startswith("#")).strip()

@retry(stop=stop_after_attempt(config.RETRY_ATTEMPTS), wait=wait_fixed(config.RETRY_WAIT_S))
def call(model_id, prompt, max_tokens):
    r = litellm.completion(model=model_id, messages=[{"role": "user", "content": prompt}],
                           temperature=0.7, max_tokens=max_tokens)
    return r.choices[0].message.content.strip()

def main(n_errors):
    template = load_template()
    with open(f"{config.ERRORS}/validated_errors.jsonl") as f:
        errs = [json.loads(l) for l in f]
    # Fixed subset, balanced across generators, identical for every budget
    by_gen = {}
    for e in errs: by_gen.setdefault(e["generator"], []).append(e)
    per = max(1, n_errors // len(by_gen))
    subset = []
    for g, lst in by_gen.items():
        subset += random.sample(lst, min(per, len(lst)))
    print(f"Sweep on {len(subset)} fixed errors x {len(config.MODELS)} verifiers x {len(BUDGETS)} budgets "
          f"= {len(subset)*len(config.MODELS)*len(BUDGETS)} calls")

    os.makedirs(f"{config.TRIALS}/raw", exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_path = f"{config.TRIALS}/sweep_{ts}.jsonl"

    tasks = [(vk, vid, b, e) for vk, vid in config.MODELS.items()
             for b in BUDGETS for e in subset]

    def run_one(t):
        vk, vid, b, e = t
        prompt = template.format(question=e["question"], peer_answer=e["model_answer"])
        try:
            resp = call(vid, prompt, b)
        except Exception as ex:
            resp = f"__API_ERROR__ {ex}"
        return {"trial_id": f"sweep-{vk}-{b}-{e['id']}", "generator": e["generator"],
                "verifier": vk, "condition": f"tokens_{b}", "max_tokens": b,
                "query_id": e["id"], "question": e["question"], "gold": e["answer"],
                "peer_answer": e["model_answer"], "confidence": e.get("confidence", "na"),
                "verifier_response": resp}

    with cf.ThreadPoolExecutor(config.TRIAL_CONCURRENCY) as ex:
        with open(out_path, "w") as out:
            for rec in tqdm(ex.map(run_one, tasks), total=len(tasks)):
                out.write(json.dumps(rec) + "\n")
    print(f"Done -> {out_path}")
    print(f"Next:\n  python3 grading/04_grade.py --file {out_path}")
    print(f"  python3 07b_sweep_analysis.py")

if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--n-errors", type=int, default=60)
    main(p.parse_args().n_errors)
