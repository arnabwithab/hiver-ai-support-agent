# ChaseSupport Agent — Evaluation Report (F012)

All numbers traceable: `B` = `make build` stdout 2026-09-09; `G` = golden
jsonl counts; `T` = `make test` stdout; `L` = local eval 2026-09-09
(`src/intent.train_adapt("data/golden/dev")` + `classification_metrics` on the
holdout — method mirrors `src/build.py`, not a committed artifact).
No human ratings collected yet: every unmeasured claim is labeled as such.

## 1. Problem framing + non-goals

Good for ChaseSupport means: route each customer message to one of 9 intents
(§4 taxonomy), draft replies grounded in same-intent brand resolutions
(DM-takeover counts as faithful, design entry 6), and escalate with a written
reason whenever confidence or quality is low — fail-closed (entry 10).
Proof (golden set, baselines, calibrated judge) outranks system polish.

Non-goals (design §14, add-when in brackets): per-criterion judges (budget
allows); orchestration framework (graph gains real cycles); multilingual
support (non-English brand data); live A/B proof (production traffic);
fine-tuned local drafter (API dependence must go).

## 2. Results vs both baselines (holdout n=60: 36 real / 12 boundary / 12 adversarial `G`)

| system | accuracy | macro-F1 | source |
|---|---|---|---|
| majority (predicts dev-majority `card_delivery` + canned reply) | 0.167 | 0.032 | `B` |
| TF-IDF retrieval draft (fit on dev n=140) | 0.567 | 0.532 | `B` |
| ours, raw classifier | 0.550 | 0.508 | `L` |
| ours, final (after state machine) | 0.550 | 0.508 | `L` |

Honest headline: **we beat the trivial baseline ~3× but lose to the simple
one** (−0.017 acc, −0.024 macro-F1). Stratum split (`L`): real 0.250 (9/36),
boundary 1.000 (12/12), adversarial 1.000 (12/12). Calibration: gate threshold
T=0.442 fit on adapt-dev; holdout ECE=0.092 (`L`). Routing (`L`, fresh-state
eval): 56 Case C, 4 Case A, **0 vetoes, 0 inheritance hits — raw = final, so
the state machine contributed nothing measurable on this slice.** Cache repro
(`B`): 5 threads × 2 passes, first-pass misses [0,0], second_pass_calls=0,
live calls 0. Suite: 107 passed (`T`).

Judge calibration: protocol is 3 raters, 15 calibration + ~50 main examples,
pairwise kappas + judge-vs-majority vs mean−2σ bar (design §11). Status:
**not run — both rater sheets are blank (`data/golden/sheets/main.csv`,
`calibration.csv`), so no kappa exists and no judge-vs-golden agreement was
measured either.** The trust claim currently rests only on rubric unit tests.
Unmeasured, labeled as such.

## 3. Top-5 failure modes (all 27 errors are real-stratum; boundary/adversarial: zero)

1. **Continuation fragments classified target-only (27/27 errors).** Gold labels
   carry the thread's substantive intent, but eval feeds only the final inbound
   turn with fresh state — so context + inheritance (design §6) never engage.
   Ex: `g_real_53` (gold card_delivery): "My replacement card hasn't arrived
   yet…" → brand DM request → "Thanks, I'll DM you now." predicted
   billing_charge_dispute. Same shape: `g_real_93`, `g_real_4`, `g_real_12`.
2. **"Thanks, I'll DM you now." → billing_charge_dispute (20 cases).**
   Hypothesis: DM-takeover phrasing correlates with billing threads in dev, and
   the trigram head has no thread memory. Ex: `g_real_50` (gold account_access),
   `g_real_46`/`g_real_6` (gold greeting_smalltalk) — all auto-labeled, all wrong.
3. **"This is still not resolved, please help." → complaint_escalation
   (7 cases).** Anger tokens dominate; gold keeps the underlying intent. Ex:
   `g_real_8` (gold card_delivery, cust posted a phone number, brand refused
   voice channel), `g_real_27`/`g_real_7` (gold account_access), `g_real_68`.
   Decisions here were escalate — right action, wrong intent.
4. **State machine unexercised: 0 overrides on the holdout.** No veto fired, no
   continuation inherited, no Case B close evaluated with real prior state —
   so Case-B wrong-close recall (the silence-toward-user metric) is unmeasured.
   Coverage gap, not an accuracy gap. Unmeasured, labeled as such.
5. **Losing to TF-IDF + uncalibrated judge.** Word-overlap retrieval beats the
   hashing trigram head on this slice, and with no kappa the judge gate is an
   unproven safety claim: ≤3 retries then escalate is tested on fakes only
   (`tests/test_judge.py`, `test_orchestrate.py`).

## 4. What is misleading about my headline number

"0.55 accuracy / 0.51 macro-F1" is misleading four ways: (a) it averages a
0.25 real stratum with two 1.00 crafted strata — workload-representative
accuracy is 0.25, not 0.55; (b) raw = final hides that the state machine was
never actually tested with threaded state; (c) n=60 with per-intent slices of
3–11 makes every per-intent number noise (macro-F1's rare-intent caveat,
design §4); (d) it suggests near-parity with TF-IDF while hiding that the
parity comes from winning the easy crafted slices and collapsing on the real
ones. The number to quote is **real-stratum 9/36**, not 33/60.

## 5. Next-week plan

1. Stateful eval: classify with target + compact context and threaded state so
   inheritance/Case B actually fire; re-score real-stratum accuracy.
2. Collect rater labels (15 calibration + 50 main) → report kappas and
   judge-vs-majority vs the mean−2σ bar; re-tune rubric on mismatches.
3. Error-driven fix for fragments: continuation fallback before the head, plus
   seed terms from the 27 misses; re-tune T on adapt-dev precision–coverage.
4. Measure Case-B wrong-close recall and auto-handle precision at T on threaded
   holdout; run the `make build --live` smoke subset with keys set.

## 6. Decision log (from design §13)

1. ChaseSupport: money/access workload, same-domain Banking77 transfer, real stakes.
2. No router component: state memory + veto, one confusion matrix.
3. No orchestration framework: linear DAG, portable node boundaries.
4. LLM in exactly two nodes (draft, judge) — the verifiable safety claim.
5. Banking77 ceiling vs Twitter truth; the gap is the headline.
6. DM-takeover as faithful grounding, not retrieval failure.
7. Per-turn classification; drift as escalation signal.
8. Single multi-criteria judge call (budget; declared).
9. Kappa vs rater spread (mean−2σ), never raw accuracy.
10. Fail-closed defaults: ambiguity → strict path; retries exhausted → escalate.
11. Case B rule-closes social-after-substantive except when `awaiting_user`.
12. Continuation inheritance as fallback only; freshness by default.
13. Golden hygiene: adapt-dev-only training; 30% locked hold-out.
14. Cache-first repro keyed by (provider, model, prompt hash).
15. Intent 4 rescoped to card_delivery on measured 0.6% volume.
