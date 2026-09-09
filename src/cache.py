"""F011: shared LLM artifact cache (design §12, decision 17).

Single read-through helper behind both LLM call sites (draft.py Groq,
judge.py Gemini). Artifacts are keyed by (provider, model, prompt hash):
a hit never touches the client; a provider/model/hash mismatch or a corrupt
entry falls through to a miss. Stdlib only.
"""

import hashlib
import json
from pathlib import Path

from src.utils.logger import logger

CACHE_DIR = Path(__file__).resolve().parents[1] / "data" / "cache"


def prompt_hash(prompt):
    """Stable sha256 hex digest of a prompt string."""
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def key(provider, model, prompt_hash):
    """Cache filename for one (provider, model, prompt hash) triple."""
    safe_model = "".join(c if c.isalnum() else "_" for c in model)
    return f"{provider}_{safe_model}_{prompt_hash}.json"


def get_or_call(provider, model, prompt, call, cache_dir=None, extra=None):
    """Read-through cache: hit returns the stored artifact without calling
    ``call()`` (a zero-arg callable returning the raw LLM text); miss calls
    it once, stores ``{provider, model, prompt_hash, prompt, text, **extra}``
    and returns that artifact."""
    digest = prompt_hash(prompt)
    path = (cache_dir or CACHE_DIR) / key(provider, model, digest)
    if path.exists():
        try:
            artifact = json.loads(path.read_text())
        except (OSError, ValueError):
            artifact = None
        if (
            isinstance(artifact, dict)
            and artifact.get("provider") == provider
            and artifact.get("model") == model
            and artifact.get("prompt_hash") == digest
            and "text" in artifact
        ):
            logger.info("cache hit %s", path.name)
            return artifact
    artifact = {
        "provider": provider,
        "model": model,
        "prompt_hash": digest,
        "prompt": prompt,
        "text": call(),
        **(extra or {}),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact))
    logger.info("cache store %s", path.name)
    return artifact
