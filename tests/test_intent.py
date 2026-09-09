"""F002 tests: 9-way shape, hold-out import guard, calibration, threshold.

TDD first: these target src/intent.py (§7, no LLM ever). Phase B runs on
tmp fixture dirs until F010 lands data/golden/dev/.
"""

import json

import pytest

from src import intent


def _thread(thread_id, intent_name, *texts):
    return {
        "thread_id": thread_id,
        "intent": intent_name,
        "turns": [
            {"tweet_id": f"{thread_id}_t{i}", "inbound": True, "text": text}
            for i, text in enumerate(texts)
        ],
    }


def _trained():
    clf, _ = intent.train_phase_a()
    return clf


def test_embed_is_frozen_sentence_vector():
    a = intent.embed("hello there")
    assert len(a) == 384 == intent.DIM
    assert abs(sum(v * v for v in a) - 1.0) < 1e-5
    assert a == intent.embed("hello there")  # deterministic
    assert intent.EMBEDDING_MODEL == "all-MiniLM-L6-v2"


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
    threads = [
        _thread("t1", "refund_request", "where is my refund please", "yes that amount"),
        _thread("t2", "praise_thanks", "thanks so much"),
        _thread("t3", "mystery_intent", "locked out of my account"),  # weak-label fallback
    ]
    with open(dev / "threads.jsonl", "w") as fh:
        for thread in threads:
            fh.write(json.dumps(thread) + "\n")
    clf = intent.train_adapt(str(dev))
    assert clf.predict("where is my refund") in {1, 2, 3, 4, 5, 6, 7, 8, 9}


def test_adapt_reads_real_dev_slice():
    clf = intent.train_adapt("data/golden/dev")
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


# --- F013: Banking77 label_text → 9-way map ---


def test_banking77_map_spot_check():
    spot = {
        "transaction_charged_twice": 1,
        "extra_charge_on_statement": 1,
        "reverted_card_payment?": 1,
        "request_refund": 2,
        "Refund_not_showing_up": 2,
        "top_up_reverted": 2,
        "unable_to_verify_identity": 3,
        "change_pin": 3,
        "card_arrival": 4,
        "order_physical_card": 4,
        "get_disposable_virtual_card": 4,
        "activate_my_card": 5,
        "exchange_rate": 5,
        "receiving_money": 5,
        "terminate_account": 6,
        "compromised_card": 6,
        "lost_or_stolen_card": 6,
    }
    assert len(spot) >= 10
    for label_text, want in spot.items():
        assert intent.banking77_label(label_text) == want, label_text


def test_banking77_map_unlisted_is_other():
    for label_text in (
        "atm_support",
        "balance_not_updated_after_bank_transfer",
        "nope_not_a_label",
    ):
        assert intent.banking77_label(label_text) == 9


def test_banking77_map_leaves_social_empty():
    # Banking77 has no praise/greeting intents: reported gap, not a bug.
    assert set(intent.BANKING77_MAP.values()) <= {1, 2, 3, 4, 5, 6, 9}
    assert 7 not in intent.BANKING77_MAP.values()
    assert 8 not in intent.BANKING77_MAP.values()


def test_load_bankings77_prefers_label_text(tmp_path):
    path = tmp_path / "b77.csv"
    path.write_text(
        "text,label,label_text\n"
        "my card has not arrived,5,card_arrival\n"  # int 5 disagrees: label_text wins → 4
        "thanks a lot,7,activate_my_card\n"  # label_text wins → 5
    )
    assert intent._load_bankings77_csv(str(path)) == [
        ("my card has not arrived", 4),
        ("thanks a lot", 5),
    ]


def test_load_bankings77_falls_back_to_int_label(tmp_path):
    path = tmp_path / "b77.csv"
    path.write_text("text,label\nwhere is my refund,2\nhello there,8\n")
    assert intent._load_bankings77_csv(str(path)) == [
        ("where is my refund", 2),
        ("hello there", 8),
    ]
