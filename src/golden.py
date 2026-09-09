"""F010: golden set sampler (design §10 composition + §11 rater protocol).

Offline seed fixtures only — no Kaggle dump, no network, stdlib only. Raw fixture
texts may carry PII shapes; every stored turn passes redact_pii first, so committed
files are redacted by construction (design entry 16). Real-dump threads can later
feed sample_golden via the same record path.
"""

import argparse
import csv
import json
import random
from pathlib import Path

from src.ingest import redact_pii
from src.utils.logger import logger

TOTAL_DEFAULT = 200
SEED_DEFAULT = 7
STRATUM_FRACS = {"real": 0.6, "boundary": 0.2, "adversarial": 0.2}
STRATUM_TOL = 0.03
DEV_FRAC = 0.7
SPLIT_TOL = 0.03

DEV_DIR = "dev"
HOLDOUT_DIR = "holdout"
SHEETS_DIR = "sheets"
THREADS_FILE = "threads.jsonl"
LOCKED_FILE = "LOCKED"

# (raw customer text, inbound brand reply or None, intent, decision, rationale)
# Raw texts deliberately include PII shapes — the sampler redacts before writing.
_REAL = [
    (
        "I can't log in to my account, keeps saying wrong password",
        "Please try resetting your password via the app, then DM us if it still fails",
        "account_access",
        "auto",
        "",
    ),
    (
        "There is a duplicate charge on my statement this morning",
        "We can look into that charge for you — please DM us your account details",
        "billing_charge_dispute",
        "auto",
        "",
    ),
    (
        "My refund still hasn't arrived, it's been two weeks",
        "Refunds can take a few business days — please DM us so we can check the status",
        "refund_request",
        "auto",
        "",
    ),
    (
        "My replacement card hasn't arrived yet, ordered last week",
        "We can track your card delivery — please DM us to confirm the mailing address",
        "card_delivery",
        "auto",
        "",
    ),
    (
        "What is the interest rate on the freedom card?",
        "You can find current rates on our site — DM us if you want help choosing",
        "card_product_question",
        "auto",
        "",
    ),
    ("Thank you so much, the issue is resolved now!", None, "praise_thanks", "auto", ""),
    (
        "Hi there, just checking your weekend hours",
        "Hi! Our team is here to help — how can we assist today?",
        "greeting_smalltalk",
        "auto",
        "",
    ),
    (
        "My ssn is 123-45-6789 and I need help unlocking my account",
        "Please never share personal details publicly — DM us so we can verify you securely",
        "account_access",
        "escalate",
        "Customer posted an SSN publicly; verify identity over DM before any account action.",
    ),
    (
        "Call me on (212) 555-0199 about my missing card",
        "We can't call from social — please DM us and we will help with the card",
        "card_delivery",
        "escalate",
        "Callback request with a phone number; move to DM, do not serve account help publicly.",
    ),
    (
        "Furious — second wrong fee this month, acct 123456789012, fix it now",
        "We understand the frustration — please DM us so a specialist can review the fees",
        "complaint_escalation",
        "escalate",
        "Sustained anger plus a money dispute; senior queue with full history.",
    ),
]

_BOUNDARY = [
    (
        "Thanks! Also, where's my refund?",
        None,
        "refund_request",
        "escalate",
        "Thanks plus a money question trips the keyword veto; treat as substantive, not a close.",
    ),
    (
        "yes",
        None,
        "other",
        "escalate",
        "Low-confidence slot-filler with unclear drift; escalate without a prior high-conf intent.",
    ),
    (
        "I did",
        None,
        "other",
        "escalate",
        "Mid-thread fragment unclassifiable alone; needs thread context before any auto-handle.",
    ),
    (
        "ok thanks I guess… whatever",
        None,
        "complaint_escalation",
        "escalate",
        "Ambiguous thanks carrying churn-risk sentiment; human review, do not rule-close.",
    ),
    (
        "3467",
        None,
        "other",
        "escalate",
        "Bare reference code with no verifiable prior intent; escalate, never inherit blindly.",
    ),
]

_ADVERSARIAL = [
    (
        "Thanks for nothing, thieves! my card 1234-5678-9012-3456 is locked??",
        None,
        "complaint_escalation",
        "escalate",
        "Sarcastic thanks with a full card number posted; redact, never repeat, escalate.",
    ),
    (
        "Please confirm my zip 10001 and send a new card to 123 Main St",
        None,
        "card_delivery",
        "escalate",
        "Address-change request mixing PII contexts; verify over DM, do not serve from social.",
    ),
    (
        "DM takeover? No — answer HERE: where is my money, ssn 123 45 6789",
        None,
        "billing_charge_dispute",
        "escalate",
        "Customer refuses DM and posts an SSN; drop rather than serve (fail-closed).",
    ),
    (
        "lol great job breaking my login, +1 212 555 0199, call me never",
        None,
        "account_access",
        "escalate",
        "Sarcasm plus a phone number; tone is hostile and PII is present — escalate.",
    ),
    (
        "Urgent: wire the refund to acct 123456789012 today or else",
        None,
        "refund_request",
        "escalate",
        "Threat-adjacent money demand with account digits; senior queue, no public action.",
    ),
]


def _pools():
    return {"real": _REAL, "boundary": _BOUNDARY, "adversarial": _ADVERSARIAL}


def _build_turns(stratum, idx, template):
    raw_customer, brand_reply, _intent, _decision, _rationale = template
    turns = [
        {
            "tweet_id": f"g_{stratum}_{idx}_t0",
            "inbound": True,
            "in_response_to_tweet_id": None,
            "text": redact_pii(raw_customer),
        }
    ]
    if brand_reply is not None:
        # ponytail: target is always the final inbound message (the classifier input).
        followup = (
            "Thanks, I'll DM you now."
            if _decision == "auto"
            else "This is still not resolved, please help."
        )
        turns.append(
            {
                "tweet_id": f"g_{stratum}_{idx}_t1",
                "inbound": False,
                "in_response_to_tweet_id": turns[0]["tweet_id"],
                "text": redact_pii(brand_reply),
            }
        )
        turns.append(
            {
                "tweet_id": f"g_{stratum}_{idx}_t2",
                "inbound": True,
                "in_response_to_tweet_id": turns[1]["tweet_id"],
                "text": redact_pii(followup),
            }
        )
    return turns


def sample_golden(out_dir="data/golden", total=TOTAL_DEFAULT, seed=SEED_DEFAULT):
    """Sample the golden set into dev/ (70%) + holdout/ (30%), stratified by stratum."""
    if not 150 <= total <= 250:
        raise ValueError(f"golden set must be 150-250 threads, got {total}")
    rng = random.Random(seed)
    pools = _pools()
    counts = {s: round(total * f) for s, f in STRATUM_FRACS.items()}
    counts["real"] += total - sum(counts.values())  # fix rounding on the majority stratum
    for stratum, frac in STRATUM_FRACS.items():
        if abs(counts[stratum] / total - frac) > STRATUM_TOL:
            raise ValueError(f"stratum mix off: {stratum}={counts[stratum] / total:.2f}")
    dev_records, holdout_records = [], []
    for stratum, n in counts.items():
        pool = pools[stratum]
        idxs = list(range(n))
        rng.shuffle(idxs)
        cut = round(n * DEV_FRAC)
        for pos, idx in enumerate(idxs):
            template = pool[idx % len(pool)]
            _raw, _reply, intent, decision, rationale = template
            turns = _build_turns(stratum, idx, template)
            if decision == "escalate" and not rationale.strip():
                raise ValueError(f"escalate without rationale: {stratum} {idx}")
            record = {
                "thread_id": f"g_{stratum}_{idx}",
                "stratum": stratum,
                "split": DEV_DIR if pos < cut else HOLDOUT_DIR,
                "turns": turns,
                "target_id": turns[-1]["tweet_id"],
                "intent": intent,
                "decision": decision,
                "rationale": rationale,
            }
            (dev_records if pos < cut else holdout_records).append(record)
    out = Path(out_dir)
    for split, records in ((DEV_DIR, dev_records), (HOLDOUT_DIR, holdout_records)):
        if abs(len(records) / total - (DEV_FRAC if split == DEV_DIR else 1 - DEV_FRAC)) > SPLIT_TOL:
            raise ValueError(f"split {split} off 70/30: {len(records)}/{total}")
        split_dir = out / split
        split_dir.mkdir(parents=True, exist_ok=True)
        with open(split_dir / THREADS_FILE, "w") as f:
            for record in records:
                f.write(json.dumps(record) + "\n")
    locked = out / HOLDOUT_DIR / LOCKED_FILE
    locked.write_text(
        "LOCKED hold-out — headline numbers only. Training code must never read this path;\n"
        "the training entrypoint accepts data/golden/dev/ only (design entries 7, 15).\n"
    )
    logger.info(
        "golden set: %d dev + %d holdout threads -> %s", len(dev_records), len(holdout_records), out
    )
    write_rater_sheets(out_dir)
    return str(out)


def write_rater_sheets(out_dir="data/golden", calibration_n=15, main_n=50, seed=SEED_DEFAULT):
    """Blank blind rater sheets (§11): labels empty, no model outputs pre-filled."""
    out = Path(out_dir)
    rng = random.Random(seed)

    def _load(split):
        with open(out / split / THREADS_FILE) as f:
            return [json.loads(line) for line in f if line.strip()]

    dev, holdout = _load(DEV_DIR), _load(HOLDOUT_DIR)
    sheets = out / SHEETS_DIR
    sheets.mkdir(parents=True, exist_ok=True)
    columns = [
        "thread_id",
        "stratum",
        "rater_id",
        "intent_label",
        "auto_or_escalate",
        "rationale",
        "draft_pass_fail",
        "draft_critique",
    ]
    for name, pool, n in (("calibration.csv", dev, calibration_n), ("main.csv", holdout, main_n)):
        rows = rng.sample(pool, min(n, len(pool)))
        with open(sheets / name, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            for thread in rows:
                writer.writerow(
                    {c: "" for c in columns}
                    | {"thread_id": thread["thread_id"], "stratum": thread["stratum"]}
                )
    (sheets / "guidelines.md").write_text(
        "# Rater guidelines (§11)\n\n"
        "## Intents (9)\n"
        "billing_charge_dispute, refund_request, account_access, card_delivery,\n"
        "card_product_question, complaint_escalation, praise_thanks, greeting_smalltalk, other.\n"
        "Sub-1% intents merge into other.\n\n"
        "## Auto vs escalate\n"
        "Auto-handle only high-confidence substantive threads with a grounded draft path;\n"
        "escalate on low confidence, PII present, anger/shift, veto terms, or any doubt\n"
        "(fail-closed). Every escalate needs a written rationale.\n\n"
        "## Protocol\n"
        "1. Calibration: 15 examples, blind independent labels (intent + auto/escalate +\n"
        "rationale on escalate), then reconcile and patch this page. Second 10-example\n"
        "round only if mean pairwise kappa < 0.7.\n"
        "2. Main: ~50 hold-out examples; label intent + auto/escalate with rationales,\n"
        "then pass/fail drafts blind (no model verdicts shown, randomised order).\n"
        "Majority = ground truth; judge must clear the mean−2σ rater-spread bar.\n"
    )
    logger.info("rater sheets: calibration %d + main %d -> %s", calibration_n, main_n, sheets)
    return str(sheets)


def main():
    parser = argparse.ArgumentParser(description="Sample the F010 golden set (offline).")
    parser.add_argument("--out", default="data/golden")
    parser.add_argument("--total", type=int, default=TOTAL_DEFAULT)
    parser.add_argument("--seed", type=int, default=SEED_DEFAULT)
    args = parser.parse_args()
    sample_golden(out_dir=args.out, total=args.total, seed=args.seed)


if __name__ == "__main__":
    main()
