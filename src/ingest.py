"""F001: thread reconstruction from reply-ID chains + PII redaction (design §5 node 1, §6).

No LLM, no deps beyond stdlib `re`. Every text emitted here is noise-stripped and
redacted, so nothing raw reaches a prompt or committed artifact (design entry 16).
"""

import re
from dataclasses import dataclass

from src.utils.logger import logger

# Context pieces are capped at ~300 chars each (design §5 node 1).
CONTEXT_CHARS = 300

# Noise stripping (design §5 node 1) — 2 regexes, no NLP libs.
_TCO_URL = re.compile(r"https?://t\.co/[A-Za-z0-9]+")
_TRUNCATION = re.compile(r"\s*…+\s*$")

# PII redaction (design §6). Replacement labels are digit-free, so the redactor is
# idempotent by construction. @mentions never match — they are kept as anonymised.
_GROUPED_CARD = re.compile(r"\b(?:\d{4}[ -]){2,3}\d{4}\b")
_ACCOUNT_RUN = re.compile(r"\d{8,}")  # account/card/10-digit-SSN bare runs
# zip-context before SSN: a zip+4 ("90210-1234") is 9 digits and would otherwise
# match the 3-2-4 SSN shape.
_ZIP_CONTEXT = re.compile(r"(?i)\b(zip|postal\s+code|address)\b([^0-9]{0,8})(\d{5}(?:-\d{4})?)")
_SSN = re.compile(r"\b\d{3}[\s-]?\d{2}[\s-]?\d{4}\b")
_PHONE = re.compile(r"(?:\+?\d{1,2}[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}\b")
_ADDRESS = re.compile(
    r"\b\d{1,5}\s+(?:[A-Z][a-zA-Z]*\s+){0,3}"
    r"(?:St|Street|Ave|Avenue|Rd|Road|Blvd|Boulevard|Ln|Lane|Dr|Drive|Way|Ct|Court|"
    r"Pl|Place|Cir|Circle)\b"
)


def strip_noise(text: str) -> str:
    """Drop t.co stubs and trailing truncation ellipses."""
    return _TRUNCATION.sub("", _TCO_URL.sub("", text)).strip()


def redact_pii(text: str) -> str:
    """Replace PII digit patterns with fixed labels. Idempotent; @mentions untouched."""
    text = _GROUPED_CARD.sub("[ACCOUNT]", text)
    text = _ACCOUNT_RUN.sub("[ACCOUNT]", text)
    text = _ZIP_CONTEXT.sub(r"\1\2[ZIP]", text)
    text = _SSN.sub("[SSN]", text)
    text = _PHONE.sub("[PHONE]", text)
    text = _ADDRESS.sub("[ADDRESS]", text)
    return text


@dataclass(frozen=True)
class ThreadContext:
    """Target message plus compact context (design §5 node 1)."""

    target_id: str
    position: int  # prior turns in the thread; 0 = first contact (design §6)
    target: str
    prev_customer: str
    last_brand_reply: str


def _sanitize(text: str) -> str:
    """Noise-strip + redact; every text build_thread emits passes through here."""
    return redact_pii(strip_noise(text))


def build_thread(tweets: list[dict], target_id: str) -> ThreadContext:
    """Walk in_response_to links from target; chain order is chronological order.

    A broken link stops the walk but keeps the ancestors collected so far; a
    first-contact tweet (no link) yields empty context. Position counts prior turns —
    thread position beats content for mid-thread fragments (design §6).
    """
    by_id = {t["tweet_id"]: t for t in tweets}
    if target_id not in by_id:
        raise KeyError(f"target tweet {target_id!r} not in tweet set")
    chain = [by_id[target_id]]
    seen = {target_id}
    while chain[-1]["in_response_to_tweet_id"]:
        parent_id = chain[-1]["in_response_to_tweet_id"]
        if parent_id in seen or parent_id not in by_id:
            logger.warning("chain walk stopped at broken/missing parent %s", parent_id)
            break
        chain.append(by_id[parent_id])
        seen.add(parent_id)
    chain.reverse()  # oldest → target

    prev_customer = ""
    last_brand_reply = ""
    for turn in reversed(chain[:-1]):  # closest ancestor first
        if not prev_customer and turn["inbound"]:
            prev_customer = _sanitize(turn["text"])[:CONTEXT_CHARS]
        if not last_brand_reply and not turn["inbound"]:
            last_brand_reply = _sanitize(turn["text"])[:CONTEXT_CHARS]

    return ThreadContext(
        target_id=target_id,
        position=len(chain) - 1,
        target=_sanitize(chain[-1]["text"]),
        prev_customer=prev_customer,
        last_brand_reply=last_brand_reply,
    )
