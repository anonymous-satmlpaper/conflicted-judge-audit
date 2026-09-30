# SaTML 2027 submission package

`main.tex` is the anonymous IEEE conference manuscript. It presents a standalone
30-case, six-model study and contains the required Open Science and LLM Usage
Considerations sections.

Build from this directory with `./build.ps1`. The checked PDF is copied to
`../../output/pdf/satml-2027-submission.pdf`.

Experiment entry points:

- `../../scripts/satml_audit.py`: data-integrity and statistical audit
- `../../scripts/satml_run.py`: pinned, resumable model runs
- `../../scripts/deterministic_audit.py`: deterministic verifier
- `../../tests/test_deterministic_audit.py`: 160 seeded conformance fixtures
- `../../scripts/validate_flags.py`: manual flag-record validation
- `../../scripts/verify_manuscript_claims.py`: offline cross-check of manuscript numbers
- `../../scripts/analyze_human_reviews.js`: validates and analyzes the completed author reviews
- `../../scripts/family_stratified_audit.py`: judge-excess test by source family on the 60 audited claims (output: `../../scoring/satml/family_stratified_audit_v1.json`)

Human validation in the anonymous release bundle:

- `HUMAN_VALIDATION.md`: reviewer and coordinator procedure
- `../../reviews/satml-human-validation-packet.xlsx`: blinded review packet
- `../../reviews/reviewer-A-completed.xlsx`: anonymized completed Reviewer A workbook
- `../../reviews/reviewer-B-completed.pdf`: completed Reviewer B review
- `HUMAN_VALIDATION_RESULTS.md`: derived agreement and decision summary
- `HELDOUT_PROTOCOL.md`: frozen-verifier protocol for new cases

Keep author names and affiliations out of the review version. Confirm all
submission metadata against the registered title and abstract before upload.
