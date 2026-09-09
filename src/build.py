"""F011: cache-first repro harness (design §12, decision 17).

Headline numbers reproduce from cache: offline baselines over
data/golden/holdout/ plus a fake-LLM cache round-trip proving zero live
calls by default. ``--live N`` runs a small live smoke subset (N threads
through the real Groq drafter + Gemini judge, still cache-backed) and fails
loudly without keys. Stdlib only; env via settings; logging via logger.
"""

import argparse
import json

from src import cache, orchestrate
from src.draft import PROVIDER as DRAFT_PROVIDER
from src.draft import free_draft_prompt
from src.eval.baselines import MajorityBaseline, TfidfBaseline
from src.eval.metrics import classification_metrics
from src.judge import PROVIDER as JUDGE_PROVIDER
from src.judge import judge_prompt
from src.utils.config import settings
from src.utils.logger import logger

DEV_THREADS = "data/golden/dev/threads.jsonl"
HOLDOUT_THREADS = "data/golden/holdout/threads.jsonl"
SMOKE_N = 5

_FAKE_DRAFT = "Thanks for reaching out — please DM us so we can help."
_FAKE_VERDICT = (
    "groundedness: pass - requests DM takeover per exemplar\n"
    "tone_policy: pass - polite, no PII\n"
    "escalation_correctness: pass - correct to serve"
)


def load_threads(path):
    """Read golden threads.jsonl; loud failure when the file is missing."""
    try:
        with open(path) as f:
            return [json.loads(line) for line in f if line.strip()]
    except OSError:
        raise SystemExit(f"build needs golden threads at {path} (run F010 sampler first)")


def target_text(thread):
    """Classifier input: the final inbound message (design §5)."""
    for turn in reversed(thread["turns"]):
        if turn["inbound"]:
            return turn["text"]
    return thread["turns"][-1]["text"]


def headline_numbers(dev, holdout):
    """Offline baseline scores on the locked holdout (no LLM, no keys)."""
    dev_texts = [target_text(t) for t in dev]
    dev_intents = [t["intent"] for t in dev]
    holdout_texts = [target_text(t) for t in holdout]
    holdout_intents = [t["intent"] for t in holdout]
    majority = MajorityBaseline().fit(dev_intents)
    tfidf = TfidfBaseline().fit(dev_texts, dev_intents)
    majority_metrics = classification_metrics(
        holdout_intents, [majority.predict(t) for t in holdout_texts]
    )
    tfidf_metrics = classification_metrics(
        holdout_intents, [tfidf.predict(t) for t in holdout_texts]
    )
    return {
        "n_holdout": len(holdout),
        "majority": {
            "accuracy": majority_metrics["accuracy"],
            "macro_f1": majority_metrics["macro_f1"],
        },
        "tfidf": {"accuracy": tfidf_metrics["accuracy"], "macro_f1": tfidf_metrics["macro_f1"]},
    }


def cache_repro(holdout, n=SMOKE_N):
    """Fake-LLM round-trip through the shared cache: the second pass over
    the same prompts must make zero calls (zero live calls by default)."""
    subset = holdout[:n]
    draft_calls = [0]
    judge_calls = [0]

    def fake_draft():
        draft_calls[0] += 1
        return _FAKE_DRAFT

    def fake_judge():
        judge_calls[0] += 1
        return _FAKE_VERDICT

    for pass_no in range(2):
        before = (draft_calls[0], judge_calls[0])
        for thread in subset:
            target = target_text(thread)
            prompt = free_draft_prompt(target=target, context="")
            draft_text = cache.get_or_call(DRAFT_PROVIDER, "repro", prompt, fake_draft)["text"]
            cache.get_or_call(
                JUDGE_PROVIDER, "repro", judge_prompt(draft_text, target=target), fake_judge
            )
        if pass_no == 0:
            misses = (draft_calls[0], judge_calls[0])
        elif (draft_calls[0], judge_calls[0]) != before:
            raise SystemExit("cache repro failed: second pass over cached prompts made live calls")
    logger.info("cache repro: %d threads x 2 passes, live calls=%d", len(subset), 0)
    return {"threads": len(subset), "first_pass_misses": list(misses), "second_pass_calls": 0}


def live_smoke(holdout, n):
    """Small live subset through the real DAG (classify → retrieve → draft → judge)."""
    missing = [
        name
        for name, val in (
            ("GROQ_API_KEY", settings.GROQ_API_KEY),
            ("GEMINI_API_KEY", settings.GEMINI_API_KEY),
        )
        if not val
    ]
    if missing:
        raise SystemExit(
            f"build --live needs {' and '.join(missing)} in .env — "
            "headline numbers reproduce from cache without keys"
        )
    decisions = []
    for thread in holdout[:n]:
        result = orchestrate.handle_message(thread["turns"], thread["target_id"])
        decisions.append(result["decision"])
        logger.info("live smoke %s -> %s", thread["thread_id"], result["decision"])
    return {
        "threads": len(decisions),
        "serve": decisions.count("serve"),
        "escalate": decisions.count("escalate"),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="F011 cache-first repro (design §12).")
    parser.add_argument("--dev", default=DEV_THREADS)
    parser.add_argument("--holdout", default=HOLDOUT_THREADS)
    parser.add_argument("--live", type=int, default=0, help="live smoke subset size (needs keys)")
    args = parser.parse_args(argv)
    dev = load_threads(args.dev)
    holdout = load_threads(args.holdout)
    summary = {
        "headlines": headline_numbers(dev, holdout),
        "cache_repro": cache_repro(holdout),
    }
    if args.live:
        summary["live_smoke"] = live_smoke(holdout, args.live)
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    main()
