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
