"""Audit whether manuscript counts trace to concrete local experiment records.

This script performs no model calls. It checks stored prompts, responses,
provider metadata, ratings, and a fresh deterministic-verifier rerun.
"""
from __future__ import annotations

import hashlib
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIMS = ["support", "provenance", "obs_inf", "attribution", "reproducibility"]
ORIGINAL_MODELS = ["claude-opus-5", "claude-sonnet-5", "claude-haiku-4-5", "qwen2.5:7b"]
GPT_MODELS = ["gpt-5.5-2026-04-23", "gpt-5.4-mini-2026-03-17"]


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def expected_prompt(case: dict) -> str:
    return case["task_prompt"].replace("{ARTIFACTS_JSON}", json.dumps(case["artifacts"], indent=2))


def response_rows(folder: str):
    rows = []
    for path in sorted((ROOT / folder).glob("*.json")):
        row = read(path)
        if "case_id" in row and "response_text" in row:
            rows.append((path, row))
    return rows


def canonical_flags(data: dict):
    return sorted(
        (
            row["case_id"],
            row["model_requested"],
            tuple(
                (
                    flag["check"],
                    flag.get("domain"),
                    flag.get("evidence"),
                    tuple(flag.get("mentions", [])),
                )
                for flag in row["flags"]
            ),
        )
        for row in data["records"]
    )


def main():
    cases = {path.stem: read(path) for path in sorted((ROOT / "cases").glob("AND-*.json"))}
    assert len(cases) == 30

    original = [(path, row) for path, row in response_rows("outputs/harness") if row.get("model_requested") in ORIGINAL_MODELS]
    assert len(original) == 120
    assert Counter(row["model_requested"] for _, row in original) == Counter({model: 30 for model in ORIGINAL_MODELS})
    assert all(row["case_id"] in cases for _, row in original)
    assert all(row["prompt"] == expected_prompt(cases[row["case_id"]]) for _, row in original)
    assert all(row.get("timestamp") and row.get("model_served_by") and row.get("stop_reason") for _, row in original)
    assert all(row.get("response_text", "").strip() for _, row in original)

    extension = [(path, row) for path, row in response_rows("outputs/satml/legacy") if row.get("model_requested") in GPT_MODELS]
    assert len(extension) == 60
    assert Counter(row["model_requested"] for _, row in extension) == Counter({model: 30 for model in GPT_MODELS})
    assert all(row["case_id"] in cases for _, row in extension)
    assert all(row["prompt"] == expected_prompt(cases[row["case_id"]]) for _, row in extension)
    assert all(row.get("complete") and row.get("response_text", "").strip() for _, row in extension)
    assert all(row["prompt_sha256"] == sha(row["prompt"]) for _, row in extension)
    assert all(row["raw_response"]["status"] == "completed" for _, row in extension)
    assert all(row["model_requested"] == row["model_served_by"] == row["raw_response"]["model"] for _, row in extension)
    response_ids = [row["raw_response"]["id"] for _, row in extension]
    assert len(set(response_ids)) == 60 and all(value.startswith("resp_") for value in response_ids)
    assert all(row["usage"]["total_tokens"] > 0 for _, row in extension)

    all_outputs = original + extension
    output_pairs = [(row["case_id"], row["model_requested"]) for _, row in all_outputs]
    assert len(output_pairs) == len(set(output_pairs)) == 180
    response_hashes = [sha(row["response_text"]) for _, row in all_outputs]
    assert len(set(response_hashes)) == 180

    scores = read(ROOT / "scoring" / "all_scores.json")
    assert len(scores) == 830
    assert Counter(row["model_requested"] for row in scores) == Counter(
        {"claude-opus-5": 217, "claude-sonnet-5": 205, "claude-haiku-4-5": 159, "qwen2.5:7b": 249}
    )
    assert all(row["case_id"] in cases and row["model_requested"] in ORIGINAL_MODELS for row in scores)
    assert all(isinstance(row[d], int) and row[d] in (0, 1, 2) for row in scores for d in DIMS)
    scored_pairs = {(row["case_id"], row["model_requested"]) for row in scores}
    assert len(scored_pairs) == 120

    grouped = defaultdict(list)
    for row in scores:
        grouped[(row["case_id"], row["model_requested"])].append(row)
    case_means = {
        key: {d: statistics.mean(row[d] for row in rows) for d in DIMS}
        for key, rows in grouped.items()
    }
    manuscript_means = {
        model: {d: statistics.mean(case_means[(case_id, model)][d] for case_id in cases) for d in DIMS}
        for model in ORIGINAL_MODELS
    }

    second_files = sorted((ROOT / "outputs" / "second_rater").glob("*.json"))
    second = [read(path) for path in second_files]
    assert len(second) == 30
    assert all(row["case_id"] in cases and row["model_requested"] in ORIGINAL_MODELS for row in second)
    assert all(isinstance(row["qwen_score"][d], int) and row["qwen_score"][d] in (0, 1, 2) for row in second for d in DIMS)

    saved_audit = read(ROOT / "outputs" / "satml" / "deterministic_audit_v1.json")
    rerun_audit = read(ROOT / "tmp" / "provenance_audit_rerun.json")
    assert len(saved_audit["records"]) == len(rerun_audit["records"]) == 180
    assert canonical_flags(saved_audit) == canonical_flags(rerun_audit)

    flags = Counter(flag["check"] for row in saved_audit["records"] for flag in row["flags"])
    flags_by_model = Counter()
    for row in saved_audit["records"]:
        flags_by_model[row["model_requested"]] += len(row["flags"])

    fixture = read(ROOT / "scoring" / "satml" / "fixture_validation_v1.json")
    assert fixture["status"] == "pass"
    assert (fixture["total_positive_detected"], fixture["total_negative_rejected"]) == (80, 80)

    report = {
        "status": "pass",
        "actual_stored_model_outputs": {
            "total": 180,
            "unique_response_text_hashes": 180,
            "original_records": {
                "count": 120,
                "models": dict(Counter(row["model_requested"] for _, row in original)),
                "prompt_matches": 120,
                "evidence": "Stored full prompt/response, timestamp, requested and served model, and stop reason. Provider request IDs and token usage were not preserved in these legacy records.",
            },
            "openai_extension_records": {
                "count": 60,
                "models": dict(Counter(row["model_requested"] for _, row in extension)),
                "prompt_matches": 60,
                "unique_provider_response_ids": 60,
                "completed_provider_responses": 60,
                "served_snapshot_exact_matches": 60,
                "total_recorded_tokens": sum(row["usage"]["total_tokens"] for _, row in extension),
                "evidence": "Stored raw Responses API objects, unique response IDs, completion status, token usage, timestamps, hashes, and exact served snapshots.",
            },
        },
        "primary_rating_rows": {
            "count": 830,
            "all_scores_in_0_1_2": True,
            "all_120_original_responses_covered": True,
            "case_weighted_means_recomputed": manuscript_means,
            "provenance_limit": "Structured claim ratings are preserved, but raw primary-rater request/response objects were not preserved; numerical aggregation is reproducible, historical rater execution is not independently authenticated from provider metadata.",
        },
        "secondary_rating_rows": {
            "count": 30,
            "all_scores_in_0_1_2": True,
            "provenance_limit": "Score files and the local-rater script are preserved, but raw local-generation transcripts and run timestamps were not preserved in each record.",
        },
        "deterministic_verifier": {
            "fresh_rerun_matches_saved_decisions": True,
            "records": 180,
            "flags": dict(flags),
            "flags_by_model": dict(flags_by_model),
            "interpretation": "These are fresh code results over stored natural model outputs, not LLM-generated judgments.",
        },
        "seeded_conformance_controls": {
            "positive_detected": "80/80",
            "matched_negative_rejected": "80/80",
            "interpretation": "Executable synthetic unit controls. They are real test executions but not additional model responses and not an estimate of natural recall.",
        },
        "manual_flag_validation": {
            "confirmed": "9/9",
            "provenance_limit": "Author judgment, not blinded or independent. The new human packet is intended to replace or qualify this evidence.",
        },
    }
    destination = ROOT / "scoring" / "satml" / "execution_provenance_audit_v1.json"
    destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

