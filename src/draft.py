"""F005: reply drafter (Groq) — LLM call site #1 (design §5 nodes 4b/4d, §9, §12).

Free-draft policy for social-only threads (no exemplars); grounded policy with
intent + history + exemplars + strategy as hard context otherwise. Temperature 0,
provider + model recorded, artifacts cached by (provider, model, prompt hash).
No classification logic here — intent arrives as an argument (design §5).
"""

import hashlib
import json
import urllib.request
from pathlib import Path

from src.ingest import redact_pii
from src.utils.config import settings
from src.utils.logger import logger

PROVIDER = "groq"
TEMPERATURE = 0
CACHE_DIR = Path(__file__).resolve().parents[1] / "data" / "cache"
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
    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        _GROQ_URL,
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload["choices"][0]["message"]["content"]


def _cache_path(provider, model, prompt_hash, cache_dir):
    safe_model = "".join(c if c.isalnum() else "_" for c in model)
    return (cache_dir or CACHE_DIR) / f"{provider}_{safe_model}_{prompt_hash}.json"


def draft(prompt, client=None, model=None, judge_guided_retry=False, cache_dir=None):
    """Read-through cache: hit returns the artifact without touching the client."""
    model = model or settings.GROQ_MODEL
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    path = _cache_path(PROVIDER, model, prompt_hash, cache_dir)
    if path.exists():
        try:
            artifact = json.loads(path.read_text())
        except (OSError, ValueError):
            artifact = None
        if (
            artifact
            and artifact.get("provider") == PROVIDER
            and artifact.get("model") == model
            and artifact.get("prompt_hash") == prompt_hash
        ):
            logger.info("draft cache hit %s", path.name)
            return artifact
    text = (client or groq_complete)(prompt, model, TEMPERATURE)
    artifact = {
        "provider": PROVIDER,
        "model": model,
        "prompt_hash": prompt_hash,
        "prompt": prompt,
        "text": text,
        "judge_guided_retry": judge_guided_retry,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact))
    logger.info("draft cached %s", path.name)
    return artifact
