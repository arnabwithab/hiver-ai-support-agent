"""verify.py recomputes report numbers from the committed evidence bundle."""

from src.eval import verify as verify_mod


def test_verify_reproduces_report_numbers():
    got = verify_mod.verify()
    for key, want in verify_mod.EXPECTED.items():
        assert abs(got[key] - want) < 0.005


def test_bundle_holds_fifty_drafts_and_verdicts():
    import json

    drafts = json.loads((verify_mod.EVAL_DIR / "drafts.json").read_text())
    verdicts = json.loads((verify_mod.EVAL_DIR / "verdicts.json").read_text())
    assert len(drafts) == 50 and len(verdicts) == 50
    assert all({"thread_id", "draft", "target"} <= set(d) for d in drafts)
    assert all({"thread_id", "verdict_text", "judge_pass", "model"} <= set(v) for v in verdicts)
