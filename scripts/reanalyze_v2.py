"""
reanalyze_v2.py -- follow-up analysis addressing external review feedback:

1. Case-level paired comparison (Wilcoxon signed-rank) instead of pooling
   581 claims / 90 responses as if independent -- the original Mann-Whitney
   U treated claims nested within responses within cases as independent
   observations, which inflates apparent significance. Wilcoxon signed-rank
   on the 30 paired per-case means (Haiku vs Opus, Haiku vs Sonnet) respects
   the actual unit of replication (the case).
2. Response-length vs. rubric-score and response-length vs. ROUGE-L F1
   correlations, to test whether the RQ1 negative correlation is substantially
   a length artifact rather than a genuine reliability-vs-similarity effect.

No new API calls -- reuses outputs/harness/*.json and scoring/all_scores.json.
"""

import json
import statistics as stats
from collections import defaultdict
from pathlib import Path

from scipy.stats import spearmanr, wilcoxon

from metrics import rouge_l

ROOT = Path(__file__).resolve().parent.parent
CASES_DIR = ROOT / "cases"
HARNESS_DIR = ROOT / "outputs" / "harness"
SCORES_FILE = ROOT / "scoring" / "all_scores.json"

DIMENSIONS = ["support", "provenance", "obs_inf", "attribution", "reproducibility"]


def load_cases():
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in CASES_DIR.glob("AND-*.json")}


def load_harness():
    out = {}
    for p in HARNESS_DIR.glob("*.json"):
        d = json.loads(p.read_text(encoding="utf-8"))
        out[(d["case_id"], d["model_requested"])] = d
    return out


def load_scores():
    return json.loads(SCORES_FILE.read_text(encoding="utf-8"))


def response_mean(claims):
    return stats.mean(stats.mean(c[dim] for dim in DIMENSIONS) for c in claims)


def main():
    cases = load_cases()
    harness = load_harness()
    scores = load_scores()

    by_response = defaultdict(list)
    for entry in scores:
        by_response[(entry["case_id"], entry["model_requested"])].append(entry)

    case_ids = sorted(cases.keys())

    # --- 1. Case-level paired analysis ---
    haiku_means, opus_means, sonnet_means, qwen_means = [], [], [], []
    for cid in case_ids:
        haiku_means.append(response_mean(by_response[(cid, "claude-haiku-4-5")]))
        opus_means.append(response_mean(by_response[(cid, "claude-opus-5")]))
        sonnet_means.append(response_mean(by_response[(cid, "claude-sonnet-5")]))
        qwen_means.append(response_mean(by_response[(cid, "qwen2.5:7b")]))

    print("=== Case-level paired comparison (n=30 cases, Wilcoxon signed-rank) ===")
    w_ho, p_ho = wilcoxon(haiku_means, opus_means)
    print(f"  Haiku vs Opus:   W={w_ho:.1f}, p={p_ho:.6f}")
    w_hs, p_hs = wilcoxon(haiku_means, sonnet_means)
    print(f"  Haiku vs Sonnet: W={w_hs:.1f}, p={p_hs:.6f}")

    n_haiku_lower_opus = sum(1 for h, o in zip(haiku_means, opus_means) if h < o)
    n_haiku_lower_sonnet = sum(1 for h, s in zip(haiku_means, sonnet_means) if h < s)
    print(f"  Cases where Haiku < Opus:   {n_haiku_lower_opus}/30")
    print(f"  Cases where Haiku < Sonnet: {n_haiku_lower_sonnet}/30")

    # matched-pairs rank-biserial effect size = (sum of positive ranks - sum of negative ranks) / total
    def rank_biserial(a, b):
        diffs = [x - y for x, y in zip(a, b)]
        nz = [d for d in diffs if d != 0]
        n = len(nz)
        if n == 0:
            return 0.0
        pos = sum(1 for d in nz if d > 0)
        neg = n - pos
        return (pos - neg) / n

    print(f"  Rank-biserial (sign-based) Haiku vs Opus:   {rank_biserial(haiku_means, opus_means):.3f}")
    print(f"  Rank-biserial (sign-based) Haiku vs Sonnet: {rank_biserial(haiku_means, sonnet_means):.3f}")

    print("\n=== Case-level paired comparison, qwen2.5:7b vs each Claude model (n=30 cases) ===")
    qwen_pairs = {"Opus": opus_means, "Sonnet": sonnet_means, "Haiku": haiku_means}
    qwen_case_results = {}
    for name, other_means in qwen_pairs.items():
        w, p = wilcoxon(qwen_means, other_means)
        n_lower = sum(1 for q, o in zip(qwen_means, other_means) if q < o)
        rb = rank_biserial(qwen_means, other_means)
        print(f"  qwen vs {name}: W={w:.1f}, p={p:.6f}, qwen-lower={n_lower}/30, rank-biserial={rb:.3f}")
        qwen_case_results[name] = {"W": w, "p": p, "n_qwen_lower": n_lower, "rank_biserial": rb}

    # --- 2. Response length vs rubric score / ROUGE-L F1 ---
    print("\n=== Response length confound check ===")
    rows = []
    for (case_id, model), claims in by_response.items():
        harness_entry = harness.get((case_id, model))
        if not harness_entry:
            continue
        text = harness_entry["response_text"]
        word_count = len(text.split())
        rubric_mean = response_mean(claims)
        reference = " ".join(cases[case_id]["ground_truth"]["supported_findings"])
        r = rouge_l(text, reference)
        rows.append((word_count, rubric_mean, r["f1"]))

    word_counts, rubric_means, rouge_f1s = zip(*rows)
    rho_len_rubric, p_len_rubric = spearmanr(word_counts, rubric_means)
    rho_len_rouge, p_len_rouge = spearmanr(word_counts, rouge_f1s)
    print(f"  n={len(rows)}")
    print(f"  Spearman(length, rubric_mean):  rho={rho_len_rubric:.3f}, p={p_len_rubric:.4f}")
    print(f"  Spearman(length, ROUGE-L F1):   rho={rho_len_rouge:.3f}, p={p_len_rouge:.4f}")
    print(f"  mean word count: {stats.mean(word_counts):.0f}, stdev: {stats.stdev(word_counts):.0f}")

    # per-model mean word count (does Haiku write shorter responses?)
    per_model_len = defaultdict(list)
    for (case_id, model), claims in by_response.items():
        he = harness.get((case_id, model))
        if he:
            per_model_len[model].append(len(he["response_text"].split()))
    print("\n  Mean word count per model:")
    for m, lens in sorted(per_model_len.items()):
        print(f"    {m}: {stats.mean(lens):.0f} (n={len(lens)})")

    out = {
        "case_level_paired": {
            "n_cases": 30,
            "haiku_vs_opus": {"wilcoxon_W": w_ho, "p": p_ho, "n_haiku_lower": n_haiku_lower_opus,
                               "rank_biserial": rank_biserial(haiku_means, opus_means)},
            "haiku_vs_sonnet": {"wilcoxon_W": w_hs, "p": p_hs, "n_haiku_lower": n_haiku_lower_sonnet,
                                 "rank_biserial": rank_biserial(haiku_means, sonnet_means)},
        },
        "qwen_case_level_paired": {"n_cases": 30, **qwen_case_results},
        "length_confound": {
            "n": len(rows),
            "spearman_length_vs_rubric": {"rho": rho_len_rubric, "p": p_len_rubric},
            "spearman_length_vs_rouge_f1": {"rho": rho_len_rouge, "p": p_len_rouge},
            "mean_word_count_per_model": {m: stats.mean(l) for m, l in per_model_len.items()},
        },
    }
    out_path = ROOT / "scoring" / "reanalysis_v2.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
