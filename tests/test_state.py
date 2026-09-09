"""F003: thread-state machine (design §6). Pure logic, no LLM.

Every decision returns and logs the (raw prediction → override → final) triple
so F009 can count veto / inheritance / Case-B closes.
"""

from src.state import new_state, transition


def _base():
    return new_state()


# --- Case A: social, no prior substantive → free-draft ack ---
def test_case_a_social_first_draft():
    d = transition(_base(), raw_intent=7, confidence=0.8, text="Thanks!")
    assert d["case"] == "A"
    assert d["state"]["active_intent"] is None
    assert not d["state"]["resolved"]
    # triple returned
    assert d["raw_intent"] == 7 and d["override"] is None and d["final_intent"] == 7


# --- Case B: social after substantive → canned ack + resolved ---
def test_case_b_close():
    s = new_state(active_intent=2, history=[1])
    d = transition(s, raw_intent=7, confidence=0.9, text="Thanks!")
    assert d["case"] == "B"
    assert d["resolved"] and d["state"]["resolved"]
    assert d["state"]["active_intent"] == 2  # substantive intent preserved


def test_case_b_awaiting_user_keeps_open():
    s = new_state(active_intent=2, awaiting_user=True)
    d = transition(s, raw_intent=8, confidence=0.9, text="ok thanks")
    assert d["case"] == "B"
    assert not d["resolved"] and not d["state"]["resolved"]


def test_case_b_requires_high_confidence():
    s = new_state(active_intent=2)
    d = transition(s, raw_intent=7, confidence=0.4, text="thanks")
    assert d["case"] != "B"
    assert not d["state"]["resolved"]


# --- Case C: new substantive intent → becomes active, prior to history ---
def test_case_c_new_substantive_moves_prior_to_history():
    s = new_state(active_intent=2, history=[1])
    d = transition(s, raw_intent=1, confidence=0.8, text="dispute charge")
    assert d["case"] == "C"
    assert d["state"]["active_intent"] == 1
    assert d["state"]["history"] == [1, 2]


def test_case_c_reopens_resolved_thread():
    s = new_state(active_intent=2, resolved=True)
    d = transition(s, raw_intent=1, confidence=0.8, text="dispute")
    assert d["case"] == "C"
    assert not d["state"]["resolved"]


# --- Case D: keyword veto on social prediction (fail-closed) ---
def test_case_d_veto_thanks_refund():
    s = _base()
    d = transition(s, raw_intent=7, confidence=0.9, text="Thanks! Also, where's my refund?")
    assert d["case"] == "D"
    assert d["override"] == "veto"
    assert d["final_intent"] == 9
    assert d["state"]["active_intent"] == 9
    assert not d["state"]["resolved"]


# --- Continuation: inherit prior intent at discounted confidence ---
def test_continuation_inherits_prior_low_conf_slot_filler():
    s = new_state(active_intent=2, history=[1])
    d = transition(s, raw_intent=3, confidence=0.3, text="3467", prior_confidence=0.9)
    assert d["case"] == "continuation"
    assert d["continuation"]
    assert d["override"] == "continuation"
    assert d["final_intent"] == 2
    assert d["confidence"] == 0.45  # discounted
    assert d["state"]["active_intent"] == 2  # unchanged


def test_no_inheritance_when_high_confidence():
    s = new_state(active_intent=2)
    d = transition(s, raw_intent=3, confidence=0.8, text="3467", prior_confidence=0.9)
    assert d["case"] != "continuation"


def test_no_inheritance_without_prior_intent():
    d = transition(_base(), raw_intent=3, confidence=0.3, text="yes", prior_confidence=0.9)
    assert d["case"] != "continuation"


def test_no_inheritance_without_high_conf_prior():
    s = new_state(active_intent=2)
    d = transition(s, raw_intent=3, confidence=0.3, text="yes", prior_confidence=0.4)
    assert d["case"] != "continuation"
