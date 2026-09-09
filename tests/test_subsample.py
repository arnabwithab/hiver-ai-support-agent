"""F013: Chase subsample via fixpoint thread collection (stdlib only)."""

import csv

from src import subsample

HEADER = [
    "tweet_id",
    "author_id",
    "inbound",
    "created_at",
    "text",
    "response_tweet_id",
    "in_response_to_tweet_id",
]


def _write_fixture(path):
    rows = [
        # 2-hop chain: u1 -> b1 (Chase) -> u2
        ("u1", "user1", "True", "2020-01-01", "my card never arrived", "b1", ""),
        ("b1", "ChaseSupport", "False", "2020-01-02", "please DM us", "u2", "u1"),
        ("u2", "user1", "True", "2020-01-03", "i sent the DM", "", "b1"),
        # unrelated brand pair: must be ignored
        ("z1", "user9", "True", "2020-01-01", "late flight", "z2", ""),
        ("z2", "AmericanAir", "False", "2020-01-02", "sorry", "", "z1"),
    ]
    with open(path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(HEADER)
        writer.writerows(rows)


def test_fixpoint_collects_two_hop_chain(tmp_path):
    csv_path = str(tmp_path / "twcs.csv")
    _write_fixture(csv_path)
    ids = subsample.collect_chase_ids(csv_path)
    assert {"u1", "b1", "u2"} <= ids
    assert "z1" not in ids and "z2" not in ids


def test_threads_have_turns_only_no_labels(tmp_path):
    csv_path = str(tmp_path / "twcs.csv")
    _write_fixture(csv_path)
    ids = subsample.collect_chase_ids(csv_path)
    threads = subsample.build_threads(csv_path, ids)
    assert len(threads) == 1
    thread = threads[0]
    assert "intent" not in thread
    texts = [t["text"] for t in thread["turns"]]
    assert texts == ["my card never arrived", "please DM us", "i sent the DM"]
    assert [t["inbound"] for t in thread["turns"]] == [True, False, True]
    assert all(
        set(t) == {"tweet_id", "author_id", "inbound", "created_at", "text"}
        for t in thread["turns"]
    )


def test_weak_label_distribution_counts_inbound_only(tmp_path):
    csv_path = str(tmp_path / "twcs.csv")
    _write_fixture(csv_path)
    ids = subsample.collect_chase_ids(csv_path)
    threads = subsample.build_threads(csv_path, ids)
    dist = subsample.weak_label_distribution(threads)
    assert sum(dist.values()) == 2  # two inbound turns only
    assert set(dist) <= set(range(1, 10))


def _write_social_fixture(path):
    rows = [
        ("b1", "Tesco", "False", "2020-01-01", "how can we help", "u1", ""),
        ("u1", "user1", "True", "2020-01-02", "thanks so much, great service", "", "b1"),
        ("b2", "Tesco", "False", "2020-01-01", "how can we help", "u2", ""),
        # thanks + money term: veto-hit, must not pollute 7
        ("u2", "user2", "True", "2020-01-02", "thanks, where is my refund", "", "b2"),
        ("b3", "Tesco", "False", "2020-01-01", "how can we help", "u3", ""),
        ("u3", "user3", "True", "2020-01-02", "good morning", "", "b3"),
        # unattributed inbound (no brand parent): skipped
        ("u9", "user9", "True", "2020-01-02", "thanks anyway", "", "ghost"),
    ]
    with open(path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(HEADER)
        writer.writerows(rows)


def test_mine_social_keeps_clean_thanks_and_greetings(tmp_path):
    csv_path = str(tmp_path / "twcs.csv")
    out_path = str(tmp_path / "social.jsonl")
    _write_social_fixture(csv_path)
    counts = subsample.mine_social(csv_path, out_path, per_class=10, seed=7)
    assert counts == {7: 1, 8: 1}
    import json

    with open(out_path) as fh:
        mined = [json.loads(line) for line in fh if line.strip()]
    assert {r["label"] for r in mined} == {7, 8}
    texts = [r["text"] for r in mined]
    assert "thanks so much, great service" in texts
    assert "good morning" in texts
    assert not any("refund" in t for t in texts)
    assert not any("ghost" in t or "thanks anyway" in t for t in texts)
