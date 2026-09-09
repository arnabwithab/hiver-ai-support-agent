"""Keyless arithmetic check over committed LLM evidence (NOT a re-run).

Reads the committed bundle (data/eval/drafts.json + verdicts.json) and the
filled rater sheets, recomputes judge-vs-rater agreement, fail-recall, and
rater kappas, and asserts they match docs/report.md. It replays recorded
verdicts — it does not re-judge anything. Fresh judgments need API keys
(see --live and the rejudge path); this checks our math, not the model.
Zero LLM calls, zero network. Run: make verify.
"""

import csv
import json
from pathlib import Path

from src.eval.metrics import cohen_kappa
from src.utils.logger import logger

EVAL_DIR = Path(__file__).resolve().parents[2] / "data" / "eval"
SHEETS_DIR = Path(__file__).resolve().parents[2] / "data" / "golden" / "sheets" / "filled"

# Report §2 constants (update both here and docs/report.md together).
EXPECTED = {
    "intent_kappa": 0.928,
    "auto_kappa": 1.0,
    "draft_agreement": 0.84,
    "judge_vs_human": 0.76,
    "judge_vs_r1": 0.60,
    "fail_recall_human": 0.40,
    "fail_recall_r1": 0.18,
}


def _sheets():
    human, r1 = {}, {}
    for path in sorted(SHEETS_DIR.glob("filled_v2_*_human.csv")):
        for row in csv.DictReader(path.open()):
            human[row["thread_id"]] = row
    for path in sorted(SHEETS_DIR.glob("filled_v2_*_r1.csv")):
        for row in csv.DictReader(path.open()):
            r1[row["thread_id"]] = row
    return human, r1


def verify():
    """Recompute + assert. Returns the measured dict."""
    verdicts = {
        v["thread_id"]: v["judge_pass"]
        for v in json.loads((EVAL_DIR / "verdicts.json").read_text())
    }
    drafts = json.loads((EVAL_DIR / "drafts.json").read_text())
    assert len(drafts) == 50 and len(verdicts) == 50, "bundle must hold 50 drafts + 50 verdicts"
    human, r1 = _sheets()
    tids = sorted(set(human) & set(r1))
    got = {
        "intent_kappa": cohen_kappa(
            [human[t]["intent_label"] for t in tids], [r1[t]["intent_label"] for t in tids]
        ),
        "auto_kappa": cohen_kappa(
            [human[t]["auto_or_escalate"] for t in tids],
            [r1[t]["auto_or_escalate"] for t in tids],
        ),
    }
    main = [t for t in tids if human[t]["draft_pass_fail"]]
    got["draft_agreement"] = sum(
        1 for t in main if human[t]["draft_pass_fail"] == r1[t]["draft_pass_fail"]
    ) / len(main)
    judged = sorted(set(verdicts) & set(main))
    for name, panel in (("human", human), ("r1", r1)):
        pv = [(verdicts[t], panel[t]["draft_pass_fail"] == "pass") for t in judged]
        got[f"judge_vs_{name}"] = sum(1 for j, r in pv if j == r) / len(pv)
        fails = [t for t in judged if panel[t]["draft_pass_fail"] != "pass"]
        got[f"fail_recall_{name}"] = sum(1 for t in fails if not verdicts[t]) / max(len(fails), 1)
    logger.info("verify: %s", {k: round(v, 3) for k, v in got.items()})
    for key, want in EXPECTED.items():
        assert abs(got[key] - want) < 0.005, f"{key}: got {got[key]:.3f}, report says {want:.3f}"
    print(json.dumps({k: round(v, 3) for k, v in got.items()}, indent=2))
    return got


if __name__ == "__main__":
    verify()
