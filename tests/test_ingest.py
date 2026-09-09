"""F001: thread ingestion (reply-chain walk) + PII redaction (design §5 node 1, §6).

The redactor is a graded-claim dependency (design entry 16): raw PII must never
reach a prompt or committed artifact, so the chain-walk tests assert redacted
outputs, and every emitted field is covered.
"""

import pytest

from src.ingest import ThreadContext, build_thread, redact_pii, strip_noise


def _tweet(tweet_id, text, inbound=True, in_response_to=None, author=None):
    return {
        "tweet_id": tweet_id,
        "in_response_to_tweet_id": in_response_to,
        "inbound": inbound,
        "text": text,
        "author": author,
    }


# --- F001-2: PII redactor ---


def test_redact_ssn():
    assert redact_pii("my ssn is 123-45-6789") == "my ssn is [SSN]"
    assert redact_pii("ssn 123 45 6789") == "ssn [SSN]"
    # A bare 9-digit run is the same shape as a digit-free account run; either
    # label satisfies the guardrail — the point is no digit pattern survives.
    assert "123456789" not in redact_pii("bare 123456789")


def test_redact_account_digit_runs():
    assert redact_pii("acct 123456789012") == "acct [ACCOUNT]"
    assert redact_pii("card 1234-5678-9012") == "card [ACCOUNT]"
    assert redact_pii("card 1234 5678 9012 3456") == "card [ACCOUNT]"


def test_redact_phone():
    assert redact_pii("call (212) 555-0199 now") == "call [PHONE] now"
    assert redact_pii("call 212-555-0199 now") == "call [PHONE] now"
    assert redact_pii("call +1 212 555 0199") == "call [PHONE]"


def test_redact_zip_in_context_only():
    assert redact_pii("my zip is 10001") == "my zip is [ZIP]"
    assert redact_pii("postal code 90210-1234") == "postal code [ZIP]"
    assert redact_pii("send to address 10001") == "send to address [ZIP]"
    assert redact_pii("ref 10001 stays") == "ref 10001 stays"


def test_redact_address():
    assert redact_pii("I live at 123 Main St") == "I live at [ADDRESS]"
    assert redact_pii("billing: 456 Oak Avenue") == "billing: [ADDRESS]"


def test_redact_keeps_anonymised_mentions():
    text = "@chasesupport @user123 please help"
    assert redact_pii(text) == text


def test_redact_keeps_short_reference_codes():
    # Continuation slot-filler (design §6) — 4 digits, not PII.
    assert redact_pii("yes, 3467") == "yes, 3467"


def test_redact_idempotent():
    dirty = "ssn 123-45-6789, phone (212) 555-0199, acct 123456789012, " "zip 10001, 123 Main St"
    once = redact_pii(dirty)
    assert redact_pii(once) == once
    assert not any(ch.isdigit() for ch in once)


# --- Noise stripping ---


def test_strip_noise_removes_tco_stub_and_truncation():
    assert strip_noise("read this https://t.co/abc123 …") == "read this"
    assert strip_noise("reply coming…") == "reply coming"
    assert strip_noise("no noise here") == "no noise here"


# --- F001-1: reply-chain walk ---


def test_build_thread_first_contact_empty_context():
    tweets = [_tweet("t1", "hello there")]
    ctx = build_thread(tweets, "t1")
    assert ctx.target_id == "t1"
    assert ctx.position == 0
    assert ctx.target == "hello there"
    assert ctx.prev_customer == ""
    assert ctx.last_brand_reply == ""


def test_build_thread_walks_chain_and_orders_chronologically():
    tweets = [
        _tweet("t1", "I can't log in"),
        _tweet("t2", "Please DM us for help", inbound=False, in_response_to="t1"),
        _tweet("t3", "ok my ssn is 123-45-6789", in_response_to="t2"),
    ]
    ctx = build_thread(tweets, "t3")
    assert isinstance(ctx, ThreadContext)
    assert ctx.position == 2
    assert ctx.prev_customer == "I can't log in"
    assert ctx.last_brand_reply == "Please DM us for help"
    assert ctx.target == "ok my ssn is [SSN]"  # PII redacted in emitted text


def test_build_thread_broken_link_keeps_existing_ancestors():
    tweets = [
        _tweet("t2", "Please DM us", inbound=False, in_response_to="tZ"),  # tZ missing
        _tweet("t3", "dm sent", in_response_to="t2"),
    ]
    ctx = build_thread(tweets, "t3")
    assert ctx.position == 1
    assert ctx.prev_customer == ""
    assert ctx.last_brand_reply == "Please DM us"


def test_build_thread_context_char_cap():
    long_text = "x" * 500
    tweets = [
        _tweet("t1", long_text),
        _tweet("t2", long_text, inbound=False, in_response_to="t1"),
        _tweet("t3", "still here", in_response_to="t2"),
    ]
    ctx = build_thread(tweets, "t3")
    assert len(ctx.prev_customer) <= 300
    assert len(ctx.last_brand_reply) <= 300


def test_build_thread_redacts_all_emitted_text():
    tweets = [
        _tweet("t1", "my phone is (212) 555-0199"),
        _tweet("t2", "we called you", inbound=False, in_response_to="t1"),
        _tweet("t3", "my account 123456789012 is locked", in_response_to="t2"),
    ]
    ctx = build_thread(tweets, "t3")
    assert "555-0199" not in ctx.prev_customer
    assert "123456789012" not in ctx.target
    assert "555-0199" not in str(ctx)


def test_build_thread_missing_target_raises():
    with pytest.raises(KeyError):
        build_thread([_tweet("t1", "hi")], "nope")
