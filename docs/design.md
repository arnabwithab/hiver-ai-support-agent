# Design: Hiver-style AI support agent for ChaseSupport (Twitter)

## 1. Purpose and scope

Build an AI support agent for a single brand (**ChaseSupport**) on real customer-support
Twitter threads that (a) classifies each incoming customer message into a small intent set,
(b) drafts a reply grounded in how the brand historically resolved similar issues, and
(c) decides auto-handle vs escalate-to-human with a stated reason — then proves it is
trustworthy through a golden evaluation set, baselines, a calibrated judge, and failure
analysis. This document is the complete, self-contained specification: data, taxonomy,
architecture, conversation handling, evaluation, operations, and decisions.

## 2. Background and design methodology

Two external sources shape this design directly:

- **Intent-based support operations (Hiver).** Hiver's operating doctrine is "resolve on
  intent, not scripts": rules handle only what never changes (thank-you auto-close, SLA
  timers, fixed-format routing); an intent layer (categorisation + sentiment triage,
  extract-and-act, agents) handles everything else. Their canonical workload — billing
  disputes, duplicate charges, refunds, login/access issues, order status — informs our
  intent taxonomy (finalised against measured ChaseSupport thread volume, §4), and their
  guardrail model (explicit policy for when AI steps in vs hands
  off, full-context handoff, every correction feeding back) defines our escalation policy
  [1][2].
- **LLM-as-a-judge lifecycle (Netflix; Kong et al.).** A four-phase lifecycle — Birth
  (rationale-annotated benchmark), Training (rubric tuned on mismatches *including
  right-label-wrong-reason errors* via a meta-judge), Deployment (one judge as both gate
  and critic, bounded retries, drop-rather-than-serve), Monitoring (weekly stratified human
  review, judge held to within raters' own spread, drift triggers re-tune behind human
  sign-off with rollback retained) — structures our evaluation and operations [3][4].
  Agreement is measured chance-corrected (Cohen's kappa), never raw accuracy [5][6].

## 3. Data

- **Primary: Customer Support on Twitter** (Kaggle `thoughtvector/customer-support-on-twitter`,
  ~2.8M tweets) [7]. Schema: `tweet_id, author_id, inbound, created_at, text,
  response_tweet_id, in_response_to_tweet_id`. `inbound=True` = customer. Threads are
  reconstructed through the reply-ID chain (≈55% of inbound messages carry reply links,
  so reconstruction is viable for the majority). Known noise: anonymised user mentions
  (`@115712`), `t.co` stubs, truncation, emoji, sarcasm. Raw threads contain customer PII
  (≈1.5% by crude pattern match; true rate higher) — all committed artifacts and all LLM
  prompts use redacted text (§6).
- **Secondary: Banking77** (13k queries, 77 intents) [8] for clean training only, via Kaggle
  mirror (the `datasets`-library script path is deprecated). Used to establish a clean-data
  accuracy ceiling; all deployment claims are measured on noisy Twitter threads.
- **Working subsample:** ChaseSupport slices (~9k brand replies plus their inbound threads),
  small enough to reproduce headline results in under 15 minutes with an API key set.

## 4. Intent taxonomy (9, Hiver-mapped, data-validated)

| # | intent | Hiver analogue | typical action |
|---|---|---|---|
| 1 | billing_charge_dispute | billing dispute / duplicate charge | verify → DM takeover |
| 2 | refund_request | refund pipeline | eligibility → DM takeover |
| 3 | account_access | login / credentials | troubleshoot or verify |
| 4 | card_delivery | order/shipment status | card-mail lookup → update |
| 5 | card_product_question | product/plan question | answer from exemplars |
| 6 | complaint_escalation | churn-risk / sentiment-flagged | senior queue, priority |
| 7 | praise_thanks | thank-you (rule-closable) | acknowledge |
| 8 | greeting_smalltalk | greeting (rule-closable) | greet |
| 9 | other | long-tail fallback | clarify or escalate |

Intents 7–8 are the social lane: social-only threads get a per-draft-judged LLM ack (§5);
social-after-substantive is rule-closed (§6, Case B).

**Data validation (n=4,300 ChaseSupport inbound, keyword probe).** Measured shares:
card_product_question 17.8%, praise_thanks 12.6%, billing_charge_dispute 6.2%,
account_access 4.6%, refund_request 1.8%, complaint_escalation 1.4%, greeting_smalltalk
1.0% (strict pattern; true share higher), order/delivery terms 0.6% — and those hits are
overwhelmingly *card mail* ("replacement card hasn't arrived", "rush delivery for my new
card"), not e-commerce orders. Intent 4 is therefore scoped as **card_delivery**. Rule: any
intent below ~1% measured share in the final golden sample merges into `other`, and the
merge is reported. Per-intent golden counts are published with confidence intervals;
macro-F1 carries the caveat that rare-intent slices are thin.

**Brand choice.** ChaseSupport was selected over higher-volume alternatives (Tesco,
AmericanAir, telecom brands) on three grounds: (i) its workload matches Hiver's
money-and-access profile; (ii) Banking77→finance-brand is same-domain transfer
(banking→banking), keeping the clean-to-noisy story credible; (iii) genuine escalation
stakes — lockouts, money movement, customers posting raw PII publicly.

## 5. Architecture

```
                    ┌─────────────────────────────────────────────────┐
                    │              INCOMING CUSTOMER MESSAGE          │
                    │        (+ thread_history via reply-ID chain)    │
                    └───────────────────────┬─────────────────────────┘
                                            ▼
                    ┌─────────────────────────────────────────────────┐
                    │ 1. THREAD BUILDER (no LLM)                      │
                    │    walk reply chain; order turns; emit target   │
                    │    + context (prev customer msg + last brand    │
                    │    reply, ~300 chars each); load thread state   │
                    └───────────────────────┬─────────────────────────┘
                                            ▼
                    ┌─────────────────────────────────────────────────┐
                    │ 2. EMBED + CLASSIFY (no LLM)                    │
                    │    frozen embedding → linear head → 9 intents   │
                    │    + calibrated confidence p                    │
                    └───────────────────────┬─────────────────────────┘
                                            ▼
                    ┌─────────────────────────────────────────────────┐
                    │ 3. GATE + STATE APPLY (no LLM)                  │
                    │    a. keyword veto (§6, Case D)                 │
                    │    b. p < T → inherit-or-escalate (§6)          │
                    │    c. transition rules A–D (§6)                 │
                    └───────┬─────────────────────────┬───────────────┘
              close │       │ draft                   │ escalate/info
                    ▼       ▼                         ▼
        ┌───────────────────┐             ┌─────────────────────────┐
        │ 4e. CANNED ACK +  │             │ intent in {praise,      │
        │ RESOLVE (no LLM)  │             │ greeting}?              │
        └───────────────────┘             └───────┬─────────┬───────┘
                                            YES  │         │ NO
                                                 ▼         ▼
                                        ┌────────────┐ ┌──────────────────────┐
                                        │ 4b. DRAFT_ │ │ 4c. RETRIEVE (no LLM)│
                                        │ FREE [LLM] │ │ top-k same-intent    │
                                        └─────┬──────┘ │ resolutions+strategy │
                                              │        └──────────┬───────────┘
                                              │                   ▼
                                              │        ┌──────────────────────┐
                                              │        │ 4d. DRAFT_GROUNDED   │
                                              │        │ [LLM] intent+history │
                                              │        │ + exemplars+strategy │
                                              │        └──────────┬───────────┘
                                              └──────────┬────────┘
                                                         ▼
                    ┌─────────────────────────────────────────────────┐
                    │ 5. JUDGE [LLM] — gate + critic                  │
                    │    one call, rubric + rationale per criterion:  │
                    │    groundedness / tone_policy /                 │
                    │    escalation_correctness (+ shift-aware check) │
                    └───────────────────────┬─────────────────────────┘
                                            ▼
                                 ┌──────────┴──────────┐
                            PASS │                     │ FAIL (+critique)
                                 ▼                     ▼
                    ┌───────────────────┐   ┌─────────────────────────┐
                    │ 6a. SERVE         │   │ 6b. RETRY (≤3, critique │
                    │ update thr. state │   │ appended) else 6c.      │
                    └───────────────────┘   │ ESCALATE w/ rationale   │
                                            └─────────────────────────┘
                    ┌─────────────────────────────────────────────────┐
                    │ 7. MONITOR (offline, human-in-the-loop, §11)    │
                    └─────────────────────────────────────────────────┘
```

**LLM boundary (exhaustive).** The LLM runs in exactly two nodes: drafting (`4b`/`4d`)
and judging (`5`, whose critique output is reused). Everything else is deterministic code.
Verification: the LLM client is invoked from exactly two call sites. There is no separate
router component: routing survives only as thread-state memory plus a keyword veto (§6).
Every routing decision is logged as (raw classifier prediction → veto/inheritance/Case
override → final label); evaluation reports both the raw and the final confusion matrices
plus override counts (veto triggers, inheritance hits, Case B closes), so no error is
hidden inside the state machine.

## 6. Conversation handling and thread-state machine

Threads are reconstructed from reply-ID chains, never assumed. Classification input is the
target customer message plus compact context; thread position is a feature (mid-thread
fragments such as `Thanks` or `I did` are unclassifiable alone). Retrieval is restricted
to same-intent history; drafting receives target + context + exemplars + strategy tag.

Thread state (minimal; no session manager, no timeouts — threads die by abandonment):

```python
state = {
  "active_intent": 1 | 2 | … | None,  # last substantive intent
  "history": [...],                   # every substantive intent, in order
  "awaiting_user": bool,              # brand asked a question last turn
  "resolved": bool,                   # set by Case B close
}
```

- **Case A — social (7/8), no prior substantive intent.** Pure hello/thanks thread:
  free-draft ack through the per-draft judge (§5).
- **Case B — social (7/8) after a substantive intent.** Discard the work (no retrieval, no
  grounded draft, no full judge): deterministic canned ack, mark resolved. Exception: if
  `awaiting_user` is set, "thanks" may signal compliance rather than farewell — ack but
  keep the thread open. Case B additionally requires high-confidence social plus a
  keyword-veto pass, since misclassification here means silence toward a user.
- **Case C — new substantive intent.** It becomes `active_intent`; predecessors stay in
  `history[]` as drafter context. Retrieval serves the *new* intent; the draft must
  acknowledge any still-open prior intent (judge's shift-aware groundedness check).
  Sustained anger across a shift adds escalation weight.
- **Case D — keyword veto.** A social prediction co-occurring with money/account/action
  terms or `?` (e.g. "Thanks! Also, where's my refund?") falls through to informational.
  Fail-closed.
- **Continuation fallback.** Low-confidence slot-fillers (`yes`, `3467`) with a prior
  high-conf intent and no drift signals inherit it at discounted confidence, flagged
  `continuation=true`. Sticky-as-fallback only; fresh per-turn classification stays the
  default so topic changes never go stale.
- **PII redaction.** Before any text reaches an LLM prompt or a committed artifact, redact
  account/SSN digit patterns, phone numbers, zips in PII contexts, and addresses. The
  judge's `tone_policy` criterion includes a PII-leak check: any draft echoing customer
  PII fails.

## 7. Intent model (no LLM)

Frozen sentence embedding plus linear head. **Phase A:** train on Banking77 to prove the
architecture and publish the clean-data ceiling. **Phase B:** adapt to the 9 Chase intents
via weak supervision (keyword seeds + same-intent thread expansion) tuned on a 70%
adapt-dev slice of the golden set. The remaining **30% is a locked hold-out**, never
touched during training, calibration, or threshold-setting; all reported metrics come from
it. Enforcement: the training entrypoint accepts only the dev-slice path, so hold-out
contamination is a code error, not a discipline error. The expected adapt-dev→hold-out and
clean→noisy drops are the report's honest headline. Probabilities are calibrated
(Platt/temperature scaling on adapt-dev; reliability diagram shipped); the gate threshold
`T` is set by the human judge from the adapt-dev precision–coverage curve.

## 8. Retrieval grounding

Historical brand replies are clustered *within* each intent (embed + k-means, small k,
hand-inspected) to yield named **response strategies** (e.g. `request_DM_plus_verify`,
`cite_policy`, `promise_callback`), each keeping 2–3 exemplars. Serve time injects top-k
same-intent exemplars plus the strategy tag as hard context. Declared limitation: brand
replies skew heavily toward DM-takeover deflection, so faithful grounding means the draft
*requests takeover rather than inventing an answer* — the groundedness criterion rewards
exactly this.

## 9. Judge and revision loop

One LLM call per draft; multi-criteria rubric (groundedness, tone_policy incl. PII-leak,
escalation-correctness), every verdict with a written rationale. Drafter and judge run on
different providers: **drafter = Groq-hosted open model** (volume role: 250 examples ×
retries needs throughput), **judge = Gemini** (reasoning role: rubric adherence +
rationales). Cross-provider separation exceeds the different-model requirement
(self-preference bias); both are pinned and recorded in every artifact, and artifacts flag
judge-guided retries. The judge is tuned on
judge–human mismatches **including right-label-wrong-reason errors** [3]. In deployment it
serves as **gate and critic**: failures append the critique to the draft prompt for ≤3
retries, then **drop (escalate) rather than serve** — the escalation reason is the judge's
rationale, reused as the human handoff note. Deterministic Case-B canned acks carry no LLM
content and are explicitly outside the gate.

## 10. Evaluation

- **Golden set (150–250):** Netflix Birth composition at a fixed stratum mix — 60% real
  sampled threads (sampling frame: ChaseSupport inbound, reply-linked chains preserved,
  stratified by week), 20% boundary cases near the auto/escalate line, 20% expert-crafted
  adversarial cases. Workload-representative accuracy is reported on the 60% real stratum;
  adversarial/boundary slices are reported separately, so crafted difficulty can neither
  inflate nor deflate the headline. Every escalate/fail label carries a written rationale;
  the author adjudicates all of them. 70/30 adapt-dev/locked-hold-out split (§7); all
  headline numbers come from the hold-out.
- **Baselines:** trivial (majority intent + canned reply) and simple (TF-IDF retrieval
  draft). Unbeaten slices become failure analysis.
- **Metrics:** intent accuracy/macro-F1 on raw *and* final labels plus override counts (§5),
  per-intent counts with CIs, auto-handle precision at the operating threshold, judge
  specificity (fail-recall) as the trust metric — every metric sliced by Case A–D /
  continuation / veto / shift flags — plus a Case-B wrong-close recall metric (a wrong
  close is silence toward a user). Judge–human agreement in **Cohen's kappa** with bootstrap
  CI: pairwise rater kappas plus judge-vs-majority, with the judge held to within the
  raters' own spread (mean − 2σ) across 3 raters on a ~50-example subset (§11).
- **Mandatory report sections** (per assignment brief): problem framing + non-goals, results
  vs both baselines, top-5 failure modes with real examples, "what is misleading about my
  headline number", next-week plan, 10–15 decision log.

## 11. Monitoring and human-in-the-loop operations

The author is the standing human judge across all phases: defines "good", supplies and
adjudicates golden rationales, sets the gate threshold and drop/serve policy, and signs
off every rubric change before it ships, with the previous rubric retained for rollback.
For the take-home, monitoring ships as (i) the standing operating plan above — weekly
stratified review (served / revised / escalated, new-pattern weighted), drift event
defined as the judge falling below the rater-spread band on any metric–criterion pair,
re-tune on the augmented benchmark — and (ii) one **simulated drift check**: the frozen
judge re-run on a later time-slice of the subsample with agreement deltas reported. With
no production traffic there are no true weeks; the simulation exercises the same code path
(stratify → label → kappa → drift verdict). Standing review additionally asks whether the
*rubric itself* is incomplete — drift detection aligns the judge to the rubric; only human
review aligns the rubric to reality [3].

**Rater protocol (3 raters, author included; odd number ⇒ majority always resolves).**
Shared guideline first (intent definitions + auto/escalate policy). (1) Calibration: 15
examples, blind independent labels (intent + auto/escalate + rationale on escalate), then
a 30-min reconciliation call to patch the guideline; second 10-example round only if mean
pairwise kappa < 0.7 — the final number is reported either way. (2) Main: ~50-example
subset from the locked hold-out; each rater independently labels intent + auto/escalate
with rationales, then pass/fail-verdicts drafts blind (no model verdicts shown, randomised
order). Majority = ground truth; report pairwise kappas and judge-vs-majority against the
mean−2σ bar. Budget ≈ 1h calibration + 2h main per rater, async except the reconciliation
call.

## 12. Reproducibility and budget

Two OpenAI-compatible endpoints, no code change between them: Groq (`GROQ_API_KEY`,
drafter) natively, Gemini via its OpenAI-compatible endpoint (`GEMINI_API_KEY` +
`GEMINI_BASE_URL`, judge). Temperature 0, provider + model IDs recorded in every artifact.
Every LLM artifact (drafts, critiques, verdicts) is cached keyed by (provider, model ID,
prompt hash): headline numbers reproduce from cache, plus a small live smoke subset proving the
key path works end-to-end. At 15–30 free-tier RPM a from-scratch 250-example × retry-loop
run cannot fit 15 minutes — the cache is what makes the repro honest. The pipeline fails
loudly without a key (one system, not two). Budget controls: single multi-criteria judge
call, retry cap 3 — the documented simplification against Netflix's per-criterion judges.

## 13. Decision log

1. ChaseSupport: Hiver-like money/access workload; same-domain Banking77 transfer; real
   escalation stakes.
2. No router component: routing as state memory + veto; one confusion matrix.
3. No orchestration framework: linear DAG with one branch and one retry edge; node
   boundaries kept portable.
4. LLM in exactly two nodes (draft, judge): the verifiable safety claim.
5. Banking77 clean ceiling vs Twitter deployment truth; the gap is the headline.
6. DM-takeover as faithful grounding, not retrieval failure.
7. Per-turn classification; thread drift as escalation signal.
8. Single multi-criteria judge call (budget; declared).
9. Kappa: pairwise rater kappas + judge-vs-majority against the mean−2σ bar over 3
   raters (no raw accuracy, no fixed thresholds).
10. Fail-closed defaults: ambiguity → strict path; low confidence → escalate; retries
    exhausted → escalate, never serve.
11. Human owns thresholds, rubrics, ship sign-off; old rubrics retained.
12. Case B rule-closes social-after-substantive (no LLM) except when `awaiting_user`.
13. Shifts preserve history as context with shift-aware judging; cross-shift anger escalates.
14. Continuation inheritance as fallback only; freshness by default.
15. Golden hygiene: weak-supervision tuning on adapt-dev only; 30% locked hold-out for all
    headline numbers; training entrypoint accepts only the dev slice.
16. PII redaction before any LLM prompt or committed artifact; PII-leak is a judge
    criterion.
17. Cache-first repro: every LLM artifact cached by (model, prompt hash); live smoke
    subset only.
18. Judge model ≠ drafter model; judge-guided retries flagged in artifacts.
19. Intent 4 rescoped to card_delivery on measured volume (0.6% order terms, all card
    mail); sub-1% intents merge into `other`.
20. Dual-provider split: Groq drafts (throughput), Gemini judges (rubric reasoning) —
    cross-provider separation as the self-preference guard.

## 14. Non-goals (with add-when)

Per-criterion judges (budget allows); orchestration framework (graph gains real cycles);
multilingual support (non-English brand data); live A/B proof (production traffic);
fine-tuned local drafter (API dependence must go). Key risks: clean-to-noisy transfer drop;
thin DM-heavy retrieval clusters; silence-on-misclassification in Case B, guarded by the
confidence + veto requirement and measured by wrong-close recall; redaction-pattern recall
on novel PII formats (residual).

## 15. References

[1] Hiver, "Agentic omnichannel customer service platform,"
https://www.hiverhq.com/ (example workloads: billing disputes, duplicate charges, refunds,
login/API-credential issues; guardrails, observability, feedback loop).
[2] Hiver blog, "Rule-based automations are holding your support team back,"
https://hiverhq.com/blog/rule-vs-intent-based-ai-workflows (rules vs intent layer; triage,
extract-and-act, agents; thank-you auto-close).
[3] Kong et al., "The Lifecycle of LLM-as-a-Judge: Building, Aligning, and Monitoring at
scale," Netflix Technology Blog, Sep 2026 (four-phase lifecycle; RART reasoning alignment;
gate+critic deployment; weekly stratified review; rater-spread bar; human sign-off and
rollback). Research paper: https://arxiv.org/html/2608.18300v2
[4] Alessio et al., "Evaluating Netflix Show Synopses with LLM-as-a-Judge," Netflix
Technology Blog, Apr 2026 (calibration rounds; binary over Likert rubrics;
model-in-the-loop golden consensus).
[5] Galileo, "How to Calibrate Your LLM Judge With Human Annotations," 2026
(Cohen's kappa vs raw agreement; stratified sampling; anchor examples).
[6] Arize, "How to measure human-LLM judge alignment" (sample sizing; bootstrapped CIs;
evaluator versioning).
[7] ThoughtVector, "Customer Support on Twitter" (Kaggle; ~2.8M tweets, reply-linked
threads).
[8] PolyAI, "banking77" (13k queries, 77 intents; Kaggle mirror used as the `datasets`
script path is deprecated).
