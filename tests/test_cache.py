"""F011: shared LLM artifact cache (design §12, decision 17).

One read-through helper behind both LLM call sites (draft.py Groq,
judge.py Gemini). Tests run against tmp_path so committed data/cache/
is never touched.
"""

import json

from src import cache


class FakeClient:
    """Zero-arg stand-in for an LLM call: records invocations."""

    def __init__(self, text="cached text"):
        self.calls = 0
        self.text = text

    def __call__(self):
        self.calls += 1
        return self.text


def _call(tmp_path, client, provider="groq", model="m1", prompt="hello", **kwargs):
    return cache.get_or_call(provider, model, prompt, client, cache_dir=tmp_path, **kwargs)


def test_key_deterministic_and_mismatch_sensitive():
    first = cache.key("groq", "m1", "abc123")
    assert first == cache.key("groq", "m1", "abc123")
    assert cache.key("gemini", "m1", "abc123") != first
    assert cache.key("groq", "m2", "abc123") != first
    assert cache.key("groq", "m1", "def456") != first


def test_cache_hit_avoids_client_call(tmp_path):
    client = FakeClient()
    first = _call(tmp_path, client)
    second = _call(tmp_path, client)
    assert client.calls == 1
    assert first == second
    assert first["text"] == "cached text"


def test_provider_model_prompt_mismatch_invalidates(tmp_path):
    client = FakeClient()
    _call(tmp_path, client)
    _call(tmp_path, client, model="m2")
    _call(tmp_path, client, provider="gemini")
    _call(tmp_path, client, prompt="different prompt")
    assert client.calls == 4


def test_tampered_entry_falls_through_to_miss(tmp_path):
    client = FakeClient()
    artifact = _call(tmp_path, client)
    path = tmp_path / cache.key("groq", "m1", artifact["prompt_hash"])
    tampered = dict(artifact, model="some-other-model")
    path.write_text(json.dumps(tampered))
    second = _call(tmp_path, client)
    assert client.calls == 2
    assert second["model"] == "m1"


def test_corrupt_entry_falls_through_to_miss(tmp_path):
    client = FakeClient()
    artifact = _call(tmp_path, client)
    path = tmp_path / cache.key("groq", "m1", artifact["prompt_hash"])
    path.write_text("{not valid json")
    second = _call(tmp_path, client)
    assert client.calls == 2
    assert second["text"] == "cached text"
    assert json.loads(path.read_text())["text"] == "cached text"


def test_extra_fields_stored_on_artifact(tmp_path):
    artifact = _call(tmp_path, FakeClient(), extra={"judge_guided_retry": True})
    assert artifact["provider"] == "groq"
    assert artifact["model"] == "m1"
    assert artifact["prompt_hash"]
    assert artifact["prompt"] == "hello"
    assert artifact["judge_guided_retry"] is True
