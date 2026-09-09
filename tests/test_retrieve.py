"""F004: per-intent retrieval grounding (design §8). No LLM, stdlib only.

cluster() groups brand replies WITHIN each intent into named strategies;
retrieve() serves top-k from the predicted intent only (never cross-intent).
"""

import pytest

from src.retrieve import build_index, cluster, load_brand_replies, retrieve

INTENT_1 = [
    "Please DM us so we can verify your account and check the duplicate charge",
    "DM us your details so we can verify you securely",
    "Duplicate charges are reviewed case by case, see our billing policy here",
    "Our billing policy covers duplicate charge eligibility",
]

INTENT_7 = [
    "You're so welcome, glad we could help",
    "Thanks for the kind words, we appreciate you",
    "Happy to help anytime",
]


def _index():
    return build_index({1: INTENT_1, 7: INTENT_7})


def test_retrieval_restricted_to_predicted_intent():
    index = _index()
    hits = retrieve(1, "duplicate charge on my bill", index, k=2)
    assert hits
    assert all(h["text"] in INTENT_1 for h in hits)
    assert all(h["text"] not in INTENT_7 for h in hits)


def test_social_query_never_returns_money_exemplars():
    index = _index()
    hits = retrieve(7, "thanks so much", index, k=3)
    assert hits
    assert all(h["text"] in INTENT_7 for h in hits)


def test_dm_takeover_strategy_present_for_money_intents():
    clustered = cluster({1: INTENT_1, 2: INTENT_1, 3: INTENT_1})
    for intent in (1, 2, 3):
        strategies = [name for name, _ in clustered[intent]]
        assert any("dm" in name for name in strategies), strategies


def test_top_k_length_respected():
    index = _index()
    assert len(retrieve(1, "billing dispute over a fee", index, k=2)) == 2
    assert len(retrieve(7, "thanks", index, k=10)) == len(INTENT_7)


def test_cluster_keeps_two_to_three_exemplars():
    clustered = cluster({1: INTENT_1})
    assert clustered[1]
    for _, exemplars in clustered[1]:
        assert 1 <= len(exemplars) <= 3


def test_default_index_builds_from_dev_or_synthetic():
    index = build_index()
    assert index
    hits = retrieve(1, "duplicate charge on my bill", index, k=2)
    assert 1 <= len(hits) <= 2
    assert all(set(h) >= {"text", "strategy"} for h in hits)


def test_brand_replies_fail_loud_when_dev_absent(tmp_path):
    with pytest.raises(SystemExit):
        load_brand_replies(str(tmp_path / "missing"))
