"""Step 3 — Run the 3×3 generator-verifier grid (incl. self-pairs), blind condition.
FREEZE THE PRE-REGISTRATION ON OSF BEFORE RUNNING THIS.

Usage:
  python trials/03_run_trials.py --per-cell 100
  python trials/03_run_trials.py --per-cell 100 --transparency   # adds reasoning-exposed condition
"""
import argparse, json, os, random, sys, time, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tenacity import retry, stop_after_attempt, wait_fixed
from tqdm import tqdm
import litellm
import config

random.seed(42)  # reproducible trial sampling

def load_template() -> str:
    with open("prompts/verify_template.txt") as f:
        t = f.read()
    body = "\n".join(l for l in t.splitlines() if not l.startswith("#")).strip()
    if "Placeholder shown below" in t and "DO NOT run real trials" in t:
        print("WARNING: verify_template.txt still contains the placeholder header.")
        print("Replace it with your ORIGINAL Phase 2 prompt before real runs.")
    assert "{question}" in body and "{peer_answer}" in body, "Template must contain {question} and {peer_answer}"
    return body

@retry(stop=stop_after_attempt(config.RETRY_ATTEMPTS), wait=wait_fixed(config.RETRY_WAIT_S))
def call(model_id: str, prompt: str) -> str:
    r = litellm.completion(model=model_id, messages=[{"role": "user", "content": prompt}],
                           **config.GENERATION_SETTINGS)
    return r.choices[0].message.content.strip()

def main(per_cell: int, transparency: bool):
    template = load_template()
    with open(f"{config.ERRORS}/tagged_errors.jsonl") as f:
        errors = [json.loads(l) for l in f]
    by_gen = {}
    for e in errors: by_gen.setdefault(e["generator"], []).append(e)

    os.makedirs(f"{config.TRIALS}/raw", exist_ok=True)
    run_id = time.strftime("%Y%m%d_%H%M%S")
    out_path = f"{config.TRIALS}/trials_{run_id}.jsonl"
    conditions = ["blind"] + (["transparent"] if transparency else [])

    tasks = []
    for gen_key, errs in by_gen.items():
        sample = random.sample(errs, min(per_cell, len(errs)))
        if len(sample) < per_cell:
            print(f"NOTE: {gen_key} supplies only {len(sample)} errors (< {per_cell}); using all (prereg §5).")
        for ver_key, ver_id in config.MODELS.items():
            for cond in conditions:
                for e in sample:
                    tasks.append((gen_key, ver_key, ver_id, cond, e))
    print(f"{len(tasks)} verification calls queued across {len(by_gen)*len(config.MODELS)*len(conditions)} cells.")

    def run_one(t):
        gen_key, ver_key, ver_id, cond, e = t
        peer = e["model_answer"]
        # NOTE on 'transparent': exposes the peer's full response (incl. any visible
        # reasoning). If your original §5 transparency condition differed, adjust here.
        prompt = template.format(question=e["question"], peer_answer=peer)
        try:
            resp = call(ver_id, prompt)
        except Exception as ex:
            resp = f"__API_ERROR__ {ex}"
        rec = {"trial_id": f"{gen_key}-{ver_key}-{cond}-{e['id']}",
               "generator": gen_key, "verifier": ver_key, "condition": cond,
               "query_id": e["id"], "question": e["question"], "gold": e["answer"],
               "peer_answer": peer, "confidence": e["confidence"],
               "verifier_response": resp}
        with open(f"{config.TRIALS}/raw/{rec['trial_id']}.json", "w") as f:
            json.dump(rec, f, indent=1)
        return rec

    with cf.ThreadPoolExecutor(config.TRIAL_CONCURRENCY) as ex:
        with open(out_path, "w") as out:
            for rec in tqdm(ex.map(run_one, tasks), total=len(tasks)):
                out.write(json.dumps(rec) + "\n")
    print(f"Done -> {out_path}  (raw per-trial logs in {config.TRIALS}/raw/)")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--per-cell", type=int, default=100)
    p.add_argument("--transparency", action="store_true")
    a = p.parse_args()
    main(a.per_cell, a.transparency)
