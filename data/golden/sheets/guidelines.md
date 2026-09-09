# Rater guidelines (§11)

## Intents (9)
billing_charge_dispute, refund_request, account_access, card_delivery,
card_product_question, complaint_escalation, praise_thanks, greeting_smalltalk, other.
Sub-1% intents merge into other.

## Auto vs escalate
Auto-handle only high-confidence substantive threads with a grounded draft path;
escalate on low confidence, PII present, anger/shift, veto terms, or any doubt
(fail-closed). Every escalate needs a written rationale.

## Protocol
1. Calibration: 15 examples, blind independent labels (intent + auto/escalate +
rationale on escalate), then reconcile and patch this page. Second 10-example
round only if mean pairwise kappa < 0.7.
2. Main: ~50 hold-out examples; label intent + auto/escalate with rationales,
then pass/fail drafts blind (no model verdicts shown, randomised order).
Majority = ground truth; judge must clear the mean−2σ rater-spread bar.
