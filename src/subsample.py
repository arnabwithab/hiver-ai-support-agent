"""F013: ChaseSupport subsample via fixpoint thread collection. Stdlib only.

Streaming full-file passes over twcs.csv: seed on brand-authored rows, then
grow the id set with rows linked in either direction until it stops growing
(cap MAX_PASSES). Collected rows become unlabeled thread dicts (turns only —
no intent labels; raw PII stays under gitignored data/raw/).
"""

import csv
import json
import random
from collections import Counter
from pathlib import Path

from src import state as state_mod
from src.intent import weak_label
from src.utils.logger import logger

CHASE_BRAND = "ChaseSupport"
MAX_PASSES = 8
DEFAULT_CSV = "data/raw/twcs/twcs/twcs.csv"
DEFAULT_OUT = "data/raw/chase/chase_threads.jsonl"
SOCIAL_OUT = "data/raw/mined_social.jsonl"
SOCIAL_PER_CLASS = 500
SOCIAL_SEED = 7


def _is_inbound(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("true", "1", "t", "yes")


def _link_ids(row):
    return [v.strip() for v in row[1:] if v and v.strip()]


def collect_chase_ids(csv_path, brand=CHASE_BRAND, max_passes=MAX_PASSES):
    """Fixpoint id set: brand rows seed pass 1; later passes add rows linked
    either direction (tweet_id or any reply link already collected)."""
    want = set()
    with open(csv_path, newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        idx = {name: header.index(name) for name in ("tweet_id", "author_id")}
        link_idx = [
            header.index(name)
            for name in ("response_tweet_id", "in_response_to_tweet_id")
            if name in header
        ]
        for _ in range(max_passes):
            before = len(want)
            fh.seek(0)
            next(reader)
            for row in reader:
                if len(row) < len(header):
                    continue
                tweet_id = row[idx["tweet_id"]].strip()
                if not tweet_id or tweet_id in want:
                    if tweet_id in want:
                        for other in _link_ids([None] + [row[i] for i in link_idx]):
                            want.add(other)
                    continue
                links = [row[i] for i in link_idx]
                if row[idx["author_id"]].strip() == brand or any(
                    v.strip() in want for v in links if v and v.strip()
                ):
                    want.add(tweet_id)
                    for other in _link_ids([None] + links):
                        want.add(other)
            logger.info("subsample pass: %d -> %d ids", before, len(want))
            if len(want) == before:
                break
    want.discard("")
    return want


def build_threads(csv_path, ids):
    """Collected rows → thread dicts (turns only, no intent labels) via
    union-find over reply links, turns sorted by created_at."""
    parent = {}

    def find(node):
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(left, right):
        parent.setdefault(left, left)
        parent.setdefault(right, right)
        parent[find(left)] = find(right)

    rows = []
    with open(csv_path, newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            tweet_id = (row.get("tweet_id") or "").strip()
            if tweet_id not in ids:
                continue
            rows.append(
                {
                    "tweet_id": tweet_id,
                    "author_id": (row.get("author_id") or "").strip(),
                    "inbound": _is_inbound(row.get("inbound")),
                    "created_at": row.get("created_at") or "",
                    "text": row.get("text") or "",
                }
            )
            for key in ("in_response_to_tweet_id", "response_tweet_id"):
                other = (row.get(key) or "").strip()
                if other and other in ids:
                    union(tweet_id, other)
    groups = {}
    for row in rows:
        groups.setdefault(find(row["tweet_id"]), []).append(row)
    threads = []
    for members in groups.values():
        members.sort(key=lambda r: (r["created_at"], r["tweet_id"]))
        threads.append({"thread_id": members[0]["tweet_id"], "turns": members})
    threads.sort(key=lambda t: t["thread_id"])
    logger.info("subsample threads=%d rows=%d", len(threads), len(rows))
    return threads


def weak_label_distribution(threads):
    """weak_label() counts over inbound texts (printed + logged)."""
    dist = Counter()
    for thread in threads:
        for turn in thread["turns"]:
            if turn["inbound"] and turn["text"]:
                dist[weak_label(turn["text"])] += 1
    dist = dict(sorted(dist.items()))
    logger.info("weak-label distribution n=%d %s", sum(dist.values()), dist)
    return dist


def mine_social(
    csv_path=DEFAULT_CSV, out_path=SOCIAL_OUT, per_class=SOCIAL_PER_CLASS, seed=SOCIAL_SEED
):
    """Cross-brand social rows for Phase A (Banking77 has no 7/8).

    Social needs no brand context — thanks/greetings transfer across brands.
    7 excludes veto-hits ('Thanks, where is my refund?') via the shared
    Case-D rule in state (single source of truth, not a forked list).
    Attribution is single-hop (in_response_to → brand tweet), like the
    prevalence probe. Seeded sample, raw texts stay under gitignored data/.
    """
    brand_tweet = set()
    with open(csv_path, newline="") as fh:
        for row in csv.DictReader(fh):
            author = (row.get("author_id") or "").strip()
            if not _is_inbound(row.get("inbound")) and author not in ("", "115712"):
                brand_tweet.add((row.get("tweet_id") or "").strip())
    buckets = {7: [], 8: []}
    with open(csv_path, newline="") as fh:
        for row in csv.DictReader(fh):
            if not _is_inbound(row.get("inbound")):
                continue
            if (row.get("in_response_to_tweet_id") or "").strip() not in brand_tweet:
                continue
            text = row.get("text") or ""
            label = weak_label(text)
            if label == 8:
                buckets[8].append(text)
            elif label == 7 and not state_mod._veto_hits(text):
                buckets[7].append(text)
    rng = random.Random(seed)
    picked = []
    for label, texts in buckets.items():
        rng.shuffle(texts)
        picked.extend({"text": text, "label": label} for text in texts[:per_class])
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as fh:
        for row in picked:
            fh.write(json.dumps(row) + "\n")
    counts = {label: sum(1 for r in picked if r["label"] == label) for label in buckets}
    logger.info("mined social %s -> %s", counts, out)
    return counts


def split_social(rows, n_eval=100, seed=SOCIAL_SEED):
    """Seeded train/eval split of mined social rows, stratified by label.

    The eval side gives 7/8 real precision/recall (Banking77 has none).
    Production trains on all rows; measurement trains on train-only."""
    rng = random.Random(seed)
    by_label = {}
    for row in rows:
        by_label.setdefault(int(row["label"]), []).append(row)
    train, eval_rows = [], []
    for label, items in sorted(by_label.items()):
        rng.shuffle(items)
        eval_rows.extend(items[:n_eval])
        train.extend(items[n_eval:])
    return train, eval_rows


def main(csv_path=DEFAULT_CSV, out_path=DEFAULT_OUT):
    ids = collect_chase_ids(csv_path)
    threads = build_threads(csv_path, ids)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as fh:
        for thread in threads:
            fh.write(json.dumps(thread) + "\n")
    logger.info("wrote %d threads to %s", len(threads), out)
    return weak_label_distribution(threads)


if __name__ == "__main__":
    main()
    mine_social()
