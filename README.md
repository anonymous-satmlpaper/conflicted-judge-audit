# Anonymous artifact for SaTML 2027 review

This release supports the manuscript “Auditing a Conflicted Judge: Hybrid
Verification for an LLM-Scored Forensic Reliability Benchmark.” It contains
frozen benchmark inputs, preserved model outputs, scoring records, deterministic
verification code, conformance tests, author-audit records, and manuscript source.

No API key or provider credential is included. The incomplete Qwen3 pilot is
excluded from all comparisons and from this release.

## Main checks

From the artifact root, run:

```text
python scripts/verify_manuscript_claims.py
python tests/test_deterministic_audit.py
```

The claim checker uses only the Python standard library and preserved outputs.
The test file executes the 160 seeded verifier fixtures: 20 positive and 20
matched negative fixtures for each of C1--C4.

`scoring/satml/family_stratified_audit_v1.json` holds the family-stratified
judge-excess test (Table VII), including the 60 per-claim primary and mean
author scores it is computed from. `scripts/family_stratified_audit.py`
produced it from the internal review records, which are not released in
original form. The per-claim rows are sufficient to recompute every reported
statistic.

## Layout

- `cases/`: 30 synthetic Android-forensics cases.
- `outputs/harness/`: 120 Claude/Qwen response records.
- `outputs/satml/legacy/`: 60 preserved OpenAI extension records.
- `outputs/second_rater/`: the 30-response cross-family rater sample.
- `scoring/`: primary scores and frozen audit summaries.
- `scripts/` and `tests/`: verifier, analyses, and conformance suite.
- `reviews/`: anonymized completed records for Reviewer A and Reviewer B,
  blank review packet, and anonymized derived agreement results.
- `paper/`: anonymous LaTeX source and reproducibility documentation.

## Human-audit provenance

Reviewer A and Reviewer B completed their model-blinded reviews separately. The
authors report that all scores and decisions were selected and filled manually.
They consulted ordinary websites and reference material; any LLM assistance was
limited to editorial phrasing after the judgments. Both reviewers are paper
authors, so the manuscript describes this as an author audit rather than
independent external validation.

The release includes one completed record for each reviewer. Reviewer A's
workbook withholds identity and background; all scored claim, flag, and
miss-review cells were verified unchanged from the completed internal record.

## Frozen scope

The natural-output verifier findings are specific to the preserved outputs. The
seeded conformance suite establishes implementation behavior for C1--C4, not
recall over unrestricted natural language. Do not use the API-running scripts to
replace frozen responses when reproducing the paper's reported numbers.
