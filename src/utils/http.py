"""Shared OpenAI-compatible chat transport (stdlib urllib).

Not an LLM call site: the two LLM clients (groq_complete in src/draft.py,
gemini_complete in src/judge.py) are the only callers, so the
exactly-two-call-sites guardrail still holds — grep post_json to verify.
"""

import json
import urllib.request


def post_json(url, api_key, model, prompt, temperature):
    """POST one chat-completion request; return the assistant text."""
    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload["choices"][0]["message"]["content"]
