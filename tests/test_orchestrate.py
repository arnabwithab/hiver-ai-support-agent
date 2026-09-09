"""F007: pipeline orchestration — DAG only (design §5). Tests run on fakes, no keys."""

from src.intent import embed
from src.state import new_state

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


class FakeClassifier:
    def __init__(self, intent, confidence=0.9):
        self.intent = intent
        self.confidence = confidence

    def predict(self, text):
        return self.intent

    def calibrated_confidence(self, text):
        return self.confidence


class FakeDraftClient:
    def __init__(self, text="draft reply"):
        self.text = text
        self.calls = []

    def __call__(self, prompt, model, temperature):
        self.calls.append({"prompt": prompt, "model": model, "temperature": temperature})
        return self.text


class FakeJudgeClient:
    def __init__(self, texts):
        self.texts = list(texts)
        self.calls = []

    def __call__(self, prompt, model, temperature):
        self.calls.append({"prompt": prompt, "model": model, "temperature": temperature})
        idx = min(len(self.calls) - 1, len(self.texts) - 1)
        return self.texts[idx]


def make_tweets(target_text, parent=None):
    tweets = [
        {"tweet_id": "t1", "inbound": True, "text": target_text, "in_response_to_tweet_id": None}
    ]
    if parent is not None:
        tweets.append(
            {
                "tweet_id": "t0",
                "inbound": parent[1],
                "text": parent[0],
                "in_response_to_tweet_id": None,
            }
        )
        tweets[0]["in_response_to_tweet_id"] = "t0"
    return tweets


def make_index(
    intent, exemplar="Please DM us so we can check this securely", strategy="request_dm_plus_verify"
):
    return {intent: [{"text": exemplar, "strategy": strategy, "vec": embed(exemplar)}]}


def test_case_a_serves_judged_free_draft(tmp_path):
    from src.orchestrate import handle_message

    draft_client = FakeDraftClient("Hello! How can we help today?")
    judge_client = FakeJudgeClient([PASS_TEXT])
    result = handle_message(
        make_tweets("Hello there!"),
        "t1",
        state=new_state(),
        classifier=FakeClassifier(8, 0.9),
        index=make_index(8, "Hello, how can we help today", "acknowledge"),
        draft_client=draft_client,
        judge_client=judge_client,
        cache_dir=tmp_path,
    )
    assert result["case"] == "A"
    assert result["decision"] == "serve"
    assert result["text"] == "Hello! How can we help today?"
    assert len(judge_client.calls) == 1
    # free draft: no exemplars in the prompt
    assert "Brand exemplar" not in draft_client.calls[0]["prompt"]


def test_case_b_closes_with_no_judge_call(tmp_path):
    from src.orchestrate import handle_message

    draft_client = FakeDraftClient()
    judge_client = FakeJudgeClient([PASS_TEXT])
    result = handle_message(
        make_tweets("Thanks so much!"),
        "t1",
        state=new_state(active_intent=1, history=[]),
        classifier=FakeClassifier(7, 0.95),
        index=make_index(7),
        draft_client=draft_client,
        judge_client=judge_client,
        cache_dir=tmp_path,
    )
    assert result["case"] == "B"
    assert result["decision"] == "resolve"
    assert result["state"]["resolved"] is True
    assert result["text"]
    assert draft_client.calls == []
    assert judge_client.calls == []


def test_case_c_drafts_grounded_and_serves(tmp_path):
    from src.orchestrate import handle_message

    draft_client = FakeDraftClient("Please DM us so we can check the charge.")
    judge_client = FakeJudgeClient([PASS_TEXT])
    result = handle_message(
        make_tweets("I was charged twice this month"),
        "t1",
        state=new_state(),
        classifier=FakeClassifier(1, 0.9),
        index=make_index(1),
        draft_client=draft_client,
        judge_client=judge_client,
        cache_dir=tmp_path,
    )
    assert result["case"] == "C"
    assert result["decision"] == "serve"
    assert result["final_intent"] == 1
    assert result["state"]["active_intent"] == 1
    prompt = draft_client.calls[0]["prompt"]
    assert "Brand exemplar" in prompt
    assert "DM" in prompt


def test_case_d_vetoes_to_informational(tmp_path):
    from src.orchestrate import handle_message

    draft_client = FakeDraftClient("Please DM us so we can look into this.")
    judge_client = FakeJudgeClient([PASS_TEXT])
    result = handle_message(
        make_tweets("Thanks! Also, where is my refund?"),
        "t1",
        state=new_state(),
        classifier=FakeClassifier(7, 0.9),
        index=make_index(9),
        draft_client=draft_client,
        judge_client=judge_client,
        cache_dir=tmp_path,
    )
    assert result["case"] == "D"
    assert result["final_intent"] == 9
    assert result["decision"] == "serve"
    assert len(judge_client.calls) == 1


def test_judge_exhaustion_escalates_with_handoff_note(tmp_path):
    from src.orchestrate import handle_message

    draft_client = FakeDraftClient("a bad draft")
    judge_client = FakeJudgeClient([FAIL_TEXT])
    result = handle_message(
        make_tweets("I was charged twice this month"),
        "t1",
        state=new_state(),
        classifier=FakeClassifier(1, 0.9),
        index=make_index(1),
        draft_client=draft_client,
        judge_client=judge_client,
        cache_dir=tmp_path,
    )
    assert result["decision"] == "escalate"
    assert result["text"] is None
    assert result["handoff_note"]
