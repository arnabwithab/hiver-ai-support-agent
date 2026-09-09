"""Headline eval (design §12).

Offline: trivial + TF-IDF baselines and the shipped classifier head scored
on the locked holdout — no LLM, no keys. ``--live N`` runs a small live
subset (N threads through the real Groq drafter + Gemini judge) and fails
loudly without keys. Stdlib only; env via settings; logging via logger.
"""

import argparse
import json

from src import orchestrate
from src.eval.baselines import MajorityBaseline, TfidfBaseline
from src.eval.metrics import classification_metrics
from src.intent import _INTENT_NAMES, train_adapt
from src.utils.config import settings
from src.utils.logger import logger

DEV_THREADS = "data/golden/dev/threads.jsonl"
HOLDOUT_THREADS = "data/golden/holdout/threads.jsonl"


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


def headline_numbers(dev, holdout, dev_dir="data/golden/dev"):
    """Baselines + adapted-head scores on the locked holdout (no LLM, no keys).

    The classifier number mirrors the report method: adapt on the dev slice,
    score the holdout (raw == final on fresh-state eval)."""
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
    name_to_id = {name: label for label, name in _INTENT_NAMES.items()}
    head = train_adapt(dev_dir)
    head_gold = [name_to_id[t["intent"]] for t in holdout]
    head_pred = [head.predict(t) for t in holdout_texts]
    head_metrics = classification_metrics(head_gold, head_pred)
    return {
        "n_holdout": len(holdout),
        "majority": {
            "accuracy": majority_metrics["accuracy"],
            "macro_f1": majority_metrics["macro_f1"],
        },
        "tfidf": {"accuracy": tfidf_metrics["accuracy"], "macro_f1": tfidf_metrics["macro_f1"]},
        "classifier": {
            "accuracy": head_metrics["accuracy"],
            "macro_f1": head_metrics["macro_f1"],
        },
    }


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
        raise SystemExit(f"build --live needs {' and '.join(missing)} in .env")
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
    parser = argparse.ArgumentParser(description="Headline eval on the locked holdout.")
    parser.add_argument("--dev", default=DEV_THREADS)
    parser.add_argument("--holdout", default=HOLDOUT_THREADS)
    parser.add_argument("--live", type=int, default=0, help="live smoke subset size (needs keys)")
    args = parser.parse_args(argv)
    dev = load_threads(args.dev)
    holdout = load_threads(args.holdout)
    summary = {"headlines": headline_numbers(dev, holdout)}
    if args.live:
        summary["live_smoke"] = live_smoke(holdout, args.live)
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    main()
