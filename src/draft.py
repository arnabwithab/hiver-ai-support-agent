"""F005: reply drafter (Groq) — LLM call site #1 (design §5 nodes 4b/4d, §9, §12).

Free-draft policy for social-only threads (no exemplars); grounded policy with
intent + history + exemplars + strategy as hard context otherwise. Temperature 0,
provider + model recorded, artifacts cached by (provider, model, prompt hash).
No classification logic here — intent arrives as an argument (design §5).
"""

from src import cache
from src.ingest import redact_pii
from src.utils.config import settings
from src.utils.http import post_json

PROVIDER = "groq"
TEMPERATURE = 0
CACHE_DIR = cache.CACHE_DIR
_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def free_draft_prompt(target, context=""):
    """Social-only ack (design §5 node 4b): target + history only, no exemplars."""
    target = redact_pii(target)
    context = redact_pii(context or "")
    lines = [
        "You are ChaseSupport. Write a brief, friendly acknowledgement.",
        "Keep it to one or two sentences. Do not promise any account action.",
        f"Customer message: {target}",
    ]
    if context:
        lines.append(f"Thread history: {context}")
    return "\n".join(lines)


def grounded_draft_prompt(target, context, intent, exemplars, strategy):
    """Grounded draft (design §5 node 4d): exemplars + strategy are hard context."""
    lines = [
        "You are ChaseSupport. Draft a reply grounded in how the brand "
        "resolved similar issues. Follow the resolution strategy below; "
        "request takeover rather than inventing an answer.",
        f"Intent: {intent}",
        f"Customer message: {redact_pii(target)}",
    ]
    if context:
        lines.append(f"Thread history: {redact_pii(context)}")
    lines.append(f"Resolution strategy: {redact_pii(strategy)}")
    for exemplar in exemplars:
        lines.append(f"Brand exemplar: {redact_pii(exemplar)}")
    return "\n".join(lines)


def groq_complete(prompt, model, temperature=TEMPERATURE):
    """Default client: Groq OpenAI-compatible endpoint over stdlib urllib."""
    key = settings.GROQ_API_KEY
    if not key:
        raise RuntimeError("GROQ_API_KEY is missing")
    return post_json(_GROQ_URL, key, model, prompt, temperature)


def draft(prompt, client=None, model=None, judge_guided_retry=False, cache_dir=None):
    """Read-through cache: hit returns the artifact without touching the client."""
    model = model or settings.GROQ_MODEL

    def call():
        return (client or groq_complete)(prompt, model, TEMPERATURE)

    return cache.get_or_call(
        PROVIDER,
        model,
        prompt,
        call,
        cache_dir=cache_dir,
        extra={"judge_guided_retry": judge_guided_retry},
    )
