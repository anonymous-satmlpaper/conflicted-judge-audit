"""Family-stratified judge-affinity test on the blinded author audit.

For each of the 60 sampled claims, compute the primary-judge score minus the
mean of the two author scores (the "judge excess"). Compare judge excess for
claims authored by Claude endpoints against claims authored by Qwen2.5 7B, and
for the judge's own endpoint (Sonnet) against all others. Inference uses a
response-clustered permutation test: family labels are permuted at the response
level so claims from the same response move together.

Inputs are the same files used by analyze_human_reviews.js.
"""
import json
import random
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent.parent
KEY = ROOT / "scoring" / "satml" / "human_review_key_v1.json"
A_RAW = ROOT / "tmp" / "human_review" / "completed_reviews.json"
B_FIELDS = ROOT / "scoring" / "satml" / "reviewer_B_pdf_fields_v1.json"
OUT = ROOT / "scoring" / "satml" / "family_stratified_audit_v1.json"

DIMS = ["support", "provenance", "obs_inf", "attribution", "reproducibility"]
B_SUFFIX = {"support": "Evidence", "provenance": "Provenance", "obs_inf": "Observation",
            "attribution": "Attribution", "reproducibility": "Reproducibility"}
JUDGE = "claude-sonnet-5"
N_PERM = 20000
SEED = 20260930


def load_reviewer_a():
    raw = json.loads(A_RAW.read_text(encoding="utf-8"))
    name = next((n for n in raw if "reviewer-a" in n.lower()), next(iter(raw)))
    rows = raw[name]["claims"][1:]
    return {r[0]: dict(zip(DIMS, r[4:9])) for r in rows}


def load_reviewer_b(key):
    fields = json.loads(B_FIELDS.read_text(encoding="utf-8"))
    fm = {f["name"]: f["value"] for f in fields}
    return {c["sample_id"]: {d: int(fm[f"{c['sample_id']}.{B_SUFFIX[d]}"]) for d in DIMS}
            for c in key["claim_sample"]}


def family(model):
    return "claude" if model.startswith("claude") else "qwen"


def cluster_perm_test(rows, group_of_response, n_perm=N_PERM, seed=SEED):
    """Two-sided test of mean(excess | group True) - mean(excess | group False),
    permuting group labels across responses."""
    by_resp = {}
    for r in rows:
        by_resp.setdefault(r["response_id"], []).append(r["excess"])
    resp_ids = sorted(by_resp)
    labels = [group_of_response[rid] for rid in resp_ids]

    def stat(lab):
        g1 = [x for rid, l in zip(resp_ids, lab) if l for x in by_resp[rid]]
        g0 = [x for rid, l in zip(resp_ids, lab) if not l for x in by_resp[rid]]
        return mean(g1) - mean(g0)

    observed = stat(labels)
    rng = random.Random(seed)
    extreme = 0
    for _ in range(n_perm):
        perm = labels[:]
        rng.shuffle(perm)
        if abs(stat(perm)) >= abs(observed) - 1e-12:
            extreme += 1
    return {"difference": observed, "p_two_sided": (extreme + 1) / (n_perm + 1),
            "n_responses": len(resp_ids), "n_permutations": n_perm}


def summarize(rows):
    out = {"n_claims": len(rows), "n_responses": len({r["response_id"] for r in rows})}
    for d in DIMS:
        p = mean(r["primary"][d] for r in rows)
        a = mean(r["author"][d] for r in rows)
        out[d] = {"primary_mean": p, "author_mean": a, "judge_excess": p - a}
    out["all_dims"] = {
        "primary_mean": mean(mean(r["primary"][d] for d in DIMS) for r in rows),
        "author_mean": mean(mean(r["author"][d] for d in DIMS) for r in rows),
        "judge_excess": mean(r["excess"] for r in rows),
    }
    return out


def main():
    key = json.loads(KEY.read_text(encoding="utf-8"))
    A = load_reviewer_a()
    B = load_reviewer_b(key)
    rows = []
    for c in key["claim_sample"]:
        sid = c["sample_id"]
        primary = {d: c[d] for d in DIMS}
        author = {d: (A[sid][d] + B[sid][d]) / 2 for d in DIMS}
        rows.append({
            "sample_id": sid, "response_id": c["response_id"], "case_id": c["case_id"],
            "model": c["model_requested"], "family": family(c["model_requested"]),
            "primary": primary, "author": author,
            # Mean over dimensions of (primary - author mean).
            "excess": mean(primary[d] - author[d] for d in DIMS),
        })

    by_model = {m: summarize([r for r in rows if r["model"] == m])
                for m in sorted({r["model"] for r in rows})}
    by_family = {f: summarize([r for r in rows if r["family"] == f]) for f in ("claude", "qwen")}

    resp_model = {r["response_id"]: r["model"] for r in rows}
    claude_vs_qwen = cluster_perm_test(rows, {k: family(v) == "claude" for k, v in resp_model.items()})
    self_vs_other = cluster_perm_test(rows, {k: v == JUDGE for k, v in resp_model.items()})
    # Scale-matched contrast: both compact endpoints, differing in family.
    compact = [r for r in rows if r["model"] in ("claude-haiku-4-5", "qwen2.5:7b")]
    haiku_vs_qwen = cluster_perm_test(
        compact, {r["response_id"]: r["model"] == "claude-haiku-4-5" for r in compact})

    # Per-dimension family contrast for the two dimensions with non-trivial variance.
    per_dim = {}
    for d in ("support", "obs_inf", "reproducibility"):
        drows = [dict(r, excess=r["primary"][d] - r["author"][d]) for r in rows]
        per_dim[d] = cluster_perm_test(drows, {k: family(v) == "claude" for k, v in resp_model.items()})

    result = {
        "schema": "satml-family-stratified-audit-v1",
        "definition": "judge_excess = primary-judge score minus mean of the two blinded author scores; "
                      "positive values mean the primary judge is more lenient than the authors.",
        "judge_model": JUDGE,
        "by_model": by_model,
        "by_family": by_family,
        "tests": {
            "claude_minus_qwen_excess_all_dims": claude_vs_qwen,
            "judge_self_minus_other_excess_all_dims": self_vs_other,
            "haiku_minus_qwen_excess_all_dims_scale_matched": haiku_vs_qwen,
            "claude_minus_qwen_excess_by_dimension": per_dim,
        },
        "claims": [{k: r[k] for k in ("sample_id", "response_id", "case_id", "model",
                                       "primary", "author", "excess")} for r in rows],
        "caveats": [
            "15 claims per system from few responses; the test has low power.",
            "Author raters are not independent external validators.",
            "Claims were sampled from the primary judge's own decomposition, so segmentation is judge-controlled.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    print(f"{'model':<18}{'n':>3}{'resp':>5}  {'P':>6}{'Auth':>6}{'Excess':>8}   support P/Auth")
    for m, s in by_model.items():
        a = s["all_dims"]; sp = s["support"]
        print(f"{m:<18}{s['n_claims']:>3}{s['n_responses']:>5}  {a['primary_mean']:6.3f}{a['author_mean']:6.3f}"
              f"{a['judge_excess']:8.3f}   {sp['primary_mean']:.2f}/{sp['author_mean']:.2f}")
    for f, s in by_family.items():
        a = s["all_dims"]
        print(f"family {f:<11}{s['n_claims']:>3}{s['n_responses']:>5}  {a['primary_mean']:6.3f}"
              f"{a['author_mean']:6.3f}{a['judge_excess']:8.3f}")
    print(json.dumps(result["tests"], indent=1))


if __name__ == "__main__":
    main()
