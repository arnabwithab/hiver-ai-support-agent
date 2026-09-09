"""F006: judge as gate and critic (Gemini) — LLM call site #2 (design §9).

Tests run on a fake client (no keys, no network). Case-B canned acks never
enter the gate (design §5/§9) — no test calls the judge for those.
"""

from src.judge import (
    MAX_RETRIES,
    RUBRIC_VERSION,
    judge,
    judge_prompt,
    parse_verdict,
    review,
)

PASS_TEXT = (
    "groundedness: pass - requests DM takeover per exemplar\n"
    "tone_policy: pass - polite, no PII\n"
    "escalation_correctness: pass - correct to serve"
)

FAIL_TEXT = (
    "groundedness: fail - invents an account answer instead of takeover\n"
    "tone_policy: pass - polite\n"
    "escalation_correctness: pass - correct to serve"
)


class FakeClient:
    """Injectable Gemini stand-in: records (prompt, model, temperature)."""

    def __init__(self, texts):
        self.texts = list(texts)
        self.calls = []

    def __call__(self, prompt, model, temperature):
        self.calls.append({"prompt": prompt, "model": model, "temperature": temperature})
        if len(self.calls) <= len(self.texts):
            return self.texts[len(self.calls) - 1]
        return self.texts[-1]


# --- F006-1: rubric prompt + parsing ---


def test_rubric_version_pinned_in_prompt():
    prompt = judge_prompt(draft_text="hello", target="hi")
    assert RUBRIC_VERSION in prompt
    assert "groundedness" in prompt
    assert "tone_policy" in prompt
    assert "escalation_correctness" in prompt


def test_prompt_redacts_pii():
    dirty = "my ssn is 123-45-6789 call (212) 555-0199"
    prompt = judge_prompt(draft_text=dirty, target=dirty, context=dirty)
    assert "123-45-6789" not in prompt
    assert "555-0199" not in prompt


def test_parse_verdict_pass_fail_per_criterion_with_rationale():
    verdict = parse_verdict(PASS_TEXT)
    assert verdict["pass"] is True
    for criterion in ("groundedness", "tone_policy", "escalation_correctness"):
        assert verdict["criteria"][criterion]["pass"] is True
        assert verdict["criteria"][criterion]["rationale"]
    failed = parse_verdict(FAIL_TEXT)
    assert failed["pass"] is False
    assert failed["criteria"]["groundedness"]["pass"] is False
    assert failed["criteria"]["groundedness"]["rationale"]


def test_judge_temperature_zero():
    client = FakeClient([PASS_TEXT])
    judge("a clean draft", target="hello", client=client, model="m1")
    assert client.calls[0]["temperature"] == 0


def test_pii_echo_draft_fails_tone_policy_despite_llm_pass():
    # Local PII check overrides the LLM: fake client says pass everywhere,
    # but the draft echoes customer PII, so tone_policy must fail.
    pii_draft = "thanks! confirming your ssn 123-45-6789 and (212) 555-0199"
    verdict = judge(pii_draft, target="here is my ssn", client=FakeClient([PASS_TEXT]))
    assert verdict["pass"] is False
    assert verdict["criteria"]["tone_policy"]["pass"] is False
    assert verdict["criteria"]["tone_policy"]["rationale"]


# --- F006-2: gate/critic loop ---


def test_pass_through_serves_on_first_verdict():
    client = FakeClient([PASS_TEXT])
    calls = []

    def draft_fn(critique=""):
        calls.append(critique)
        return "a clean draft"

    result = review(draft_fn, target="hello", client=client)
    assert result["decision"] == "serve"
    assert result["text"] == "a clean draft"
    assert len(calls) == 1
    assert len(client.calls) == 1


def test_retry_loop_caps_at_3_then_escalates_with_rationale():
    client = FakeClient([FAIL_TEXT])
    seen = []

    def draft_fn(critique=""):
        seen.append(critique)
        return "a bad draft"

    result = review(draft_fn, target="hello", client=client)
    assert result["decision"] == "escalate"
    assert len(seen) == MAX_RETRIES + 1
    assert len(client.calls) == MAX_RETRIES + 1
    # Critique appended to the redraft prompt: later attempts see it.
    assert any("groundedness" in (c or "").lower() for c in seen[1:])
    # Judge rationale reused as the human handoff note (design §9).
    assert result["handoff_note"]
    assert (
        "takeover" in result["handoff_note"].lower() or "invent" in result["handoff_note"].lower()
    )


def test_retry_recovers_on_second_attempt():
    client = FakeClient([FAIL_TEXT, PASS_TEXT])
    seen = []

    def draft_fn(critique=""):
        seen.append(critique)
        return "a recovering draft"

    result = review(draft_fn, target="hello", client=client)
    assert result["decision"] == "serve"
    assert len(seen) == 2
