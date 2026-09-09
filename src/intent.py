"""F002: intent classifier with calibration. Design §7. No LLM, stdlib + ST.

Frozen sentence embedding (all-MiniLM-L6-v2, never fine-tuned) plus a
hand-rolled softmax-regression head. Swap the model id without touching
the head. Labels are ints 1-9 per src/state.py. train_adapt accepts a
dev-slice path only and refuses anything hold-out/test-flavoured.
"""

import csv
import json
import math
from collections import Counter
from pathlib import Path

from src.eval.metrics import classification_metrics
from src.utils.logger import logger

DIM = 384
N_INTENTS = 9
EPOCHS = 50
LR = 0.1
N_BINS = 10
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
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


_encoder = None


def _model():
    """Frozen sentence encoder, loaded once. Loud failure, never a fallback:
    silently swapping features would invalidate every trained head."""
    global _encoder
    if _encoder is None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise SystemExit(
                "sentence-transformers is required "
                "(https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)"
            )
        _encoder = SentenceTransformer(EMBEDDING_MODEL)
    return _encoder


def embed(text):
    """Frozen sentence embedding (design §7), L2-normalised. Deterministic."""
    return [
        float(v) for v in _model().encode(text, normalize_embeddings=True, show_progress_bar=False)
    ]


def embed_many(texts):
    """Batch encode; one model call for a whole corpus."""
    return [
        [float(v) for v in row]
        for row in _model().encode(list(texts), normalize_embeddings=True, show_progress_bar=False)
    ]


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


def _train_head(rows, epochs=EPOCHS, lr=LR, balanced=True):
    clf = IntentClassifier()
    if balanced:
        # Equal gradient influence per class (N/K·n_c); keeps every row,
        # unlike undersampling. ponytail: no oversampling machinery.
        counts = Counter(label for _, label in rows)
        weights = {label: len(rows) / (len(counts) * n) for label, n in counts.items()}
    else:
        weights = {}
    uniq = list(dict.fromkeys(text for text, _ in rows))
    vecs = dict(zip(uniq, embed_many(uniq)))
    for _ in range(epochs):
        for text, label in rows:
            vec = vecs[text]
            proba = _softmax(
                [
                    sum(w * v for w, v in zip(clf.weights[k], vec)) + clf.bias[k]
                    for k in range(N_INTENTS)
                ]
            )
            step = lr * weights.get(label, 1.0)
            for k in range(N_INTENTS):
                err = proba[k] - (1.0 if label == k + 1 else 0.0)
                wk = clf.weights[k]
                for j in range(DIM):
                    wk[j] -= step * err * vec[j]
                clf.bias[k] -= step * err
    return clf


def _synthetic_rows():
    return [(text, label) for label, texts in _SYNTHETIC.items() for text in texts]


# F013: Banking77 label_text → 9-way map. Intents 7/8 intentionally empty
# (Banking77 has no social intents — reported gap, not a bug); unlisted → 9.
_BANKING77_GROUPS = {
    1: (
        "transaction_charged_twice",
        "extra_charge_on_statement",
        "card_payment_fee_charged",
        "cash_withdrawal_charge",
        "exchange_charge",
        "top_up_by_bank_transfer_charge",
        "top_up_by_card_charge",
        "transfer_fee_charged",
        "card_payment_wrong_exchange_rate",
        "wrong_exchange_rate_for_cash_withdrawal",
        "wrong_amount_of_cash_received",
        "reverted_card_payment?",
    ),
    2: ("request_refund", "Refund_not_showing_up", "top_up_reverted"),
    3: (
        "unable_to_verify_identity",
        "verify_my_identity",
        "verify_source_of_funds",
        "verify_top_up",
        "why_verify_identity",
        "passcode_forgotten",
        "pin_blocked",
        "change_pin",
        "lost_or_stolen_phone",
        "edit_personal_details",
    ),
    4: (
        "card_arrival",
        "card_delivery_estimate",
        "order_physical_card",
        "get_physical_card",
        "getting_spare_card",
        "getting_virtual_card",
        "get_disposable_virtual_card",
    ),
    5: (
        "activate_my_card",
        "apple_pay_or_google_pay",
        "card_linking",
        "disposable_card_limits",
        "top_up_limits",
        "exchange_rate",
        "supported_cards_and_currencies",
        "visa_or_mastercard",
        "fiat_currency_support",
        "country_support",
        "card_acceptance",
        "age_limit",
        "automatic_top_up",
        "exchange_via_app",
        "top_up_by_cash_or_cheque",
        "topping_up_by_card",
        "transfer_into_account",
        "transfer_timing",
        "receiving_money",
    ),
    6: ("terminate_account", "compromised_card", "lost_or_stolen_card"),
}

BANKING77_MAP = {
    label_text: label for label, texts in _BANKING77_GROUPS.items() for label_text in texts
}


def banking77_label(label_text):
    """Banking77 label_text → intent 1-9; unlisted → 9 (other)."""
    return BANKING77_MAP.get(label_text, 9)


def _load_bankings77_csv(path):
    rows = []
    with open(path, newline="") as fh:
        reader = csv.DictReader(fh)
        use_text = reader.fieldnames and "label_text" in reader.fieldnames
        for row in reader:
            if not row.get("text"):
                continue
            if use_text and row.get("label_text"):
                rows.append((row["text"], banking77_label(row["label_text"])))
            elif row.get("label"):
                rows.append((row["text"], int(row["label"])))
    return rows


def train_phase_a(csv_path=None, social_path=None):
    """Phase A: Banking77-format CSV if present else synthetic fixtures.

    social_path appends mined cross-brand social rows (labels 7/8, absent
    from Banking77) — the ceiling is then measured on banking77 test for
    1-6/9 plus probe accuracy for 7/8. Returns (classifier, ceiling metrics
    via metrics.classification_metrics)."""
    if csv_path and Path(csv_path).exists():
        rows = _load_bankings77_csv(csv_path)
    else:
        rows = _synthetic_rows()
    if social_path and Path(social_path).exists():
        with open(social_path) as fh:
            for line in fh:
                line = line.strip()
                if line:
                    row = json.loads(line)
                    rows.append((row["text"], int(row["label"])))
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
    """Thread dicts from the F010 slice (threads.jsonl only): each row carries
    thread_id, intent (gold name), and turns with text/inbound."""
    rows = []
    for path in sorted(Path(dev_dir).glob("*.jsonl")):
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    return rows


def train_adapt(dev_dir):
    """Phase B: weak-supervision adaptation on the adapt-dev slice ONLY.

    Thread label is the gold intent name when present; otherwise one
    weak_label call over the thread's inbound text (same-intent thread
    expansion: every inbound turn trains under the thread label)."""
    _check_dev_path(dev_dir)
    rows = _read_dev_rows(dev_dir)
    if not rows:
        raise ValueError(f"no readable rows in dev slice: {dev_dir}")
    name_to_id = {name: label for label, name in _INTENT_NAMES.items()}
    train_rows = []
    for thread in rows:
        inbound = [t["text"] for t in thread.get("turns", []) if t.get("inbound") and t.get("text")]
        if not inbound:
            continue
        gold = thread.get("intent")
        thread_label = name_to_id.get(gold, weak_label(" ".join(inbound)))
        train_rows.extend((text, thread_label) for text in inbound)
    if not train_rows:
        raise ValueError(f"no inbound turns in dev slice: {dev_dir}")
    clf = _train_head(train_rows)
    texts = [text for text, _ in train_rows]
    labels = [label for _, label in train_rows]
    calibrate(clf, texts, labels)
    clf.threshold = select_threshold(clf, texts, labels)
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


def _mapped_rows(csv_path):
    rows = []
    with open(csv_path) as fh:
        for row in csv.DictReader(fh):
            rows.append((row["text"], BANKING77_MAP.get(row.get("label_text") or "", 9)))
    return rows


if __name__ == "__main__":
    """make train: Phase A on banking77 (+mined social) if present, else synthetic."""
    train_csv = "data/raw/banking77/train.csv"
    train_csv = train_csv if Path(train_csv).exists() else None
    social = "data/raw/mined_social.jsonl"
    social = social if Path(social).exists() else None
    clf, _ = train_phase_a(train_csv, social)
    test_csv = "data/raw/banking77/test.csv"
    if Path(test_csv).exists():
        gold = _mapped_rows(test_csv)
        pred = [clf.predict(text) for text, _ in gold]
        out = classification_metrics([label for _, label in gold], pred)
        out = {"n": out["n"], "accuracy": out["accuracy"], "macro_f1": out["macro_f1"]}
    else:
        out = {"note": "no banking77 test split; trained on synthetic fixtures"}
    out.update({"threshold": clf.threshold, "embedding": EMBEDDING_MODEL})
    print(json.dumps(out, indent=2))
