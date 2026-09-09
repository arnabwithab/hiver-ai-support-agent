"""F006: judge as gate and critic (Gemini) — LLM call site #2 (design §9).

One call, multi-criteria rubric (groundedness / tone_policy incl. PII-leak /
escalation-correctness + shift-aware check), rationale per verdict. Failures
return a critique for ≤3 retries, then drop-to-escalate with the rationale as
the human handoff note. Judge model != drafter model by construction (Gemini
here, Groq in src/draft.py). Temperature 0.

Deterministic Case-B canned acks carry no LLM content and are explicitly
outside this gate (design §5/§9): callers must never pass them to review().
"""

import json
import re
import urllib.request

from src.ingest import redact_pii
from src.utils.config import settings
from src.utils.logger import logger

PROVIDER = "gemini"
TEMPERATURE = 0
MAX_RETRIES = 3
RUBRIC_VERSION = "v1"

# Old rubrics retained for rollback (design §11: human signs off every change).
RUBRIC_V0 = "v0: pass if polite and relevant. Single overall verdict, no rationale."
# v1: per-criterion pass/fail + rationale; adds groundedness (DM-takeover is
# faithful, inventing answers fails), tone_policy PII-leak check,
# escalation-correctness, and the shift-aware groundedness check (Case C).

CRITERIA = ("groundedness", "tone_policy", "escalation_correctness")

_VERDICT_LINE = re.compile(
    r"^(groundedness|tone_policy|escalation_correctness)\s*:\s*(pass|fail)\b\s*[-–:.]?\s*(.*)$",
    re.IGNORECASE | re.MULTILINE,
)


def _has_pii(text):
    """Local PII check: any redactor pattern hit means the draft leaks PII."""
    return redact_pii(text) != text


def judge_prompt(
    draft_text, target="", context="", intent=None, exemplars=(), strategy="", shift=False
):
    """Versioned rubric prompt. Every text is redacted before entering the prompt."""
    lines = [
        f"You are the ChaseSupport reply judge (rubric {RUBRIC_VERSION}).",
        "Rate the draft on each criterion as 'pass' or 'fail' with a short rationale,",
        "one per line in the form '<criterion>: <pass|fail> - <rationale>'.",
        "Criteria: groundedness (faithful to exemplars/strategy; requesting DM",
        "takeover instead of inventing an answer passes; echoing customer PII fails",
        "tone_policy too); tone_policy (polite, no PII leak — any draft echoing",
        "customer PII fails); escalation_correctness (serve vs escalate is right).",
    ]
    if shift:
        lines.append(
            "Shift-aware check: the thread changed intent — the draft must acknowledge "
            "any still-open prior intent or fail groundedness."
        )
    lines.append(f"Customer message: {redact_pii(target)}")
    if context:
        lines.append(f"Thread history: {redact_pii(context)}")
    if intent is not None:
        lines.append(f"Intent: {intent}")
    if strategy:
        lines.append(f"Resolution strategy: {redact_pii(strategy)}")
    for exemplar in exemplars:
        lines.append(f"Brand exemplar: {redact_pii(exemplar)}")
    lines.append(f"Draft to judge: {redact_pii(draft_text)}")
    return "\n".join(lines)


def parse_verdict(text):
    """Parse per-criterion pass/fail + rationale. Fail-closed: missing → fail."""
    found = {}
    for match in _VERDICT_LINE.finditer(text or ""):
        name = match.group(1).lower()
        if name not in found:  # first mention wins
            rationale = match.group(3).strip()
            found[name] = {"pass": match.group(2).lower() == "pass", "rationale": rationale}
    criteria = {}
    for name in CRITERIA:
        if name in found and found[name]["rationale"]:
            criteria[name] = found[name]
        elif name in found:
            criteria[name] = {"pass": False, "rationale": "verdict without rationale"}
        else:
            criteria[name] = {"pass": False, "rationale": "criterion missing from verdict"}
    passed = all(criteria[name]["pass"] for name in CRITERIA)
    critique = "; ".join(
        f"{name} failed: {criteria[name]['rationale']}"
        for name in CRITERIA
        if not criteria[name]["pass"]
    )
    return {"pass": passed, "criteria": criteria, "critique": critique}


def gemini_complete(prompt, model, temperature=TEMPERATURE):
    """Default client: Gemini OpenAI-compatible endpoint over stdlib urllib."""
    key = settings.GEMINI_API_KEY
    if not key:
        raise RuntimeError("GEMINI_API_KEY is missing")
    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        settings.GEMINI_BASE_URL.rstrip("/") + "/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload["choices"][0]["message"]["content"]


def judge(
    draft_text,
    target="",
    context="",
    intent=None,
    exemplars=(),
    strategy="",
    shift=False,
    client=None,
    model=None,
):
    """Judge one draft; local PII check overrides an LLM pass on tone_policy."""
    model = model or settings.GEMINI_MODEL
    prompt = judge_prompt(draft_text, target, context, intent, exemplars, strategy, shift)
    raw = (client or gemini_complete)(prompt, model, TEMPERATURE)
    verdict = parse_verdict(raw)
    if _has_pii(draft_text):
        verdict["criteria"]["tone_policy"] = {
            "pass": False,
            "rationale": "draft echoes customer PII (local check)",
        }
        verdict["pass"] = False
        verdict["critique"] = "; ".join(
            f"{name} failed: {verdict['criteria'][name]['rationale']}"
            for name in CRITERIA
            if not verdict["criteria"][name]["pass"]
        )
    verdict.update({"provider": PROVIDER, "model": model, "rubric_version": RUBRIC_VERSION})
    logger.info("judge verdict pass=%s model=%s", verdict["pass"], model)
    return verdict


def review(
    draft_fn,
    target="",
    context="",
    intent=None,
    exemplars=(),
    strategy="",
    shift=False,
    client=None,
    model=None,
    max_retries=MAX_RETRIES,
):
    """Gate/critic loop: draft_fn(critique) → judge; ≤max_retries redrafts, else escalate."""
    critique = ""
    verdict = None
    draft_text = ""
    attempts = 0
    for attempt in range(max_retries + 1):
        draft_text = draft_fn(critique)
        attempts = attempt + 1
        verdict = judge(
            draft_text, target, context, intent, exemplars, strategy, shift, client, model
        )
        if verdict["pass"]:
            return {
                "decision": "serve",
                "text": draft_text,
                "verdict": verdict,
                "attempts": attempts,
                "handoff_note": "",
            }
        critique = verdict["critique"]
        logger.info("judge fail attempt=%d critique=%s", attempts, critique)
    return {
        "decision": "escalate",
        "text": None,
        "verdict": verdict,
        "attempts": attempts,
        "handoff_note": critique,
    }
