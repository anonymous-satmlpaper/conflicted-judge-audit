"""Compare the same atomic claims scored by the primary and GPT raters."""
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIMS = ["support", "provenance", "obs_inf", "attribution", "reproducibility"]


def weighted_kappa(a, b, squared=False):
    n = len(a)
    pa, pb = Counter(a), Counter(b)
    def weight(i, j):
        distance = abs(i - j) / 2
        return distance * distance if squared else distance
    observed = sum(weight(x, y) for x, y in zip(a, b)) / n
    expected = sum(weight(i, j) * pa[i] * pb[j] for i in range(3) for j in range(3)) / (n * n)
    return None if expected == 0 else 1 - observed / expected


def main():
    primary = json.loads((ROOT / "scoring" / "all_scores.json").read_text(encoding="utf-8"))
    primary_by_key = {}
    for row in primary:
        primary_by_key.setdefault((row["case_id"], row["model_requested"]), []).append(row)
    paired = []
    for path in sorted((ROOT / "outputs" / "satml" / "claim_rater_gpt55").glob("*.json")):
        rated = json.loads(path.read_text(encoding="utf-8"))
        key = (rated["case_id"], rated["source_model_blinded_during_rating"])
        source = primary_by_key[key]
        assert len(source) == len(rated["scores"])
        for p, g in zip(source, sorted(rated["scores"], key=lambda x: x["index"])):
            assert p["claim"] == g["claim"]
            paired.append((p, g))
    assert len(paired) == len(primary), (len(paired), len(primary))
    summary = {
        "n_claims": len(paired),
        "n_responses": len(list((ROOT / "outputs" / "satml" / "claim_rater_gpt55").glob("*.json"))),
        "unit": "same atomic claim for both raters",
        "rater_blinded_to_source_model": True,
        "per_dimension": {},
    }
    for dim in DIMS:
        a = [p[dim] for p, _ in paired]
        b = [g[dim] for _, g in paired]
        summary["per_dimension"][dim] = {
            "exact_agreement": sum(x == y for x, y in zip(a, b)) / len(a),
            "mean_primary": sum(a) / len(a),
            "mean_gpt": sum(b) / len(b),
            "mean_gpt_minus_primary": sum(y - x for x, y in zip(a, b)) / len(a),
            "mean_absolute_difference": sum(abs(y - x) for x, y in zip(a, b)) / len(a),
            "linear_weighted_kappa": weighted_kappa(a, b),
            "quadratic_weighted_kappa": weighted_kappa(a, b, squared=True),
        }
    dest = ROOT / "scoring" / "satml" / "claim_rater_gpt55_summary.json"
    dest.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
