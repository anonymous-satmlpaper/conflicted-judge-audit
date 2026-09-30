"""Cross-check numerical claims used in the SaTML manuscript.

Uses only the Python standard library and reads the preserved machine-readable
audit outputs. It does not call any model API or modify experiment inputs.
"""
from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def fisher_two_sided(a: int, b: int, c: int, d: int) -> float:
    """Two-sided Fisher exact p-value using probability ordering."""
    r1, r2, c1 = a + b, c + d, a + c
    n = r1 + r2
    lo, hi = max(0, c1 - r2), min(r1, c1)

    def probability(x: int) -> float:
        return math.comb(r1, x) * math.comb(r2, c1 - x) / math.comb(n, c1)

    observed = probability(a)
    return sum(probability(x) for x in range(lo, hi + 1) if probability(x) <= observed + 1e-15)


def main() -> None:
    legacy = read_json(ROOT / "scoring" / "satml" / "legacy_audit.json")
    audit = read_json(ROOT / "outputs" / "satml" / "deterministic_audit_v1.json")
    fixtures = read_json(ROOT / "scoring" / "satml" / "fixture_validation_v1.json")
    validation = read_json(ROOT / "scoring" / "satml" / "validation_summary_v1.json")
    human = read_json(ROOT / "scoring" / "satml" / "human_validation_results_v2.json")

    assert legacy["n_cases"] == 30
    assert legacy["n_responses"] == 120
    assert legacy["n_claims"] == 830
    assert legacy["prompt_mismatches"] == []
    assert len(audit["records"]) == 180

    responses = Counter(r["model_requested"] for r in audit["records"])
    assert len(responses) == 6 and set(responses.values()) == {30}
    flags = Counter(f["check"] for r in audit["records"] for f in r["flags"])
    assert flags == Counter({"C3": 7, "C1": 2})

    by_model = Counter()
    for record in audit["records"]:
        by_model[record["model_requested"]] += len(record["flags"])
    expected = {
        "claude-opus-5": 0,
        "claude-sonnet-5": 0,
        "claude-haiku-4-5": 1,
        "qwen2.5:7b": 4,
        "gpt-5.5-2026-04-23": 1,
        "gpt-5.4-mini-2026-03-17": 3,
    }
    assert {model: by_model[model] for model in expected} == expected
    assert validation == {
        "raised": 9,
        "confirmed": 9,
        "rejected": 0,
        "observed_precision": 1,
        "recall_validated": False,
        "blinded": False,
    }
    assert human["completeness"]["valid_and_complete"] is True
    assert human["flag_review"]["consensus_counts"] == {
        "Yes": 7, "No": 0, "Unclear": 2, "Disagreement": 0
    }
    assert human["miss_review"]["consensus_counts"] == {
        "Yes": 1, "No": 22, "Unclear": 0, "Disagreement": 1
    }
    expected_claim_agreement = {
        "support": (53, 0.798076923076923),
        "provenance": (60, None),
        "obs_inf": (54, 0.888268156424581),
        "attribution": (59, 0.9514563106796117),
        "reproducibility": (55, 0.8295454545454546),
    }
    for dim, (matches, kappa) in expected_claim_agreement.items():
        result = human["claim_ratings"][dim]
        assert result["author_author_exact"]["matches"] == matches
        assert result["author_author_exact"]["n"] == 60
        if kappa is None:
            assert result["author_author_quadratic_weighted_kappa"] is None
        else:
            assert abs(result["author_author_quadratic_weighted_kappa"] - kappa) < 1e-12

    assert fixtures["status"] == "pass"
    assert fixtures["total_positive_controls"] == 80
    assert fixtures["total_positive_detected"] == 80
    assert fixtures["total_negative_controls"] == 80
    assert fixtures["total_negative_rejected"] == 80
    for result in fixtures["checks"].values():
        assert result == {
            "positive_controls": 20,
            "positive_detected": 20,
            "negative_controls": 20,
            "negative_rejected": 20,
        }

    second = legacy["second_rater"]
    assert second["n_responses"] == 30 and second["n_unique_cases"] == 21
    assert abs(second["rounded_ordinal_alpha"]["pooled"] - 0.05187413610862679) < 1e-12
    assert abs(second["mean_secondary_minus_primary"] + 0.18673015873015875) < 1e-12
    assert abs(second["response_wilcoxon"]["p"] - 0.0003392724719078384) < 1e-15
    assert abs(second["case_aggregated_wilcoxon"]["p"] - 0.002048437590048656) < 1e-15

    assert abs(fisher_two_sided(1, 29, 8, 22) - 0.025690734963116427) < 1e-12
    assert abs(fisher_two_sided(1, 9, 3, 7) - 0.5820433436532508) < 1e-12

    report = {
        "status": "pass",
        "cases": 30,
        "responses": 180,
        "systems": 6,
        "primary_claims": 830,
        "flags": dict(flags),
        "flags_by_model": expected,
        "historical_unblinded_confirmation": "9/9; reported separately from the blinded author audit",
        "blinded_author_audit": "7/9 confirmed, 2/9 unclear; 1/24 sampled nonflags missed, 1/24 disputed",
        "seeded_controls": "80/80 violations detected; 80/80 matched non-violations rejected",
        "cross_rater_pooled_alpha": second["rounded_ordinal_alpha"]["pooled"],
        "cross_rater_mean_secondary_minus_primary": second["mean_secondary_minus_primary"],
        "frontier_compact_fisher_two_sided": fisher_two_sided(1, 29, 8, 22),
        "scope": "Consistency check of preserved outputs; no new model calls.",
    }
    out = ROOT / "scoring" / "satml" / "manuscript_claims_v4.json"
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

