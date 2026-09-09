"""F009: metrics and agreement. Design §10. Pure local math — stdlib only, no LLM.

Two concerns live here:
  * F009-1  classification metrics over one golden-adjudicated decision per
            EvalRow (accuracy / macro-F1 on raw AND final labels, override
            counts, per-intent counts with normal-approx CIs, auto-handle
            precision at the operating threshold, judge specificity /
            fail-recall, Case-B wrong-close recall), every metric sliceable by
            case / continuation / veto flags.
  * F009-2  rater agreement: Cohen's kappa, bootstrap CIs, pairwise rater
            kappas and the judge-vs-majority vs mean−2σ rater-spread bar.

Labels are opaque (str or int — the state machine emits ints 1-9, golden files
may carry names); anything hashable works.
"""

from __future__ import annotations

import random
import statistics
from collections import Counter
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EvalRow:
    """One routing decision with its golden adjudication.

    Label semantics mirror state.py's decision dict: ``true_label`` is the
    golden intent, ``raw_pred`` the classifier output and ``final_label`` the
    post-state-machine label (override applied). ``closed`` marks a Case-B
    rule-close (silence, no draft served). Judge fields are only set on
    drafted rows; ``conf`` is None for deterministic rule-closes.
    """

    true_label: object
    raw_pred: object
    final_label: object
    case: str = ""
    continuation: bool = False
    veto: bool = False
    auto: bool = False
    closed: bool = False
    conf: float | None = None
    gold_auto: bool | None = None
    judge_fail: bool | None = None
    gold_fail: bool | None = None
    gold_needs_reply: bool | None = None


# --- F009-1: classification and routing metrics --------------------------------


def accuracy(true, pred):
    if not true:
        return 0.0
    return sum(1 for t, p in zip(true, pred) if t == p) / len(true)


def _per_class(true, pred, labels):
    matrix = confusion_matrix(true, pred)  # single pass; derive tp/fp/fn from it
    classes = {}
    for label in labels:
        tp = matrix[label][label]
        fp = sum(matrix[t][label] for t in labels) - tp
        fn = sum(matrix[label][p] for p in labels) - tp
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        classes[label] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "support": tp + fn,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }
    return classes


def _labels(true, pred):
    return sorted(set(true) | set(pred))


def classification_metrics(true, pred):
    """Per-class precision/recall/F1 plus accuracy and macro-F1 over the
    union of observed labels (zero-denominator cells read 0.0)."""
    labels = _labels(true, pred)
    classes = _per_class(true, pred, labels)
    macro = sum(c["f1"] for c in classes.values()) / len(labels) if labels else 0.0
    return {
        "n": len(true),
        "labels": labels,
        "classes": classes,
        "accuracy": accuracy(true, pred),
        "macro_f1": macro,
    }


def macro_f1(true, pred):
    return classification_metrics(true, pred)["macro_f1"]


def confusion_matrix(true, pred):
    """Nested {true_label: {pred_label: count}} over the union of labels."""
    labels = _labels(true, pred)
    matrix = {t: {p: 0 for p in labels} for t in labels}
    for t, p in zip(true, pred):
        matrix[t][p] += 1
    return matrix


def override_counts(rows):
    """Veto triggers, inheritance (continuation) hits and Case-B closes (§5)."""
    return {
        "veto": sum(1 for r in rows if r.veto),
        "inheritance": sum(1 for r in rows if r.continuation),
        "case_b_closes": sum(1 for r in rows if r.case == "B" and r.closed),
    }


def slice_rows(rows, *, case=None, continuation=None, veto=None):
    """Rows matching every supplied filter value (None = leave unfiltered)."""
    active = {"case": case, "continuation": continuation, "veto": veto}
    active = {k: v for k, v in active.items() if v is not None}
    return [r for r in rows if all(getattr(r, k) == v for k, v in active.items())]


def proportion_ci(k, n, z=1.96):
    """Normal-approximation CI on a proportion k/n. Returns (None, None) for
    an empty denominator. ponytail: normal approx per scope; Wilson if n is
    ever small enough to matter."""
    if n <= 0:
        return (None, None)
    p = k / n
    se = (p * (1 - p) / n) ** 0.5
    return (p - z * se, p + z * se)


def per_intent_table(true, z=1.96):
    """Counts and share-CIs per intent label (§4: golden counts + CIs)."""
    n = len(true)
    if n == 0:
        return []
    table = []
    for label, count in sorted(Counter(true).items()):
        lo, hi = proportion_ci(count, n, z)
        table.append({"label": label, "count": count, "share": count / n, "ci_lo": lo, "ci_hi": hi})
    return table


def auto_handle_precision(rows, threshold=None):
    """Precision of the auto-handle (serve) decision at the operating point.

    Denominator: rows the system auto-handled with a golden verdict — cut to
    calibrated ``conf >= threshold`` when a threshold is given. Deterministic
    rule-closes carry conf=None and are therefore outside the threshold band;
    their safety is measured by wrong_close_recall instead. None when no row
    qualifies."""
    denom = [
        r
        for r in rows
        if r.auto
        and r.gold_auto is not None
        and (threshold is None or (r.conf is not None and r.conf >= threshold))
    ]
    if not denom:
        return None
    return sum(1 for r in denom if r.gold_auto) / len(denom)


def judge_specificity(rows):
    """Judge fail-recall: of drafts the golden says should not be served, the
    share the judge actually failed. The gate's trust metric. None when no
    gold-fail row was judged."""
    fails = [r for r in rows if r.gold_fail and r.judge_fail is not None]
    if not fails:
        return None
    return sum(1 for r in fails if r.judge_fail) / len(fails)


def wrong_close_recall(rows):
    """Case-B wrong-close recall: a wrong close is silence toward a user (§14).

    Among turns the golden adjudicated as needing a real reply (so a
    rule-close would be silence), the share the system did NOT close. None
    when no such turn exists."""
    at_risk = [r for r in rows if r.gold_needs_reply]
    if not at_risk:
        return None
    return sum(1 for r in at_risk if not r.closed) / len(at_risk)


def evaluate(rows, *, auto_threshold=None, z=1.96):
    """Full F009-1 report over rows: raw + final classification metrics, both
    confusion matrices, override counts, per-intent CIs and the three trust
    metrics. Slice first via slice_rows for case/flag breakdowns."""
    true = [r.true_label for r in rows]
    raw = [r.raw_pred for r in rows]
    final = [r.final_label for r in rows]
    return {
        "n": len(rows),
        "accuracy_raw": accuracy(true, raw),
        "accuracy_final": accuracy(true, final),
        "macro_f1_raw": macro_f1(true, raw),
        "macro_f1_final": macro_f1(true, final),
        "confusion_raw": confusion_matrix(true, raw),
        "confusion_final": confusion_matrix(true, final),
        "per_intent": per_intent_table(true, z),
        "overrides": override_counts(rows),
        "auto_handle_precision": auto_handle_precision(rows, auto_threshold),
        "judge_specificity": judge_specificity(rows),
        "wrong_close_recall": wrong_close_recall(rows),
    }


# --- F009-2: kappa, bootstrap CI, rater-spread bar ------------------------------


def cohen_kappa(a, b):
    """Chance-corrected agreement between two raters (§2, decision 9).

    kappa = (p_o - p_e) / (1 - p_e) over the joint label distribution. When
    both raters are constant on one class chance correction is undefined:
    perfect agreement reads 1.0, any disagreement 0.0."""
    if len(a) != len(b):
        raise ValueError("rater label lists must be the same length")
    n = len(a)
    if n == 0:
        return 0.0
    joint = Counter(zip(a, b))
    fa = Counter(a)
    fb = Counter(b)
    po = sum(c for (x, y), c in joint.items() if x == y) / n
    pe = sum(fa[x] * fb[x] for x in set(a) | set(b)) / (n * n)
    if pe == 1.0:
        return 1.0 if po == 1.0 else 0.0
    return (po - pe) / (1 - pe)


def bootstrap_ci(units, stat, n_boot=1000, seed=0, alpha=0.05):
    """Percentile bootstrap CI for ``stat`` over resampled units.

    ``units`` is the sample (one element per bootstrap draw, e.g. paired rater
    rows), ``stat`` maps a resampled list back to a float. Returns
    (lo, hi, point) where point is stat on the full sample."""
    rng = random.Random(seed)
    n = len(units)
    if n == 0:
        return (None, None, None)
    stats = sorted(stat([units[rng.randrange(n)] for _ in range(n)]) for _ in range(n_boot))
    k = int(round(alpha / 2 * n_boot))
    point = stat(units)
    return (stats[max(k - 1, 0)], stats[min(n_boot - k, n_boot - 1)], point)


def majority_label(ratings):
    """Per-row majority label across raters (mode per column; odd rater count
    means a strict majority always exists — alphabetical tie-break keeps it
    deterministic anyway)."""
    names = list(ratings)
    if not names:
        return []
    out = []
    for i in range(len(ratings[names[0]])):
        votes = Counter(ratings[name][i] for name in names)
        out.append(sorted(votes, key=lambda label: (-votes[label], str(label)))[0])
    return out


def pairwise_kappas(ratings):
    """Cohen's kappa for every rater pair in insertion order."""
    names = list(ratings)
    out = {}
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            out[(a, b)] = cohen_kappa(ratings[a], ratings[b])
    return out


def rater_spread_bar(kappas, n_sigma=2.0):
    """mean − n_sigma·σ over the raters' own pairwise kappas (§11). None when
    fewer than two kappas exist to estimate a spread."""
    values = list(kappas.values())
    if len(values) < 2:
        return None
    return statistics.mean(values) - n_sigma * statistics.stdev(values)


def judge_spread_check(human_ratings, judge_ratings, n_sigma=2.0):
    """Judge-vs-majority kappa against the mean−2σ bar set by the human raters'
    own pairwise kappas. ``passed`` is the drift verdict (§11)."""
    kappas = pairwise_kappas(human_ratings)
    majority = majority_label(human_ratings)
    judge_vs_majority = cohen_kappa(judge_ratings, majority)
    bar = rater_spread_bar(kappas, n_sigma)
    return {
        "pairwise_human_kappas": kappas,
        "judge_vs_majority": judge_vs_majority,
        "bar": bar,
        "passed": bar is None or judge_vs_majority >= bar,
    }
