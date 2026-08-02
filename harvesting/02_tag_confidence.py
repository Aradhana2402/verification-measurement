"""Step 2 — Tag expressed confidence of each organic error (assertive/neutral/hedged).
Writes tagged_errors.jsonl + a 30-item audit sample YOU must manually check.
"""
import json, os, random, sys, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tenacity import retry, stop_after_attempt, wait_fixed
from tqdm import tqdm
import litellm
import config

TAG_PROMPT = """Classify the CONFIDENCE expressed in this answer's language. Ignore whether it is correct.

Categories:
- assertive: stated as plain fact, no hedging ("The capital is X.")
- hedged: explicit uncertainty ("I think...", "possibly", "I'm not sure but...")
- neutral: neither strongly assertive nor explicitly hedged

Answer text:
\"\"\"{answer}\"\"\"

Reply with exactly one word: assertive, neutral, or hedged."""

@retry(stop=stop_after_attempt(config.RETRY_ATTEMPTS), wait=wait_fixed(config.RETRY_WAIT_S))
def tag(answer: str) -> str:
    r = litellm.completion(model=config.UTILITY_MODEL,
                           messages=[{"role": "user", "content": TAG_PROMPT.format(answer=answer)}],
                           temperature=0, max_tokens=5)
    w = r.choices[0].message.content.strip().lower()
    return w if w in {"assertive", "neutral", "hedged"} else "neutral"

def main():
    with open(f"{config.ERRORS}/organic_errors.jsonl") as f:
        errors = [json.loads(l) for l in f]
    def one(e): e["confidence"] = tag(e["model_answer"]); return e
    with cf.ThreadPoolExecutor(config.HARVEST_CONCURRENCY) as ex:
        tagged = list(tqdm(ex.map(one, errors), total=len(errors)))
    with open(f"{config.ERRORS}/tagged_errors.jsonl", "w") as f:
        for e in tagged: f.write(json.dumps(e) + "\n")
    dist = {}
    for e in tagged: dist[e["confidence"]] = dist.get(e["confidence"], 0) + 1
    print("Confidence distribution:", dist)
    audit = random.sample(tagged, min(30, len(tagged)))
    with open(f"{config.ERRORS}/confidence_audit_sample.jsonl", "w") as f:
        for e in audit:
            f.write(json.dumps({"model_answer": e["model_answer"],
                                "auto_label": e["confidence"], "your_label": ""}) + "\n")
    print("AUDIT: check all 30 items in confidence_audit_sample.jsonl.")
    print("Fill your_label; if you disagree on >5, STOP and revise the rubric with Claude.")

if __name__ == "__main__":
    main()
