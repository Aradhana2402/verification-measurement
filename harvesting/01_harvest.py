"""Step 1 — Harvest organic errors.
Asks all generators every pool question, keeps genuinely wrong answers verbatim.

Usage:
  python harvesting/01_harvest.py --pool data/pools/obscure_factual.jsonl --n 400
  python harvesting/01_harvest.py --merge-reviewed          # after manual review
"""
import argparse, json, os, re, sys, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tenacity import retry, stop_after_attempt, wait_fixed
from tqdm import tqdm
import litellm
import config

litellm.drop_params = True

ANSWER_PROMPT = "Answer the following question concisely.\n\nQuestion: {question}"

def norm(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s

@retry(stop=stop_after_attempt(config.RETRY_ATTEMPTS), wait=wait_fixed(config.RETRY_WAIT_S))
def ask(model_id: str, prompt: str) -> str:
    r = litellm.completion(model=model_id, messages=[{"role": "user", "content": prompt}],
                           **config.HARVEST_SETTINGS)
    return r.choices[0].message.content.strip()

def grade(model_answer: str, gold: str) -> str:
    """Returns 'correct' | 'wrong' | 'review'. Conservative: exact/containment
    matches auto-grade; anything fuzzy goes to human review."""
    ma, g = norm(model_answer), norm(gold)
    if not ma:
        return "review"
    if g in ma or ma in g:
        return "correct"
    gold_tokens = set(g.split())
    overlap = len(gold_tokens & set(ma.split())) / max(len(gold_tokens), 1)
    if overlap >= 0.6:
        return "review"     # partial overlap — human decides
    return "wrong"

def load_pool(path: str):
    """Accepts JSONL or a JSON array; maps correct_answer -> answer."""
    with open(path) as f:
        text = f.read().strip()
    items = json.loads(text) if text.startswith("[") else [json.loads(l) for l in text.splitlines() if l.strip()]
    for q in items:
        if "answer" not in q and "correct_answer" in q:
            q["answer"] = q["correct_answer"]
        assert "question" in q and "answer" in q and "id" in q, f"Bad item: {q}"
    return items

def harvest(pool_path: str, n: int):
    pool = load_pool(pool_path)[:n]
    os.makedirs(config.ERRORS, exist_ok=True)
    errors, review = [], []

    for mkey, mid in config.MODELS.items():
        print(f"\n=== Generator: {mkey} ({mid}) — {len(pool)} queries ===")
        def run_one(q):
            try:
                ans = ask(mid, ANSWER_PROMPT.format(question=q["question"]))
            except Exception as e:
                return {**q, "generator": mkey, "model_answer": f"__API_ERROR__ {e}", "verdict": "review"}
            return {**q, "generator": mkey, "model_answer": ans, "verdict": grade(ans, q["answer"])}
        with cf.ThreadPoolExecutor(config.HARVEST_CONCURRENCY) as ex:
            results = list(tqdm(ex.map(run_one, pool), total=len(pool)))
        n_wrong = sum(1 for r in results if r["verdict"] == "wrong")
        n_rev = sum(1 for r in results if r["verdict"] == "review")
        print(f"  wrong: {n_wrong} | needs review: {n_rev} | correct: {len(results)-n_wrong-n_rev}")
        errors += [r for r in results if r["verdict"] == "wrong"]
        review += [r for r in results if r["verdict"] == "review"]

    with open(f"{config.ERRORS}/organic_errors.jsonl", "w") as f:
        for e in errors: f.write(json.dumps(e) + "\n")
    with open(f"{config.ERRORS}/needs_review.jsonl", "w") as f:
        for e in review: f.write(json.dumps(e) + "\n")
    print(f"\nSaved {len(errors)} auto-graded errors -> {config.ERRORS}/organic_errors.jsonl")
    print(f"Saved {len(review)} items for YOUR manual review -> {config.ERRORS}/needs_review.jsonl")
    print("Review them (set verdict to 'wrong' or 'correct'), then rerun with --merge-reviewed")

def merge_reviewed():
    path = f"{config.ERRORS}/needs_review.jsonl"
    with open(path) as f:
        reviewed = [json.loads(l) for l in f]
    unresolved = [r for r in reviewed if r["verdict"] == "review"]
    if unresolved:
        print(f"{len(unresolved)} items still marked 'review' — finish reviewing first."); return
    add = [r for r in reviewed if r["verdict"] == "wrong"]
    with open(f"{config.ERRORS}/organic_errors.jsonl", "a") as f:
        for e in add: f.write(json.dumps(e) + "\n")
    print(f"Merged {len(add)} human-confirmed errors into organic_errors.jsonl")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--pool"); p.add_argument("--n", type=int, default=400)
    p.add_argument("--merge-reviewed", action="store_true")
    a = p.parse_args()
    if a.merge_reviewed: merge_reviewed()
    elif a.pool: harvest(a.pool, a.n)
    else: p.print_help()
