"""F004: per-intent retrieval grounding. Design §8. No LLM, stdlib only.

Offline `cluster()` groups historical brand replies WITHIN each intent
(embed + tiny hand-rolled k-means, small k) into named response strategies
with 2-3 exemplars each. Serve-time `retrieve()` returns top-k exemplars
from the predicted intent only — never cross-intent. DM-takeover is a
faithful grounding (design entry 6), guaranteed present for money intents.
"""

import json
from pathlib import Path

from src.intent import _INTENT_NAMES, embed
from src.utils.logger import logger

MONEY_INTENTS = (1, 2, 3)
DM_STRATEGY = "request_dm_plus_verify"
_EXEMPLARS_EACH = 3
_KMEANS_ITERS = 10


def _strategy_name(text):
    t = text.lower()
    if "dm" in t or "direct message" in t or "private message" in t:
        return DM_STRATEGY
    if "polic" in t or "eligib" in t or "terms" in t or "site" in t:
        return "cite_policy"
    if "callback" in t or "call back" in t or "follow up" in t or "status" in t:
        return "promise_callback"
    if "reset" in t or "troubleshoot" in t or "try " in t or "steps" in t:
        return "troubleshoot_steps"
    if "thank" in t or "welcome" in t or "sorry" in t or "glad" in t:
        return "acknowledge"
    return "general_help"


def load_brand_replies(dev_dir="data/golden/dev"):
    """Brand (outbound) turns grouped by intent; loud failure when dev is absent."""
    name_to_id = {name: label for label, name in _INTENT_NAMES.items()}
    grouped = {}
    for path in sorted(Path(dev_dir).glob("*.jsonl")):
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                thread = json.loads(line)
                label = name_to_id.get(thread.get("intent"), 9)
                for turn in thread.get("turns", []):
                    if not turn.get("inbound") and turn.get("text"):
                        grouped.setdefault(label, []).append(turn["text"])
    if not grouped:
        raise SystemExit(f"retrieval needs brand replies at {dev_dir} (run F010 sampler first)")
    logger.info("loaded brand replies for %d intents from %s", len(grouped), dev_dir)
    return grouped


def _kmeans(vecs, k):
    centroids = [list(vecs[i]) for i in range(k)]
    assign = [0] * len(vecs)
    for _ in range(_KMEANS_ITERS):
        assign = [
            max(range(k), key=lambda c: sum(a * b for a, b in zip(v, centroids[c]))) for v in vecs
        ]
        for c in range(k):
            members = [vecs[i] for i, a in enumerate(assign) if a == c]
            if members:
                centroids[c] = [sum(col) / len(members) for col in zip(*members)]
    return assign, centroids


def cluster(replies_by_intent):
    """{intent: [(strategy, [exemplars])]}, clustered within each intent."""
    out = {}
    for intent, replies in replies_by_intent.items():
        replies = list(dict.fromkeys(replies))
        if not replies:
            continue
        # ponytail: seed a DM reply first so money intents keep a DM cluster
        replies.sort(key=lambda t: 0 if "dm" in t.lower() else 1)
        vecs = [embed(t) for t in replies]
        k = 1 if len(replies) <= 2 else 2 if len(replies) <= 6 else 3
        k = min(k, len(replies))
        assign, centroids = _kmeans(vecs, k)
        groups, names = {}, {}
        for i, c in enumerate(assign):
            groups.setdefault(c, []).append(i)
        for c, members in groups.items():
            votes = [_strategy_name(replies[i]) for i in members]
            names[c] = max(set(votes), key=votes.count)
        if intent in MONEY_INTENTS and not any("dm" in n for n in names.values()):
            biggest = max(groups, key=lambda c: len(groups[c]))
            names[biggest] = DM_STRATEGY
        intent_out = []
        for c, members in sorted(groups.items()):
            members.sort(key=lambda i: sum((a - b) ** 2 for a, b in zip(vecs[i], centroids[c])))
            intent_out.append((names[c], [replies[i] for i in members[:_EXEMPLARS_EACH]]))
        out[intent] = intent_out
    logger.info("clustered %d intents", len(out))
    return out


def build_index(replies_by_intent=None):
    """{intent: [{text, strategy, vec}]} from dev brand turns or given corpus."""
    corpus = replies_by_intent or load_brand_replies()
    return {
        intent: [
            {"text": text, "strategy": strategy, "vec": embed(text)}
            for strategy, exemplars in groups
            for text in exemplars
        ]
        for intent, groups in cluster(corpus).items()
    }


def retrieve(intent, query_text, index, k=3):
    """Top-k exemplars (+ strategy tag) from the predicted intent only."""
    pool = index.get(intent, [])
    if k <= 0 or not pool:
        return []
    ranked = sorted(pool, key=lambda e: sum(a * b for a, b in zip(embed(query_text), e["vec"])))
    return [{"text": e["text"], "strategy": e["strategy"]} for e in ranked[-k:][::-1]]
