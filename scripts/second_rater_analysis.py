"""
second_rater_analysis.py -- compare the primary AI annotator's (Claude
Sonnet 5) response-level mean scores against qwen2.5:7b's independent
scores on the same stratified 30-response subset, to test whether the
primary annotator's self-preference bias (same organization/model as
the systems scored) measurably inflates scores for Claude-authored
responses relative to a rater with no stake in the Claude family.
"""

import json
import statistics as stats
from collections import defaultdict
from pathlib import Path

import krippendorff
from scipy.stats import wilcoxon, pearsonr

ROOT = Path(__file__).resolve().parent.parent
SCORES_FILE = ROOT / "scoring" / "all_scores.json"
SECOND_RATER_DIR = ROOT / "outputs" / "second_rater"

DIMENSIONS = ["support", "provenance", "obs_inf", "attribution", "reproducibility"]


def load_primary_scores():
    scores = json.loads(SCORES_FILE.read_text(encoding="utf-8"))
    by_response = defaultdict(list)
    for entry in scores:
        by_response[(entry["case_id"], entry["model_requested"])].append(entry)
    return by_response


def response_mean(claims):
    return {dim: stats.mean(c[dim] for c in claims) for dim in DIMENSIONS}


def main():
    primary = load_primary_scores()
    second_rater_files = sorted(SECOND_RATER_DIR.glob("*__qwen-rater.json"))
    print(f"Second-rater scored responses found: {len(second_rater_files)}")

    pairs = []  # (case_id, model, dim, primary_score, qwen_score)
    rows = []   # per-response: (case_id, model, primary_overall_mean, qwen_overall_mean)
    for p in second_rater_files:
        rec = json.loads(p.read_text(encoding="utf-8"))
        case_id, model = rec["case_id"], rec["model_requested"]
        qwen_score = rec["qwen_score"]
        primary_claims = primary.get((case_id, model))
        if not primary_claims:
            continue
        primary_means = response_mean(primary_claims)
        for dim in DIMENSIONS:
            pairs.append((case_id, model, dim, primary_means[dim], qwen_score[dim]))
        rows.append((case_id, model, stats.mean(primary_means.values()), stats.mean(qwen_score[d] for d in DIMENSIONS)))

    n = len(rows)
    print(f"Matched (case, model) pairs: {n}\n")

    # --- Per-dimension agreement ---
    print("=== Per-dimension agreement (primary annotator vs qwen2.5:7b rater) ===")
    summary = {"n_responses": n, "per_dimension": {}}
    for dim in DIMENSIONS:
        primary_vals = [p for (cid, m, d, p, q) in pairs if d == dim]
        qwen_vals = [q for (cid, m, d, p, q) in pairs if d == dim]
        # exact agreement (rounding primary's continuous mean to nearest int for a strict check)
        primary_rounded = [round(v) for v in primary_vals]
        qwen_rounded = [round(v) for v in qwen_vals]
        exact_agree = sum(1 for a, b in zip(primary_rounded, qwen_rounded) if a == b) / n
        mean_abs_diff = stats.mean(abs(a - b) for a, b in zip(primary_vals, qwen_vals))
        try:
            r, r_p = pearsonr(primary_vals, qwen_vals)
        except Exception:
            r, r_p = float("nan"), float("nan")
        # Krippendorff's alpha (ordinal), two raters, n items -- reliability_data shape (2, n)
        try:
            alpha = krippendorff.alpha(
                reliability_data=[primary_rounded, qwen_rounded],
                level_of_measurement="ordinal",
            )
        except Exception as e:
            alpha = float("nan")
        print(f"  {dim:16s}: exact_agree={exact_agree:.2f}, mean_abs_diff={mean_abs_diff:.2f}, "
              f"pearson_r={r:.3f}, alpha={alpha:.3f}")
        summary["per_dimension"][dim] = {
            "exact_agreement": exact_agree, "mean_abs_diff": mean_abs_diff,
            "pearson_r": r, "pearson_p": r_p, "krippendorff_alpha": alpha,
        }

    # --- Overall (all dims pooled) ---
    all_primary_rounded = [round(p) for (cid, m, d, p, q) in pairs]
    all_qwen_rounded = [round(q) for (cid, m, d, p, q) in pairs]
    overall_alpha = krippendorff.alpha(
        reliability_data=[all_primary_rounded, all_qwen_rounded], level_of_measurement="ordinal"
    )
    overall_exact = sum(1 for a, b in zip(all_primary_rounded, all_qwen_rounded) if a == b) / len(pairs)
    print(f"\n=== Overall (all dimensions pooled, n={len(pairs)}) ===")
    print(f"  exact_agreement={overall_exact:.3f}, Krippendorff's alpha (ordinal)={overall_alpha:.3f}")
    summary["overall"] = {"exact_agreement": overall_exact, "krippendorff_alpha": overall_alpha, "n_scored_pairs": len(pairs)}

    # --- Does the Claude-vs-Claude model ranking survive under qwen's ratings? ---
    print("\n=== Per-model mean overall score: primary annotator vs qwen rater (same subset) ===")
    per_model_primary = defaultdict(list)
    per_model_qwen = defaultdict(list)
    for (cid, m, primary_mean, qwen_mean) in rows:
        per_model_primary[m].append(primary_mean)
        per_model_qwen[m].append(qwen_mean)
    model_comparison = {}
    for m in sorted(per_model_primary):
        pm = stats.mean(per_model_primary[m])
        qm = stats.mean(per_model_qwen[m])
        print(f"  {m:20s}: primary_mean={pm:.3f} (n={len(per_model_primary[m])}), qwen_mean={qm:.3f}")
        model_comparison[m] = {"primary_mean": pm, "qwen_mean": qm, "n": len(per_model_primary[m])}
    summary["per_model_comparison"] = model_comparison

    # paired test: does qwen's overall score differ from primary's, systematically?
    primary_all = [r[2] for r in rows]
    qwen_all = [r[3] for r in rows]
    diffs = [q - p for p, q in zip(primary_all, qwen_all)]
    print(f"\n  Mean(qwen - primary) overall score: {stats.mean(diffs):+.3f} (negative = qwen stricter)")
    try:
        w, wp = wilcoxon(primary_all, qwen_all)
        print(f"  Wilcoxon signed-rank (primary vs qwen, paired by response): W={w:.1f}, p={wp:.4f}")
        summary["primary_vs_qwen_paired_wilcoxon"] = {"W": w, "p": wp, "mean_diff_qwen_minus_primary": stats.mean(diffs)}
    except Exception as e:
        print(f"  Wilcoxon skipped: {e}")

    out_path = ROOT / "scoring" / "second_rater_agreement.json"
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
