"""F002 tests: 9-way shape, hold-out import guard, calibration, threshold.

TDD first: these target src/intent.py (§7, no LLM ever). Phase B runs on
tmp fixture dirs until F010 lands data/golden/dev/.
"""

import csv

import pytest

from src import intent


def _trained():
    clf, _ = intent.train_phase_a()
    return clf


def test_predict_labels_are_ints_1_to_9():
    clf = _trained()
    for text in ["where is my refund", "thanks so much", "hello", "locked out"]:
        assert clf.predict(text) in {1, 2, 3, 4, 5, 6, 7, 8, 9}


def test_predict_proba_nine_way_shape():
    clf = _trained()
    proba = clf.predict_proba("where is my refund")
    assert len(proba) == 9
    assert abs(sum(proba) - 1.0) < 1e-6
    assert all(0.0 <= p <= 1.0 for p in proba)


def test_training_refuses_holdout_paths():
    for bad in (
        "data/golden/holdout",
        "data/golden/hold-out",
        "data/golden/hold_out",
        "data/test",
    ):
        with pytest.raises(ValueError):
            intent.train_adapt(bad)


def test_phase_a_ceiling_beats_chance():
    _, metrics = intent.train_phase_a()
    assert metrics["accuracy"] > 1 / 9
    assert set(metrics["labels"]) <= {1, 2, 3, 4, 5, 6, 7, 8, 9}


def test_adapt_trains_on_dev_dir_only(tmp_path):
    dev = tmp_path / "dev"
    dev.mkdir()
    with open(dev / "messages.csv", "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["text", "thread_id"])
        writer.writerow(["where is my refund please", "t1"])
        writer.writerow(["yes that amount", "t1"])
        writer.writerow(["thanks so much", "t2"])
        writer.writerow(["locked out of my account", "t3"])
    clf = intent.train_adapt(str(dev))
    assert clf.predict("where is my refund") in {1, 2, 3, 4, 5, 6, 7, 8, 9}


def test_calibration_runs_and_returns_bins():
    clf = _trained()
    texts = ["where is my refund", "thanks so much", "hello there", "locked out"] * 5
    labels = [2, 7, 8, 3] * 5
    before = intent.expected_calibration_error(clf, texts, labels)
    intent.calibrate(clf, texts, labels)
    assert clf.temperature > 0
    bins, after = intent.reliability(clf, texts, labels)
    assert len(bins) == 10
    assert all(set(b) == {"bin", "n", "accuracy", "avg_conf"} for b in bins)
    assert after <= before + 0.05


def test_threshold_selection_in_unit_interval():
    clf = _trained()
    texts = ["where is my refund", "thanks so much", "hello there", "locked out"] * 5
    labels = [2, 7, 8, 3] * 5
    threshold = intent.select_threshold(clf, texts, labels)
    assert isinstance(threshold, float)
    assert 0.0 < threshold < 1.0


def test_calibrated_confidence_matches_top_proba():
    clf = _trained()
    assert clf.calibrated_confidence("hello") == pytest.approx(max(clf.predict_proba("hello")))


def test_intent_names_cover_all_nine():
    assert [intent.intent_name(i) for i in range(1, 10)] == [
        "billing_charge_dispute",
        "refund_request",
        "account_access",
        "card_delivery",
        "card_product_question",
        "complaint_escalation",
        "praise_thanks",
        "greeting_smalltalk",
        "other",
    ]
