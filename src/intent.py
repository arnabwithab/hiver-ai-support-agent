"""F002: intent classifier with calibration. Design §7. No LLM, stdlib only.

Frozen embedding is a portable stand-in: hashing char-trigram encoder
(md5 → fixed dim, L2-normalised). Swap for a sentence-embedding model
without touching the head. Linear head is hand-rolled softmax regression.

Labels are ints 1-9 per src/state.py. train_adapt accepts a dev-slice
path only and refuses anything hold-out/test-flavoured.
"""

import csv
import hashlib
import json
import math
from pathlib import Path

from src.eval.metrics import classification_metrics
from src.utils.logger import logger

DIM = 128
N_INTENTS = 9
EPOCHS = 50
LR = 0.1
N_BINS = 10
_TEMPS = (0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0)

KEYWORD_SEEDS = {
    1: ("charge", "charged", "billing", "bill", "dispute", "duplicate", "fee"),
    2: ("refund", "reimburse", "money back"),
    3: ("login", "log in", "password", "locked", "access", "username", "verify"),
    4: ("card", "delivery", "deliver", "arrived", "shipping", "replacement", "mail"),
    5: ("apr", "interest", "rate", "rewards", "limit", "offer", "eligible", "policy"),
    6: ("complaint", "awful", "terrible", "angry", "sue", "worst", "escalate"),
    7: ("thank", "thanks", "great service", "appreciated"),
    8: ("hello", "hi ", "hey", "good morning", "good afternoon"),
    9: (),
}

_SYNTHETIC = {
    1: ["duplicate charge on my bill", "billing dispute over a fee", "charged twice this month"],
    2: ["where is my refund", "request a refund please", "money back for that fee"],
    3: ["locked out of my account", "cannot login to my account", "reset my password"],
    4: ["my replacement card hasn't arrived", "card delivery is late", "rush my new card"],
    5: ["what is the interest rate", "are these rewards eligible", "what is my limit"],
    6: ["this is terrible service", "awful experience, escalate this", "worst support ever"],
    7: ["thanks so much", "thank you, great service", "much appreciated"],
    8: ["hello there", "hi, good morning", "hey, how are you"],
    9: ["not sure what happened", "please advise on next steps", "following up here"],
}


def embed(text):
    """Hashing char-trigram embedding, L2-normalised. Deterministic."""
    vec = [0.0] * DIM
    text = f" {text.lower()} "
    for i in range(max(len(text) - 2, 1)):
        gram = text[i : i + 3]
        vec[int(hashlib.md5(gram.encode()).hexdigest(), 16) % DIM] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _softmax(logits, temperature=1.0):
    scaled = [v / temperature for v in logits]
    top = max(scaled)
    exps = [math.exp(v - top) for v in scaled]
    total = sum(exps)
    return [v / total for v in exps]


class IntentClassifier:
    """Frozen-embed + linear head. temperature: Platt-style scaling fit on adapt-dev."""

    def __init__(self):
        self.weights = [[0.0] * DIM for _ in range(N_INTENTS)]
        self.bias = [0.0] * N_INTENTS
        self.temperature = 1.0
        self.threshold = 0.5

    def _logits(self, text):
        vec = embed(text)
        return [
            sum(w * v for w, v in zip(self.weights[k], vec)) + self.bias[k]
            for k in range(N_INTENTS)
        ]

    def predict_proba(self, text):
        return _softmax(self._logits(text), self.temperature)

    def predict(self, text):
        proba = self.predict_proba(text)
        return proba.index(max(proba)) + 1

    def calibrated_confidence(self, text):
        return max(self.predict_proba(text))


def _train_head(rows, epochs=EPOCHS, lr=LR):
    clf = IntentClassifier()
    for _ in range(epochs):
        for text, label in rows:
            vec = embed(text)
            proba = _softmax(clf._logits(text))
            for k in range(N_INTENTS):
                err = proba[k] - (1.0 if label == k + 1 else 0.0)
                wk = clf.weights[k]
                for j in range(DIM):
                    wk[j] -= lr * err * vec[j]
                clf.bias[k] -= lr * err
    return clf


def _synthetic_rows():
    return [(text, label) for label, texts in _SYNTHETIC.items() for text in texts]


def _load_bankings77_csv(path):
    rows = []
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            if row.get("text") and row.get("label"):
                rows.append((row["text"], int(row["label"])))
    return rows


def train_phase_a(csv_path=None):
    """Phase A: Banking77-format CSV if present else synthetic fixtures.

    Returns (classifier, ceiling metrics via metrics.classification_metrics)."""
    if csv_path and Path(csv_path).exists():
        rows = _load_bankings77_csv(csv_path)
    else:
        rows = _synthetic_rows()
    clf = _train_head(rows)
    pred = [clf.predict(text) for text, _ in rows]
    metrics = classification_metrics([label for _, label in rows], pred)
    logger.info("phase-a ceiling accuracy=%.3f n=%d", metrics["accuracy"], len(rows))
    return clf, metrics


def weak_label(text):
    """Best keyword-seed hit; 9 (other) when nothing fires."""
    scored = [
        (sum(1 for kw in kws if kw in text.lower()), label)
        for label, kws in KEYWORD_SEEDS.items()
        if kws
    ]
    hits, label = max(scored)
    return label if hits else 9


def _check_dev_path(dev_dir):
    parts = {p.lower() for p in Path(dev_dir).parts}
    blob = str(dev_dir).lower()
    if "holdout" in blob or "hold-out" in blob or "hold_out" in blob:
        raise ValueError(f"refusing hold-out path: {dev_dir}")
    if parts & {"test", "tests"}:
        raise ValueError(f"refusing test path: {dev_dir}")


def _read_dev_rows(dev_dir):
    """Tolerant reader for the F010 slice (csv/json/jsonl: text + optional
    thread_id/label). Falls back to weak labels when gold labels are absent."""
    rows = []
    for path in sorted(Path(dev_dir).glob("*")):
        if path.suffix == ".csv":
            with open(path, newline="") as fh:
                for row in csv.DictReader(fh):
                    if row.get("text"):
                        rows.append(dict(row))
        elif path.suffix in (".json", ".jsonl"):
            with open(path) as fh:
                content = fh.read().strip()
            blobs = content.splitlines() if path.suffix == ".jsonl" else [content]
            for blob in blobs:
                data = json.loads(blob)
                items = data if isinstance(data, list) else [data]
                rows.extend(r for r in items if isinstance(r, dict) and r.get("text"))
    return rows


def _label_key(row):
    for key in ("label", "intent", "gold_label"):
        if row.get(key) not in (None, ""):
            return int(row[key])
    return None


def train_adapt(dev_dir):
    """Phase B: weak-supervision adaptation on the adapt-dev slice ONLY."""
    _check_dev_path(dev_dir)
    rows = _read_dev_rows(dev_dir)
    if not rows:
        raise ValueError(f"no readable rows in dev slice: {dev_dir}")
    by_thread = {}
    for row in rows:
        by_thread.setdefault(row.get("thread_id") or id(row), []).append(row)
    train_rows, gold_texts, gold_labels = [], [], []
    for messages in by_thread.values():
        scored = [
            (sum(1 for kw in KEYWORD_SEEDS[label] if kw in m["text"].lower()), label, m)
            for m in messages
            for label in KEYWORD_SEEDS
            if KEYWORD_SEEDS[label]
        ]
        _, thread_label, _ = max(scored) if scored else (0, 9, None)
        if not any(s > 0 for s, _, _ in scored):
            thread_label = 9
        for m in messages:
            train_rows.append((m["text"], thread_label))
            gold = _label_key(m)
            gold_texts.append(m["text"])
            gold_labels.append(gold if gold is not None else thread_label)
    clf = _train_head(train_rows)
    calibrate(clf, gold_texts, gold_labels)
    clf.threshold = select_threshold(clf, gold_texts, gold_labels)
    logger.info("adapted n=%d threshold=%.3f", len(train_rows), clf.threshold)
    return clf


def _nll(clf, texts, labels, temperature):
    total = 0.0
    for text, label in zip(texts, labels):
        proba = _softmax(clf._logits(text), temperature)
        total -= math.log(max(proba[label - 1], 1e-12))
    return total / max(len(texts), 1)


def calibrate(clf, texts, labels):
    """Temperature scaling: grid-search NLL on adapt-dev (grid holds 1.0, so
    NLL never worsens). Returns the fitted temperature."""
    clf.temperature = min(_TEMPS, key=lambda t: _nll(clf, texts, labels, t))
    return clf.temperature


def reliability(clf, texts, labels, n_bins=N_BINS):
    """Reliability bins + ECE over calibrated confidences."""
    bins = [{"bin": i, "n": 0, "accuracy": 0.0, "avg_conf": 0.0} for i in range(n_bins)]
    for text, label in zip(texts, labels):
        proba = clf.predict_proba(text)
        conf = max(proba)
        b = bins[min(int(conf * n_bins), n_bins - 1)]
        b["n"] += 1
        b["accuracy"] += 1.0 if proba.index(conf) + 1 == label else 0.0
        b["avg_conf"] += conf
    for b in bins:
        if b["n"]:
            b["accuracy"] /= b["n"]
            b["avg_conf"] /= b["n"]
    ece = sum(b["n"] * abs(b["accuracy"] - b["avg_conf"]) for b in bins) / max(len(texts), 1)
    return bins, ece


def expected_calibration_error(clf, texts, labels, n_bins=N_BINS):
    return reliability(clf, texts, labels, n_bins)[1]


def select_threshold(clf, texts, labels, target_precision=0.85):
    """Threshold T from the adapt-dev precision-coverage curve: lowest
    confidence cut hitting target precision (else the max-precision cut)."""
    scored = sorted(
        (
            (clf.calibrated_confidence(t), clf.predict(t) == label)
            for t, label in zip(texts, labels)
        ),
        reverse=True,
    )
    cands, best_prec, fallback = [], -1.0, scored[-1][0]
    for cut, _ in scored:
        window = [hit for c, hit in scored if c >= cut]
        prec = sum(window) / len(window)
        if prec >= target_precision:
            cands.append(cut)
        if prec >= best_prec:  # tie favours the smaller cut = larger coverage
            best_prec, fallback = prec, cut
    return float(min(max(min(cands) if cands else fallback, 1e-6), 1 - 1e-6))


_INTENT_NAMES = {
    1: "billing_charge_dispute",
    2: "refund_request",
    3: "account_access",
    4: "card_delivery",
    5: "card_product_question",
    6: "complaint_escalation",
    7: "praise_thanks",
    8: "greeting_smalltalk",
    9: "other",
}


def intent_name(label):
    return _INTENT_NAMES[label]
