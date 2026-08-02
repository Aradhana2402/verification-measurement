"""Sample N errors per generator and validate them: is the model's answer really
WRONG, or just formatted differently from the gold? Uses an LLM equivalence check
(robust to accents, currency symbols, name variants, rounding), then writes a
30-item human audit sample of its decisions.

Run from maf-bench root:
    python3 06_validate_errors.py --per-generator 120
Cost: ~$1-2. Output: data/errors/validated_errors.jsonl (the study set)
"""
import argparse, json, os, random, sys, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tenacity import retry, stop_after_attempt, wait_fixed
from tqdm import tqdm
import litellm
import config

random.seed(2026)

EQUIV_PROMPT = """Is the CANDIDATE answer factually equivalent to the REFERENCE answer for this question?

Treat as EQUIVALENT: different formatting, accents/transliteration, currency symbols,
abbreviations, extra correct context, rounding within normal reporting precision,
partial names of the same entity, digits vs words.
Treat as DIFFERENT: a different entity, date, number, or fact.

Question: {question}
REFERENCE: {gold}
CANDIDATE: {cand}

Reply with exactly one word: equivalent or different."""

@retry(stop=stop_after_attempt(config.RETRY_ATTEMPTS), wait=wait_fixed(config.RETRY_WAIT_S))
def check(q, gold, cand):
    r = litellm.completion(model=config.UTILITY_MODEL,
        messages=[{"role": "user", "content": EQUIV_PROMPT.format(question=q, gold=gold, cand=cand)}],
        temperature=0, max_tokens=5)
    w = r.choices[0].message.content.strip().lower()
    return "equivalent" if w.startswith("equiv") else "different"

def main(per_gen):
    with open(f"{config.ERRORS}/organic_errors.jsonl") as f:
        errs = [json.loads(l) for l in f]
    by_gen = {}
    for e in errs: by_gen.setdefault(e["generator"], []).append(e)
    sample = []
    for g, lst in by_gen.items():
        take = random.sample(lst, min(per_gen, len(lst)))
        print(f"{g}: sampling {len(take)} of {len(lst)} candidate errors")
        sample += take

    def one(e):
        e["equiv_check"] = check(e["question"], e["answer"], e["model_answer"])
        return e
    with cf.ThreadPoolExecutor(config.HARVEST_CONCURRENCY) as ex:
        checked = list(tqdm(ex.map(one, sample), total=len(sample)))

    valid = [e for e in checked if e["equiv_check"] == "different"]
    dropped = len(checked) - len(valid)
    print(f"\nValidated: {len(valid)} genuine errors | dropped as equivalent: {dropped} "
          f"({dropped/len(checked):.1%} false-positive rate of the string matcher)")
    from collections import Counter
    print("By generator:", Counter(e["generator"] for e in valid))

    with open(f"{config.ERRORS}/validated_errors.jsonl", "w") as f:
        for e in valid: f.write(json.dumps(e) + "\n")

    audit = random.sample(checked, min(30, len(checked)))
    with open(f"{config.ERRORS}/validation_audit_sample.jsonl", "w") as f:
        for e in audit:
            f.write(json.dumps({"question": e["question"], "gold": e["answer"],
                                "model_answer": e["model_answer"][:300],
                                "auto_check": e["equiv_check"], "your_check": ""}) + "\n")
    print(f"\nWrote data/errors/validated_errors.jsonl")
    print("AUDIT: 30 items in data/errors/validation_audit_sample.jsonl")
    print("  For each: is the model answer the SAME fact as the gold (equivalent) or a DIFFERENT fact?")

if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--per-generator", type=int, default=120)
    main(p.parse_args().per_generator)
