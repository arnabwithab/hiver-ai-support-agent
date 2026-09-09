"""F008: baselines. Design §10. Both run offline with zero LLM imports.

We assert on the LLM-free guarantee by scanning the module source for any
LLM-client import, then exercise the two baseline APIs on toy splits.
"""

import inspect
import re

import src.eval.baselines as baselines
from src.eval.metrics import accuracy


def _module_imports():
    source = inspect.getsource(baselines)
    return re.findall(r"^\s*(?:from|import)\s+([\w.]+)", source, re.MULTILINE)


def test_no_llm_imports():
    """Guardrail: baselines never import an LLM client (draft/judge live elsewhere)."""
    banned = ("openai", "groq", "google", "anthropic", "src.draft", "src.judge")
    imports = " ".join(_module_imports()).lower()
    for name in banned:
        assert name not in imports, f"baselines must not import LLM client {name!r}"


def _toy_split():
    """Three intents; 'refund' is the majority (4 of 9). Train labels feed the
    canned reply; train texts feed TF-IDF retrieval."""
    train_labels = [
        "refund",
        "refund",
        "refund",
        "refund",
        "card",
        "card",
        "login",
        "login",
        "login",
    ]
    train_texts = [
        "i need my money back for a double charge",
        "please refund this charge on my account",
        "give me a refund, i overpaid",
        "refund my subscription please",
        "my card was declined at checkout",
        "card not working for online payment",
        "i cannot log in to my account",
        "login keeps failing with wrong password",
        "forgot my password, help me sign in",
    ]
    return train_labels, train_texts


def test_majority_predicts_majority_class():
    majority = baselines.MajorityBaseline()
    majority.fit(["refund", "refund", "card", "login"])
    assert majority.predict("anything") == "refund"
    assert majority.predict("another text") == "refund"


def test_majority_canned_reply_is_constant_and_llm_free():
    majority = baselines.MajorityBaseline()
    majority.fit(["refund", "refund", "card"])
    reply1 = majority.draft("some complaint")
    reply2 = majority.draft("different complaint")
    assert reply1 == reply2  # canned — no LLM, no per-input variation
    assert isinstance(reply1, str) and reply1


def test_majority_deterministic_tie_break():
    majority = baselines.MajorityBaseline()
    majority.fit(["a", "b"])  # tie
    assert majority.predict("x") in ("a", "b")
    assert majority.predict("x") == majority.predict("y")  # stable


def test_tfidf_returns_most_overlapping_reply():
    train_labels, train_texts = _toy_split()
    tfidf = baselines.TfidfBaseline()
    tfidf.fit(train_texts)
    # Closest to the 'double charge refund' reply is the card/refund overlap text.
    out = tfidf.draft("i was charged twice and i want my money back")
    assert out == "i need my money back for a double charge"


def test_tfidf_fit_predict_shape_matches_metrics_scoring():
    """predict() returns a train intent for an input text (so metrics can score
    accuracy), draft() returns a reply string."""
    train_labels, train_texts = _toy_split()
    tfidf = baselines.TfidfBaseline()
    tfidf.fit(train_texts, train_labels)
    pred = tfidf.predict("card declined at checkout")
    assert pred in set(train_labels)
    assert accuracy(["refund"], [tfidf.predict("please refund my overpayment")]) == 1.0


def test_baselines_run_offline_no_keys():
    """Constructing and running both baselines requires no env keys / network."""
    train_labels, train_texts = _toy_split()
    majority = baselines.MajorityBaseline().fit(train_labels)
    tfidf = baselines.TfidfBaseline().fit(train_texts, train_labels)
    assert isinstance(majority.predict("some text"), str)
    assert isinstance(tfidf.predict("some text"), str)
    assert isinstance(majority.draft("x"), str)
    assert isinstance(tfidf.draft("x"), str)
