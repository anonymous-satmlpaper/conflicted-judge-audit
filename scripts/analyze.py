"""
analyze.py -- aggregate the single-annotator rubric scores (scoring/all_scores.json)
against the harness raw outputs (outputs/harness/*.json), compute ROUGE-L as
the conventional-metric baseline, and report:
  - per-model, per-dimension mean rubric scores
  - per-difficulty-tag, per-dimension mean rubric scores (esp. attribution
    dimension broken out by attribution_trap vs other tags)
  - Spearman correlation between mean rubric score and ROUGE-L F1 per response
  - descriptive stats only -- no significance testing framed as confirmatory,
    given N is a pilot/exploratory scale, not a pre-registered confirmatory study
"""

import json
import statistics as stats
from collections import defaultdict
from pathlib import Path

from scipy.stats import spearmanr

from metrics import rouge_l

ROOT = Path(__file__).resolve().parent.parent
CASES_DIR = ROOT / "cases"
HARNESS_DIR = ROOT / "outputs" / "harness"
SCORES_FILE = ROOT / "scoring" / "all_scores.json"

DIMENSIONS = ["support", "provenance", "obs_inf", "attribution", "reproducibility"]


def load_cases() -> dict:
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in CASES_DIR.glob("AND-*.json")}


def load_harness() -> dict:
    """Keyed by (case_id, model_requested)."""
    out = {}
    for p in HARNESS_DIR.glob("*.json"):
        d = json.loads(p.read_text(encoding="utf-8"))
        out[(d["case_id"], d["model_requested"])] = d
    return out


def load_scores() -> list[dict]:
    if not SCORES_FILE.exists():
        return []
    return json.loads(SCORES_FILE.read_text(encoding="utf-8"))


def response_mean_scores(claims: list[dict]) -> dict:
    return {dim: stats.mean(c[dim] for c in claims) for dim in DIMENSIONS}


def main() -> None:
    cases = load_cases()
    harness = load_harness()
    scores = load_scores()

    # group claim-level scores by response
    by_response = defaultdict(list)
    for entry in scores:
        by_response[(entry["case_id"], entry["model_requested"])].append(entry)

    print(f"Scored responses: {len(by_response)} / {len(harness)} harness outputs\n")

    # --- per-model breakdown ---
    per_model = defaultdict(lambda: defaultdict(list))
    per_tag = defaultdict(lambda: defaultdict(list))
    rows = []  # for correlation: (mean_rubric_score, rouge_l_f1)

    for (case_id, model), claims in by_response.items():
        means = response_mean_scores(claims)
        for dim in DIMENSIONS:
            per_model[model][dim].append(means[dim])
            per_tag[cases[case_id]["difficulty_tag"]][dim].append(means[dim])

        harness_entry = harness.get((case_id, model))
        if harness_entry:
            reference = " ".join(cases[case_id]["ground_truth"]["supported_findings"])
            r = rouge_l(harness_entry["response_text"], reference)
            overall_mean = stats.mean(means.values())
            rows.append((overall_mean, r["f1"]))

    print("=== Per-model mean rubric scores (0-2 scale) ===")
    for model, dims in sorted(per_model.items()):
        line = ", ".join(f"{d}={stats.mean(v):.2f}" for d, v in dims.items())
        n_responses = len(next(iter(dims.values())))
        print(f"  {model} (n={n_responses} responses): {line}")

    print("\n=== Per-difficulty-tag mean rubric scores (0-2 scale) ===")
    for tag, dims in sorted(per_tag.items()):
        line = ", ".join(f"{d}={stats.mean(v):.2f}" for d, v in dims.items())
        n_responses = len(next(iter(dims.values())))
        print(f"  {tag} (n={n_responses} responses): {line}")

    if len(rows) >= 3:
        rubric_means, rouge_f1s = zip(*rows)
        rho, p = spearmanr(rubric_means, rouge_f1s)
        print(f"\n=== RQ1: Spearman correlation, mean rubric score vs ROUGE-L F1 ===")
        print(f"  n={len(rows)}, rho={rho:.3f}, p={p:.4f}")
    else:
        print("\nNot enough scored responses yet for correlation (need >= 3).")

    # dump machine-readable summary
    summary = {
        "n_scored_responses": len(by_response),
        "n_harness_outputs": len(harness),
        "per_model": {m: {d: stats.mean(v) for d, v in dims.items()} for m, dims in per_model.items()},
        "per_difficulty_tag": {t: {d: stats.mean(v) for d, v in dims.items()} for t, dims in per_tag.items()},
    }
    if len(rows) >= 3:
        rubric_means, rouge_f1s = zip(*rows)
        rho, p = spearmanr(rubric_means, rouge_f1s)
        summary["spearman_rubric_vs_rouge_l"] = {"n": len(rows), "rho": rho, "p": p}

    # --- per-model x per-tag breakdown on the dimension the paper cares most about (support, obs_inf) ---
    per_model_tag = defaultdict(lambda: defaultdict(list))
    for (case_id, model), claims in by_response.items():
        means = response_mean_scores(claims)
        tag = cases[case_id]["difficulty_tag"]
        per_model_tag[(model, tag)]["support"].append(means["support"])
        per_model_tag[(model, tag)]["obs_inf"].append(means["obs_inf"])

    print("\n=== Per-model x per-difficulty-tag (support / obs_inf means) ===")
    for (model, tag), dims in sorted(per_model_tag.items()):
        n = len(dims["support"])
        print(f"  {model:20s} {tag:20s} (n={n}): support={stats.mean(dims['support']):.2f}, obs_inf={stats.mean(dims['obs_inf']):.2f}")

    # --- Mann-Whitney U: supplementary, pooled (non-independent) between-groups comparisons ---
    # NOTE: this pools per-response scores as if independent, which is a design-inappropriate
    # test given all models answer the same 30 cases (see reanalyze_v2.py for the corrected
    # case-paired Wilcoxon signed-rank test, which is what the paper cites as primary).
    try:
        from scipy.stats import mannwhitneyu

        def group_scores(models):
            return [stats.mean(response_mean_scores(c).values()) for (cid, m), c in by_response.items() if m in models]

        claude_models = {"claude-opus-5", "claude-sonnet-5", "claude-haiku-4-5"}

        haiku_scores = group_scores({"claude-haiku-4-5"})
        opus_sonnet_scores = group_scores({"claude-opus-5", "claude-sonnet-5"})
        u_stat, p_val = mannwhitneyu(haiku_scores, opus_sonnet_scores, alternative="two-sided")
        n1, n2 = len(haiku_scores), len(opus_sonnet_scores)
        effect_r = 1 - (2 * u_stat) / (n1 * n2)
        print(f"\n=== RQ2: Mann-Whitney U (supplementary), Haiku vs Opus+Sonnet pooled ===")
        print(f"  n_haiku={n1}, n_other={n2}, U={u_stat:.1f}, p={p_val:.6f}, rank-biserial r={effect_r:.3f}")
        summary["mannwhitney_haiku_vs_others"] = {"n_haiku": n1, "n_other": n2, "U": u_stat, "p": p_val, "rank_biserial_r": effect_r}

        qwen_scores = group_scores({"qwen2.5:7b"})
        claude_scores = group_scores(claude_models)
        u_stat2, p_val2 = mannwhitneyu(qwen_scores, claude_scores, alternative="two-sided")
        n1b, n2b = len(qwen_scores), len(claude_scores)
        effect_r2 = 1 - (2 * u_stat2) / (n1b * n2b)
        print(f"\n=== RQ2: Mann-Whitney U (supplementary), qwen2.5:7b vs all 3 Claude models pooled ===")
        print(f"  n_qwen={n1b}, n_claude={n2b}, U={u_stat2:.1f}, p={p_val2:.6f}, rank-biserial r={effect_r2:.3f}")
        summary["mannwhitney_qwen_vs_claude"] = {"n_qwen": n1b, "n_claude": n2b, "U": u_stat2, "p": p_val2, "rank_biserial_r": effect_r2}
    except Exception as e:
        print(f"\nMann-Whitney test skipped: {e}")

    out_path = ROOT / "scoring" / "analysis_summary.json"
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nSaved machine-readable summary to {out_path}")


if __name__ == "__main__":
    main()
