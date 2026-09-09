"""F007: pipeline orchestration — the DAG only (design §5).

Sequences ingest → classify → gate/state → draft/retrieve → judge →
serve/retry/escalate. No business logic here: every stage decision lives in
its module; this file only threads the state dict
(active_intent/history/awaiting_user/resolved) through the calls.
No orchestration framework (design entry 3). LLM clients are injectable.
"""

from src import draft as draft_mod
from src import ingest, retrieve
from src import intent as intent_mod
from src import judge as judge_mod
from src import state as state_mod
from src.utils.logger import logger

# Deterministic Case-B ack: no LLM content, outside the judge gate (design §9).
CANNED_ACK = "You're welcome \u2014 glad we could help!"


def handle_message(
    tweets,
    target_id,
    state=None,
    *,
    classifier=None,
    index=None,
    draft_client=None,
    judge_client=None,
    draft_model=None,
    judge_model=None,
    max_retries=judge_mod.MAX_RETRIES,
    cache_dir=None,
):
    """Route one customer message end-to-end. Returns decision + updated state."""
    ctx = ingest.build_thread(tweets, target_id)
    clf = classifier or intent_mod.IntentClassifier()
    query = f"{ctx.prev_customer} {ctx.target}".strip() or ctx.target
    decision = state_mod.transition(
        state or state_mod.new_state(),
        raw_intent=clf.predict(query),
        confidence=clf.calibrated_confidence(query),
        text=ctx.target,
    )
    outcome = {
        "state": decision["state"],
        "case": decision["case"],
        "raw_intent": decision["raw_intent"],
        "final_intent": decision["final_intent"],
        "handoff_note": "",
        "attempts": 0,
    }
    if decision["case"] == "B":
        logger.info("orchestrate case=B decision=resolve target=%s", target_id)
        return {**outcome, "decision": "resolve", "text": CANNED_ACK}

    context = "\n".join(part for part in (ctx.prev_customer, ctx.last_brand_reply) if part)
    final = decision["final_intent"]
    if decision["case"] == "A":
        base, exemplars, strategy = draft_mod.free_draft_prompt(ctx.target, context), (), ""
    else:
        hits = retrieve.retrieve(
            final, query, index if index is not None else retrieve.build_index()
        )
        exemplars = [hit["text"] for hit in hits]
        strategy = hits[0]["strategy"] if hits else ""
        base = draft_mod.grounded_draft_prompt(ctx.target, context, final, exemplars, strategy)

    def draft_fn(critique=""):
        prompt = base if not critique else f"{base}\nJudge critique: {critique}"
        return draft_mod.draft(
            prompt,
            client=draft_client,
            model=draft_model,
            judge_guided_retry=bool(critique),
            cache_dir=cache_dir,
        )["text"]

    judged = judge_mod.review(
        draft_fn,
        target=ctx.target,
        context=context,
        intent=final,
        exemplars=exemplars,
        strategy=strategy,
        shift=bool(decision["state"]["history"]),
        client=judge_client,
        model=judge_model,
        max_retries=max_retries,
        cache_dir=cache_dir,
    )
    logger.info(
        "orchestrate case=%s decision=%s attempts=%d target=%s",
        decision["case"],
        judged["decision"],
        judged["attempts"],
        target_id,
    )
    return {
        **outcome,
        "decision": judged["decision"],
        "text": judged["text"],
        "handoff_note": judged["handoff_note"],
        "attempts": judged["attempts"],
    }
