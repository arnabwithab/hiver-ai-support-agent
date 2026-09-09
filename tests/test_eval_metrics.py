"""F009: metrics and agreement (design §10). Pure local math, stdlib only.

Covers classification metrics on raw + final labels, override counts, per-intent
CIs, auto-handle precision, judge specificity (fail-recall), Case-B wrong-close
recall, flag slicing — plus Cohen's kappa, bootstrap CIs and the rater-spread bar.
"""

import statistics

import pytest

from src.eval.metrics import (
    EvalRow,
    accuracy,
    auto_handle_precision,
    bootstrap_ci,
    classification_metrics,
    cohen_kappa,
    confusion_matrix,
    evaluate,
    judge_specificity,
    judge_spread_check,
    macro_f1,
    majority_label,
    override_counts,
    pairwise_kappas,
    per_intent_table,
    proportion_ci,
    rater_spread_bar,
    slice_rows,
    wrong_close_recall,
)


def row(*labels, **flags):
    """Default EvalRow: true == raw == final unless overridden."""
    return EvalRow(labels[0], labels[1], labels[2], **flags)


# --- Cohen's kappa on a known table -------------------------------------------


def test_cohen_kappa_matches_hand_computed_table():
    # 2x2 table (rater A rows, rater B cols): [[20, 5], [10, 15]], n=50.
    # p_o = 0.7, p_e = 0.5 -> kappa = 0.4.
    pairs = [("a", "a")] * 20 + [("a", "b")] * 5 + [("b", "a")] * 10 + [("b", "b")] * 15
    a = [p[0] for p in pairs]
    b = [p[1] for p in pairs]
    assert cohen_kappa(a, b) == pytest.approx(0.4)


def test_cohen_kappa_edge_cases():
    assert cohen_kappa(["x"] * 10, ["x"] * 10) == 1.0  # perfect agreement
    # Perfect, systematic disagreement over two labels -> -1.
    assert cohen_kappa(["x"] * 5 + ["y"] * 5, ["y"] * 5 + ["x"] * 5) == pytest.approx(-1.0)
    # No variance (both raters constant, differing): chance-correction undefined -> 0.0.
    assert cohen_kappa(["x"] * 10, ["y"] * 10) == 0.0


def test_cohen_kappa_rejects_length_mismatch():
    with pytest.raises(ValueError):
        cohen_kappa(["x", "y"], ["x"])


# --- Bootstrap CI --------------------------------------------------------------


def test_bootstrap_ci_contains_point_estimate_and_is_seeded():
    pairs = [("a", "a")] * 20 + [("a", "b")] * 5 + [("b", "a")] * 10 + [("b", "b")] * 15

    def kappa_stat(sample):
        return cohen_kappa([p[0] for p in sample], [p[1] for p in sample])

    lo, hi, point = bootstrap_ci(pairs, kappa_stat, n_boot=1000, seed=0)
    assert point == pytest.approx(0.4)
    assert lo <= point <= hi
    # Seeded -> fully reproducible.
    assert bootstrap_ci(pairs, kappa_stat) == (lo, hi, point)


def test_bootstrap_ci_on_mean():
    xs = list(range(1, 21))  # mean 10.5
    lo, hi, point = bootstrap_ci(xs, statistics.mean, n_boot=500, seed=1)
    assert point == 10.5
    assert lo < point < hi


# --- Classification metrics: accuracy, macro-F1, confusion --------------------


def test_accuracy_and_macro_f1_direct():
    assert accuracy([], []) == 0.0
    assert accuracy(["x", "x", "y"], ["x", "y", "y"]) == pytest.approx(2 / 3)
    # x and y both misbalanced one way; each F1 = 2/3.
    assert macro_f1(["x", "x", "y"], ["x", "y", "y"]) == pytest.approx(2 / 3)


def test_classification_metrics_per_class_and_macro():
    true = ["x", "x", "y", "y", "z", "z"]
    pred = ["x", "y", "y", "y", "z", "x"]
    m = classification_metrics(true, pred)
    assert m["accuracy"] == pytest.approx(4 / 6)
    # x: tp1 fp1 fn1 -> F1 .5; y: tp2 fp1 fn0 -> F1 .8; z: tp1 fp0 fn1 -> F1 2/3.
    assert m["classes"]["x"]["f1"] == pytest.approx(0.5)
    assert m["classes"]["y"]["f1"] == pytest.approx(0.8)
    assert m["classes"]["z"]["f1"] == pytest.approx(2 / 3)
    assert m["macro_f1"] == pytest.approx((0.5 + 0.8 + 2 / 3) / 3)
    assert m["n"] == 6


def test_confusion_matrix_shape():
    cm = confusion_matrix(["x", "x", "y", "y", "z", "z"], ["x", "y", "y", "y", "z", "x"])
    assert cm["x"]["x"] == 1 and cm["x"]["y"] == 1 and cm["x"]["z"] == 0
    assert cm["y"]["y"] == 2
    assert cm["z"]["z"] == 1 and cm["z"]["x"] == 1


# --- Raw vs final: both confusion matrices reported ----------------------------


def test_evaluate_reports_raw_and_final_metrics():
    # Row 1: raw wrong (y), inheritance corrects to x.  Row 4: raw wrong (z),
    # veto/shift corrects to y.  Rows 2-3 correct everywhere.
    rows = [
        row("x", "y", "x", case="C", continuation=True),
        row("x", "x", "x", case="C"),
        row("y", "y", "y", case="C"),
        row("y", "z", "y", case="D", veto=True),
    ]
    r = evaluate(rows)
    assert r["n"] == 4
    assert r["accuracy_raw"] == pytest.approx(0.5)  # rows 2,3
    assert r["accuracy_final"] == pytest.approx(1.0)
    # raw macro-F1 over {x,y,z}: x 2/3, y .5, z 0 -> .3889.
    assert r["macro_f1_raw"] == pytest.approx((2 / 3 + 0.5 + 0) / 3)
    assert r["macro_f1_final"] == pytest.approx(1.0)
    assert set(r["confusion_raw"]) == {"x", "y", "z"}
    assert set(r["confusion_final"]) == {"x", "y"}  # z was overridden away everywhere
    assert r["confusion_raw"]["x"]["y"] == 1  # the raw error survives in raw's matrix
    assert r["confusion_final"]["x"]["y"] == 0
    # Overrides: one veto (row 4) and one inheritance hit (row 1).
    assert r["overrides"] == {"veto": 1, "inheritance": 1, "case_b_closes": 0}


# --- Override counts + flag slicing --------------------------------------------


def test_override_counts():
    rows = [
        row("x", "x", "x", case="A"),
        row("x", "x", "x", case="B", closed=True),
        row("x", "x", "x", case="B", closed=True),
        row("x", "x", "x", case="B"),  # awaiting_user: open, not a close
        row("x", "x", "x", case="C", continuation=True),
        row("x", "x", "x", case="D", veto=True),
    ]
    assert override_counts(rows) == {"veto": 1, "inheritance": 1, "case_b_closes": 2}
    assert override_counts([]) == {"veto": 0, "inheritance": 0, "case_b_closes": 0}


def test_slicing_partitions_rows_preserving_counts():
    rows = [
        row("x", "x", "x", case="A"),
        row("x", "x", "x", case="B", closed=True),
        row("x", "x", "x", case="B"),
        row("x", "x", "x", case="C", continuation=True),
        row("x", "x", "x", case="C", shift=True),
        row("x", "x", "x", case="D", veto=True),
    ]
    by_case = [slice_rows(rows, case=c) for c in ("A", "B", "C", "D")]
    assert [len(s) for s in by_case] == [1, 2, 2, 1]
    assert sum(len(s) for s in by_case) == len(rows)
    assert len(slice_rows(rows, case="C", continuation=True)) == 1
    assert len(slice_rows(rows, case="C", continuation=False, shift=True)) == 1
    assert len(slice_rows(rows, veto=True)) == 1
    assert len(slice_rows(rows, case="D", veto=True, continuation=False)) == 1
    assert len(slice_rows(rows, case="D", veto=False)) == 0
    # Multiple flags AND together; all-None filter returns everything.
    assert len(slice_rows(rows)) == 6


def test_evaluate_on_a_slice_keeps_metrics_local():
    rows = [
        row("x", "x", "x", case="A"),
        row("x", "x", "x", case="A"),
        row("x", "x", "x", case="C"),
        row("x", "x", "x", case="C"),
        row("x", "x", "x", case="C"),
    ]
    slice_a = evaluate(slice_rows(rows, case="A"))
    assert slice_a["n"] == 2
    assert len(slice_a["per_intent"]) == 1 and slice_a["per_intent"][0]["count"] == 2


# --- Per-intent counts with CIs ------------------------------------------------


def test_proportion_ci_guard_and_value():
    assert proportion_ci(0, 0) == (None, None)
    lo, hi = proportion_ci(3, 4, z=1.96)  # share .75, se sqrt(.75*.25/4)=.2165
    assert lo == pytest.approx(0.75 - 1.96 * 0.21650635)
    assert hi == pytest.approx(0.75 + 1.96 * 0.21650635)


def test_per_intent_table_counts_and_cis():
    table = per_intent_table(["x", "x", "x", "y"])
    assert len(table) == 2
    x, y = table[0], table[1]
    assert (x["label"], x["count"], x["share"]) == ("x", 3, 0.75)
    assert (y["label"], y["count"], y["share"]) == ("y", 1, 0.25)
    assert x["ci_lo"] <= 0.75 <= x["ci_hi"]
    assert per_intent_table([]) == []


# --- Auto-handle precision at the operating threshold --------------------------


def test_auto_handle_precision_at_threshold():
    rows = [
        row("x", "x", "x", auto=True, conf=0.95, gold_auto=True),
        row("x", "x", "x", auto=True, conf=0.90, gold_auto=False),
        row("x", "x", "x", auto=True, conf=0.85, gold_auto=True),
        row("x", "x", "x", auto=False, conf=0.60, gold_auto=True),  # escalated: not auto
        row("x", "x", "x", auto=True, conf=None, gold_auto=True),  # rule-close: no conf
        row("x", "x", "x", auto=True, conf=0.90, gold_auto=None),  # un-adjudicated
    ]
    # Rows sorted by conf: .95 T, .90 F, .85 T, .60 F(escalated). A threshold
    # of .93 keeps only the confident .95 serve -> precision 1.0.
    assert auto_handle_precision(rows, threshold=0.93) == pytest.approx(1.0)
    assert auto_handle_precision(rows, threshold=0.80) == pytest.approx(2 / 3)
    assert auto_handle_precision(rows, threshold=0.96) is None
    # No threshold: auto rows with a gold verdict, conf or not -> 3/4.
    assert auto_handle_precision(rows) == pytest.approx(3 / 4)
    assert auto_handle_precision([]) is None


# --- Judge specificity (fail-recall) --------------------------------------------


def test_judge_specificity_is_fail_recall():
    rows = [
        row("x", "x", "x", gold_fail=True, judge_fail=True),
        row("x", "x", "x", gold_fail=True, judge_fail=True),
        row("x", "x", "x", gold_fail=True, judge_fail=False),  # missed bad draft
        row("x", "x", "x", gold_fail=False, judge_fail=False),
        row("x", "x", "x", gold_fail=False, judge_fail=True),  # false alarm: not in denom
        row("x", "x", "x", gold_fail=True, judge_fail=None),  # never judged: excluded
    ]
    assert judge_specificity(rows) == pytest.approx(2 / 3)
    assert judge_specificity([row("x", "x", "x", gold_fail=False, judge_fail=False)]) is None
    assert judge_specificity([]) is None


# --- Case-B wrong-close recall ---------------------------------------------------


def test_wrong_close_recall():
    rows = [
        row("x", "x", "x", closed=True, gold_needs_reply=True),  # silent when help needed
        row("x", "x", "x", closed=False, gold_needs_reply=True),  # kept open
        row("x", "x", "x", closed=False, gold_needs_reply=True),  # kept open
        row("x", "x", "x", closed=True, gold_needs_reply=False),  # legitimate close
        row("x", "x", "x", closed=False, gold_needs_reply=None),  # not adjudicated
    ]
    assert wrong_close_recall(rows) == pytest.approx(2 / 3)
    assert wrong_close_recall([row("x", "x", "x", closed=True)]) is None
    assert wrong_close_recall([]) is None


# --- Rater agreement: kappa, majority, spread bar -------------------------------


def test_majority_label_and_pairwise_kappas():
    ratings = {"r1": ["x", "y", "x", "y"], "r2": ["x", "y", "y", "y"], "r3": ["x", "x", "x", "y"]}
    assert majority_label(ratings) == ["x", "y", "x", "y"]
    kappas = pairwise_kappas(ratings)
    assert set(kappas) == {("r1", "r2"), ("r1", "r3"), ("r2", "r3")}
    # Values hand-derived: (r1,r2)=.5, (r1,r3)=.5, (r2,r3)=.2.
    assert kappas[("r1", "r2")] == pytest.approx(0.5)
    assert kappas[("r1", "r3")] == pytest.approx(0.5)
    assert kappas[("r2", "r3")] == pytest.approx(0.2)


def test_rater_spread_bar_is_mean_minus_two_sigma():
    kappas = {("r1", "r2"): 0.5, ("r1", "r3"): 0.5, ("r2", "r3"): 0.2}
    mean = sum(kappas.values()) / 3
    sd = statistics.stdev(kappas.values())
    assert rater_spread_bar(kappas) == pytest.approx(mean - 2 * sd)
    # Not enough pairwise kappas to estimate a spread.
    assert rater_spread_bar({("r1", "r2"): 0.5}) is None


def test_judge_spread_check_verdict():
    human = {"r1": ["x", "y", "x", "y"], "r2": ["x", "y", "y", "y"], "r3": ["x", "x", "x", "y"]}
    agreeing_judge = ["x", "y", "x", "y"]  # == majority -> kappa 1.0
    check = judge_spread_check(human, agreeing_judge)
    assert check["judge_vs_majority"] == pytest.approx(1.0)
    assert check["bar"] == pytest.approx(0.4 - 2 * statistics.stdev([0.5, 0.5, 0.2]))
    assert check["passed"] is True
    # A judge that disagrees with the majority everywhere falls below the bar.
    bad_judge = ["y", "y", "y", "x"]
    bad = judge_spread_check(human, bad_judge)
    assert bad["judge_vs_majority"] == pytest.approx(-0.5)
    assert bad["passed"] is False
