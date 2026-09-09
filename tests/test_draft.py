"""F005: reply drafter (Groq) — LLM call site #1 (design §5 nodes 4b/4d, §9, §12).

Tests run on a fake client (no keys, no network). Cache is isolated per-test
via tmp_path; the real default lives under data/cache/.
"""

from src.draft import draft, free_draft_prompt, grounded_draft_prompt


class FakeClient:
    """Injectable Groq stand-in: records (prompt, model, temperature)."""

    def __init__(self, text="thanks for reaching out — we can help"):
        self.calls = []
        self.text = text

    def __call__(self, prompt, model, temperature):
        self.calls.append({"prompt": prompt, "model": model, "temperature": temperature})
        return self.text


# --- F005-1: prompt builders ---


def test_grounded_prompt_contains_intent_exemplars_strategy():
    prompt = grounded_draft_prompt(
        target="my refund never arrived",
        context="we asked for details",
        intent=2,
        exemplars=["please DM us your details", "we will check the refund status"],
        strategy="request_DM_plus_verify",
    )
    assert "2" in prompt
    assert "please DM us your details" in prompt
    assert "we will check the refund status" in prompt
    assert "request_DM_plus_verify" in prompt


def test_free_prompt_omits_exemplars_and_strategy():
    prompt = free_draft_prompt(target="thanks so much!", context="")
    assert "please DM us your details" not in prompt
    assert "request_DM_plus_verify" not in prompt
    assert "exemplar" not in prompt.lower()
    assert "thanks so much!" in prompt


def test_prompt_builders_redact_pii():
    dirty = "call me on (212) 555-0199, ssn 123-45-6789"
    for prompt in (
        free_draft_prompt(target=dirty, context=""),
        grounded_draft_prompt(
            target=dirty, context=dirty, intent=1, exemplars=[dirty], strategy="s"
        ),
    ):
        assert "555-0199" not in prompt
        assert "123-45-6789" not in prompt


# --- F005-2: artifact cache keyed by (provider, model, prompt hash) ---


def test_draft_cache_hit_avoids_second_client_call(tmp_path):
    client = FakeClient()
    prompt = free_draft_prompt(target="hello there", context="")
    first = draft(prompt, client=client, model="m1", cache_dir=tmp_path)
    second = draft(prompt, client=client, model="m1", cache_dir=tmp_path)
    assert len(client.calls) == 1
    assert first == second


def test_draft_model_mismatch_invalidates(tmp_path):
    client = FakeClient()
    prompt = free_draft_prompt(target="hello there", context="")
    draft(prompt, client=client, model="m1", cache_dir=tmp_path)
    draft(prompt, client=client, model="m2", cache_dir=tmp_path)
    assert len(client.calls) == 2


def test_draft_prompt_hash_mismatch_invalidates(tmp_path):
    client = FakeClient()
    draft("prompt one", client=client, model="m1", cache_dir=tmp_path)
    draft("prompt two", client=client, model="m1", cache_dir=tmp_path)
    assert len(client.calls) == 2


def test_draft_temperature_zero_and_artifact_fields(tmp_path):
    client = FakeClient()
    artifact = draft("hi", client=client, model="m1", cache_dir=tmp_path)
    assert client.calls[0]["temperature"] == 0
    assert artifact["provider"] == "groq"
    assert artifact["model"] == "m1"
    assert artifact["prompt_hash"]
    assert artifact["judge_guided_retry"] is False
    retry = draft("other", client=client, model="m1", judge_guided_retry=True, cache_dir=tmp_path)
    assert retry["judge_guided_retry"] is True
