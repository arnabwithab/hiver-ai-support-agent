# ChaseSupport Agent — Evaluation Report (F012)

All numbers traceable: `B` = `make build` stdout 2026-09-09; `G` = golden
jsonl counts; `T` = `make test` stdout; `L` = local eval 2026-09-09
(`src/intent.train_adapt("data/golden/dev")` + `classification_metrics` on the
holdout — method mirrors `src/build.py`, not a committed artifact); `L2` =
same method re-run 2026-09-09 with ST embeddings + class-weighted head.
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
| ours, raw classifier (ST embeddings) | 0.600 | 0.591 | `L2` |
| ours, final (after state machine) | 0.600 | 0.591 | `L2` |

Honest headline: **we now beat TF-IDF** (+0.033 acc, +0.059 macro-F1 —
embeddings closed the gap the hashing head left). Stratum split (`L2`):
real 0.333 (12/36), boundary 1.000 (12/12), adversarial 1.000 (12/12).
Calibration: gate threshold T=0.473 fit on adapt-dev (`L2`; ECE on the new
head unmeasured — recompute before trusting T). Routing (`L2`, fresh-state
eval): 56 Case C, 4 Case A, **0 vetoes, 0 inheritance hits — raw = final, so
the state machine contributed nothing measurable on this slice.** Cache repro
(`B`): 5 threads × 2 passes, first-pass misses [0,0], second_pass_calls=0,
live calls 0. Suite: 118 passed (`T`). Sink-error audit (`L2`): 5 residual
true-2/4→5 errors, mean confidence 0.565, none above 0.8 — the gate already
catches them, so multi-candidate routing is rejected for now; 99/344 other
errors exceed 0.8 (margin signal reserved as future work).

Judge calibration: protocol is 3 raters, 15 calibration + ~50 main examples,
pairwise kappas + judge-vs-majority vs mean−2σ bar (design §11). Status:
**2 raters, one human** — the author labeled all 65 blind threads via
`rate.md`; r1 is a persona-A model rater (strict QA). Filled sheets in
`data/golden/sheets/filled/` (v2). Calibration intent kappa 0.920 ≥ 0.7,
so no second round was needed. Full-panel: **intent kappa 0.928 (n=65),
auto/escalate kappa 1.000, draft-verdict agreement 0.840 (42/50).**
Disagreements are interpretable, not noise: the "whatever" threads
(human complaint_escalation vs r1 other ×3) and one sarcastic-login
thread split the anger-vs-substance line opposite ways; on drafts the
human failed 3 verbatim-copy fee replies r1 passed, while r1 failed 5
the human passed. Auto/escalate agreement is perfect — both raters
escalate identically everywhere, so the gate threshold carries no
rater-explained variance. Judge-vs-rater on 50/50 drafts (rubric v2 incl.
anti-parroting rule, `gemini-3.5-flash` — 2.5-flash deprecated for new
keys, lite proven unusable with 1.00 pass rate): **agreement 0.76 vs
human, 0.60 vs r1; fail-recall 0.40 vs human fail set (6/15), 0.18 vs
r1 (3/17).** The gate functions on the stronger model — it fails
verbatim-copy fee drafts and PII-ignoring replies — but stays stricter
than both raters in places (false alarms on 3 greeting drafts both
raters passed) while missing most rater fails. Verdict: shippable as an
escalate-happy gate with human review of fails, not as autonomous
pass-through. Model recorded per artifact.
Caveat: 2 raters give no majority on splits and no rater-spread bar
(needs 3); treat kappas as alignment evidence, not the full §11 bar.

## 3. Top-5 failure modes (all 24 errors are real-stratum; boundary/adversarial: zero)

1. **Continuation fragments classified target-only (24/24 errors).** Gold labels
   carry the thread's substantive intent, but eval feeds only the final inbound
   turn with fresh state — so context + inheritance (design §6) never engage.
   Ex: `g_real_53` (gold card_delivery): "My replacement card hasn't arrived
   yet…" → brand DM request → "Thanks, I'll DM you now." predicted
   card_product_question. Same shape: `g_real_93`, `g_real_83`, `g_real_73`.
2. **"Thanks, I'll DM you now." → card_product_question (17 cases).**
   DM-takeover phrasing now lands in the product bucket (with hashing it was
   billing — the sink moved with the features, the shape didn't). Ex: `g_real_50`
   (gold account_access), `g_real_46`/`g_real_6` (gold greeting_smalltalk),
   `g_real_92`/`g_real_12` (gold refund_request) — all auto-labeled, all wrong.
3. **"This is still not resolved, please help." → complaint_escalation
   (7 cases).** Anger tokens dominate; gold keeps the underlying intent. Ex:
   `g_real_8` (gold card_delivery, cust posted a phone number, brand refused
   voice channel), `g_real_27`/`g_real_7` (gold account_access), `g_real_68`.
   Decisions here were escalate — right action, wrong intent.
4. **State machine unexercised: 0 overrides on the holdout.** No veto fired, no
   continuation inherited, no Case B close evaluated with real prior state —
   so Case-B wrong-close recall (the silence-toward-user metric) is unmeasured.
   Coverage gap, not an accuracy gap. Unmeasured, labeled as such.
5. **Beating TF-IDF on averages, uncalibrated judge.** The averages flipped,
    but the judge gate is still an unproven safety claim: ≤3 retries then
    escalate is tested on fakes only (`tests/test_judge.py`,
    `test_orchestrate.py`), and with no kappa the trust metric is missing.

## 4. What is misleading about my headline number

"0.60 accuracy / 0.59 macro-F1" is misleading four ways: (a) it averages a
0.33 real stratum with two 1.00 crafted strata — workload-representative
accuracy is 0.33, not 0.60; (b) raw = final hides that the state machine was
never actually tested with threaded state; (c) n=60 with per-intent slices of
3–11 makes every per-intent number noise (macro-F1's rare-intent caveat,
design §4); (d) it suggests victory over TF-IDF while hiding that the win
comes from the easy crafted slices plus a real stratum where all 24 errors
are two template fragments. The number to quote is **real-stratum 12/36**,
not 36/60.

## 5. Next-week plan

1. Stateful eval: classify with target + compact context and threaded state so
   inheritance/Case B actually fire; re-score real-stratum accuracy.
2. Collect rater labels (15 calibration + 50 main) → report kappas and
   judge-vs-majority vs the mean−2σ bar; re-tune rubric on mismatches.
3. Error-driven fix for fragments: continuation fallback before the head, plus
   seed terms from the 24 misses; re-tune T on adapt-dev precision–coverage.
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

## 7. Phase A real-data ceiling (F013–F014, run 2026-09-09)

`train_phase_a('data/raw/banking77/train.csv')`, label_text → 9-way map
(`src/intent.BANKING77_MAP`, unlisted → 9), default **50 epochs**.
F014 replaced the hashing-trigram stand-in with frozen
`all-MiniLM-L6-v2` (384-dim, L2-normalised, never fine-tuned) and
appended 500+500 mined cross-brand social rows (labels 7/8, veto-filtered,
`src/subsample.mine_social`, seeded) — social needs no brand context.
Full retrain wall 218 s.

| split | n | accuracy | macro-F1 | source |
|---|---|---|---|---|
| train (in-sample) | 10003 | 0.486 | 0.402 | `R` (unweighted, hashing) |
| test (hashing, unweighted) | 3080 | 0.507 | 0.419 | `R` |
| test (hashing, class-weighted) | 3080 | 0.559 | 0.485 | `R2` |
| test (embeddings + social) | 3080 | **0.887** | **0.786** | `R3` |

`R` = run stdout 2026-09-09 (`train_phase_a` + `classification_metrics`
on mapped test). Mapped test counts `R`: {1: 480, 2: 120, 3: 400,
4: 280, 5: 760, 6: 120, 9: 920}; train `R`: {1: 1894, 2: 477,
3: 1150, 4: 815, 5: 2240, 6: 276, 9: 3151}. Intents 7/8 have
**zero coverage in train and test** (Banking77 carries no social
intents — asserted in `tests/test_intent.py`, reported gap not a bug).
Per-class test F1 `R` (unweighted): 1: 0.611, 2: 0.229, 3: 0.678, 4: 0.255,
5: 0.543, 6: 0.239, 9: 0.374 — rare money intents (2/4/6) collapse
under the hashing-trigram head. Mirror quirk: `dev.csv` is
byte-identical to `test.csv`; train ∩ test overlap is 0/3080, so the
ceiling stands.

Class-weighted SGD (`_train_head(balanced=True)`, per-class gradient
scale N/K·n_c, no rows dropped — undersampling rejected: it would discard
~80% of data and starve the diverse `other` class). `R2` per-class
prec/rec/F1: 1: 0.651/0.637/0.644, 2: 0.774/0.200/0.318,
3: 0.654/0.710/0.681, 4: 0.803/0.204/0.325, 5: 0.434/0.938/0.593,
6: 0.744/0.242/0.365, 9: 0.788/0.335/0.470 — every minority recall
improves (2: 0.133→0.200, 4: 0.150→0.204, 6: 0.142→0.242). Residual
error is class 5 as sink (true-2 → 83/120 predicted 5; true-4 →
180/280 predicted 5): the 19-intent product bucket plus trigram overlap
(`top_up_reverted`→2 vs `pending_top_up`→9) exceeds what reweighting a
frozen hashing embedding can split — needs the real sentence embedding
or a mapping rethink, not more balancing.

`R3` per-class prec/rec/F1 (embeddings + social, T=0.500): 1: 0.808/
0.946/0.871, 2: 0.980/0.817/0.891, 3: 0.955/0.963/0.959,
4: 0.844/0.950/0.894, 5: 0.941/0.864/0.901, 6: 0.900/0.900/0.900,
9: 0.912/0.829/0.869. The class-5 sink is gone (refund recall
0.200→0.817, card-delivery 0.204→0.950): the boundary confusion was a
feature problem, not a weighting problem — real embeddings separated
what reweighting hashed trigrams could not. Lesson recorded: the
zero-dependency hashing stand-in cost 0.30 macro-F1 and should never
have survived first contact with real data.

Classes 7/8 (seeded 400-train/100-eval split of the 1,000 mined rows,
`subsample.split_social`, eval texts never trained on): heldback
prec/rec/F1 = 7: 0.969/0.310/0.470, 8: 0.588/0.970/0.732 (`R4`).
Thanks is conservative (predicted rarely, right 97% of the time);
greetings over-fire (catches 97%, precision 0.588 — mostly thanks
misread as greeting plus leakage into 1/9). Synthetic probes agree
(3/3 both). Banking77 carries no social rows, so this heldback is the
only real 7/8 measurement. Prevalence on real threads: ChaseSupport
19.1% thanks / 6.2% greeting (n=1,974 attributed inbound), Tesco
23.6%/10.7%, Spotify 22.0%/3.6% (single-hop attribution, 64%
unattributed, weak labels not gold).

Chase subsample (`src/subsample.py`, fixpoint over `twcs.csv`, 5 passes
to convergence, 33 s): **6887 threads / 19110 rows** written to
gitignored `data/raw/chase/chase_threads.jsonl` (turns only, unlabeled).
Weak-label distribution over 10059 inbound texts `R`:
{1: 609, 2: 55, 3: 238, 4: 1299, 5: 561, 6: 463, 7: 898, 8: 1014,
9: 4922} — 49% fall through to `other`, the Phase B gap in one number.
