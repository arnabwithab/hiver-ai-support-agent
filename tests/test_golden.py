"""F010: golden set build (design §10 composition + §11 rater protocol).

Sampler runs offline on seed fixtures (no Kaggle dump, no network). Tests run the
sampler into tmp_path so they never touch committed data; one scan test also sweeps
the committed data/golden tree when present.
"""

import csv
import json
import re
import tempfile
from pathlib import Path

import pytest

from src.golden import (
    DEV_DIR,
    HOLDOUT_DIR,
    SHEETS_DIR,
    STRATUM_FRACS,
    write_rater_sheets,
)

# Independent PII patterns (not imported from src.ingest — the test must catch a
# broken redactor, not mirror it).
_ACCOUNT_RUN = re.compile(r"\d{8,}")
_SSN = re.compile(r"\d{3}[- ]\d{2}[- ]\d{4}")
_PHONE = re.compile(r"\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}")
_PII_PATTERNS = (_ACCOUNT_RUN, _SSN, _PHONE)


def _sample(tmp_path):
    from src.golden import sample_golden

    return sample_golden(out_dir=tmp_path, total=200, seed=7)


def _read_threads(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def _scan_pii(obj):
    if isinstance(obj, str):
        return any(p.search(obj) for p in _PII_PATTERNS)
    if isinstance(obj, dict):
        return any(_scan_pii(v) for v in obj.values())
    if isinstance(obj, list):
        return any(_scan_pii(v) for v in obj)
    return False


def test_stratum_mix_enforced():
    from src.golden import sample_golden

    with tempfile.TemporaryDirectory() as tmp:
        sample_golden(out_dir=tmp, total=200, seed=7)
        threads = _read_threads(Path(tmp) / "dev" / "threads.jsonl") + _read_threads(
            Path(tmp) / "holdout" / "threads.jsonl"
        )
    assert 150 <= len(threads) <= 250
    for stratum, frac in STRATUM_FRACS.items():
        got = sum(1 for t in threads if t["stratum"] == stratum) / len(threads)
        assert abs(got - frac) <= 0.03, f"{stratum}: {got:.2f} vs {frac:.2f}"


def test_split_counts_70_30(tmp_path):
    _sample(tmp_path)
    dev = _read_threads(tmp_path / "dev" / "threads.jsonl")
    holdout = _read_threads(tmp_path / "holdout" / "threads.jsonl")
    total = len(dev) + len(holdout)
    assert abs(len(dev) / total - 0.7) <= 0.03
    assert abs(len(holdout) / total - 0.3) <= 0.03
    assert {t["thread_id"] for t in dev}.isdisjoint({t["thread_id"] for t in holdout})


def test_dev_holdout_paths_distinct_and_locked(tmp_path):
    assert DEV_DIR != HOLDOUT_DIR
    out = _sample(tmp_path)
    assert (Path(out) / HOLDOUT_DIR / "LOCKED").exists()
    assert not (Path(out) / DEV_DIR / "LOCKED").exists()


def test_no_unredacted_pii_in_sample(tmp_path):
    _sample(tmp_path)
    for split in ("dev", "holdout"):
        for thread in _read_threads(tmp_path / split / "threads.jsonl"):
            assert not _scan_pii(thread), f"PII leak in {thread['thread_id']}"


def test_no_unredacted_pii_in_committed_files():
    root = Path(__file__).resolve().parents[1] / "data" / "golden"
    if not root.exists():
        pytest.skip("no committed golden set yet")
    files = list(root.rglob("*.jsonl")) + list(root.rglob("*.csv"))
    assert files, "golden set committed but empty"
    for path in files:
        assert not any(p.search(path.read_text()) for p in _PII_PATTERNS), f"PII in {path}"


def test_rationales_on_every_escalate(tmp_path):
    _sample(tmp_path)
    for split in ("dev", "holdout"):
        for thread in _read_threads(tmp_path / split / "threads.jsonl"):
            if thread["decision"] == "escalate":
                assert thread["rationale"].strip(), f"no rationale {thread['thread_id']}"


def test_reply_chains_preserved(tmp_path):
    from src.ingest import build_thread

    _sample(tmp_path)
    for split in ("dev", "holdout"):
        for thread in _read_threads(tmp_path / split / "threads.jsonl"):
            turns = thread["turns"]
            assert len(turns) >= 1
            by_id = {t["tweet_id"] for t in turns}
            for turn in turns[1:]:
                assert turn["in_response_to_tweet_id"] in by_id
            ctx = build_thread(turns, thread["target_id"])
            assert ctx.target == turns[-1]["text"]
            assert not _scan_pii(ctx.target)


def test_rater_sheets_blank_and_blind(tmp_path):
    _sample(tmp_path)
    write_rater_sheets(tmp_path)
    for name, n_rows in (("calibration.csv", 15), ("main.csv", 50)):
        with open(tmp_path / SHEETS_DIR / name) as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == n_rows
        for col in ("thread_id", "intent_label", "auto_or_escalate", "rationale"):
            assert col in rows[0], f"missing {col} in {name}"
        for banned in ("model_draft", "model_verdict", "judge", "prediction"):
            assert banned not in rows[0], f"model output pre-filled in {name}"
        for row in rows:
            assert row["thread_id"].strip()
            assert row["intent_label"].strip() == ""
            assert row["auto_or_escalate"].strip() == ""
    assert (tmp_path / SHEETS_DIR / "guidelines.md").exists()


def test_golden_adds_no_llm_call_site():
    src = (Path(__file__).resolve().parents[1] / "src" / "golden.py").read_text().lower()
    for banned in ("groq", "gemini", "openai", "anthropic", "httpx", "requests", "urlopen"):
        assert banned not in src
