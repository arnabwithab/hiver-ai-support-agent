"""Thread-state machine. Design §6. Pure logic, no LLM, stdlib only.

State dict: {active_intent, history[], awaiting_user, resolved}.

Cases:
  A  social (7/8) with no prior substantive intent -> free-draft ack
  B  social after a substantive intent -> canned ack + resolved=True
     (exception: awaiting_user set -> ack but keep the thread open)
  C  new substantive intent -> becomes active_intent, predecessors to history[]
  D  keyword veto: social prediction + money/account/action terms or `?`
     -> informational/fall-through (fail-closed)
  continuation  low-conf slot-filler inherits the prior high-conf intent at a
     discounted confidence (fallback only; fresh per-turn classification default)

Every decision logs and returns the (raw prediction -> override -> final) triple
so F009 can count veto / inheritance / Case-B closes.
"""

import re

from src.utils.logger import logger

# Intent taxonomy (§4): 7 = praise_thanks, 8 = greeting_smalltalk.
SOCIAL = {7, 8}
# 9 = other: the informational/fall-through intent for vetoes and fail-closed paths.
OTHER = 9

# Money/account/action terms that veto a social prediction (Case D).
_VETO_TERMS = (
    "refund",
    "charge",
    "bill",
    "payment",
    "money",
    "fee",
    "balance",
    "account",
    "card",
    "login",
    "password",
    "locked",
    "access",
    "order",
    "delivery",
    "replace",
    "activate",
    "dispute",
)

# Confidence bars. The tuning threshold T lands in F002; these encode the
# design's Case-B-close and continuation requirements.
CONF_HIGH = 0.7  # required to close a social-after-substantive thread (Case B)
CONF_LOW = 0.5  # below this, a slot-filler may inherit the prior intent
_CONT_DISCOUNT = 0.5

_SLOT_FILLERS = {
    "yes",
    "yeah",
    "yep",
    "y",
    "no",
    "nope",
    "n",
    "thanks",
    "thank you",
    "ok",
    "okay",
    "sure",
    "correct",
    "right",
    "got it",
}
_SLOT_NUM_RE = re.compile(r"^\d{3,12}$")


def new_state(active_intent=None, history=None, awaiting_user=False, resolved=False):
    """Build a fresh state dict with the minimal §6 shape."""
    return {
        "active_intent": active_intent,
        "history": list(history or []),
        "awaiting_user": bool(awaiting_user),
        "resolved": bool(resolved),
    }


def _veto_hits(text):
    t = text.lower()
    return "?" in t or any(term in t for term in _VETO_TERMS)


def _is_slot_filler(text):
    t = text.strip().lower()
    return t in _SLOT_FILLERS or bool(_SLOT_NUM_RE.match(t))


def _apply_substantive(s, intent):
    """Case C: a substantive intent becomes active; the prior one joins history."""
    if s["active_intent"] is not None and s["active_intent"] != intent:
        s["history"].append(s["active_intent"])
    s["active_intent"] = intent
    s["resolved"] = False  # new substantive work reopens a closed thread


def _log(decision):
    logger.info(
        "routing raw=%s override=%s final=%s case=%s",
        decision["raw_intent"],
        decision["override"],
        decision["final_intent"],
        decision["case"],
    )


def transition(state, *, raw_intent, confidence, text, prior_confidence=None):
    """Route one customer turn given its classifier prediction.

    Returns a dict with the (possibly updated) state and the decision triple:
    state, raw_intent, override, final_intent, confidence, case, continuation,
    resolved. `state` is copied, never mutated in place.
    """
    s = dict(state)
    s["history"] = list(s["history"])
    decision = {
        "state": s,
        "raw_intent": raw_intent,
        "override": None,
        "final_intent": raw_intent,
        "confidence": confidence,
        "case": None,
        "continuation": False,
        "resolved": False,
    }

    prior_high = prior_confidence is not None and prior_confidence >= CONF_HIGH

    # Case D: keyword veto on a social prediction (fail-closed to substantive).
    if raw_intent in SOCIAL and _veto_hits(text):
        decision["override"] = "veto"
        decision["final_intent"] = OTHER
        decision["case"] = "D"
        _apply_substantive(s, OTHER)

    # Continuation fallback: low-conf slot-filler inherits the prior intent.
    elif (
        confidence < CONF_LOW
        and _is_slot_filler(text)
        and s["active_intent"] is not None
        and prior_high
    ):
        decision["override"] = "continuation"
        decision["final_intent"] = s["active_intent"]
        decision["confidence"] = prior_confidence * _CONT_DISCOUNT
        decision["case"] = "continuation"
        decision["continuation"] = True
        # Thread continues on the same intent; state is unchanged.

    elif raw_intent in SOCIAL:
        if s["active_intent"] is None:
            # Case A: pure social thread, no prior substantive intent.
            decision["case"] = "A"
        elif confidence >= CONF_HIGH:
            # Case B: social after substantive -> canned ack + resolved,
            # except when awaiting_user (ack but keep the thread open).
            decision["case"] = "B"
            if not s["awaiting_user"]:
                s["resolved"] = True
                decision["resolved"] = True
        else:
            # Low-confidence social after substantive: fail-closed, do not close.
            decision["case"] = "C"
            decision["final_intent"] = OTHER
            _apply_substantive(s, OTHER)

    else:
        # Case C: a new substantive intent.
        decision["case"] = "C"
        _apply_substantive(s, raw_intent)

    _log(decision)
    return decision
