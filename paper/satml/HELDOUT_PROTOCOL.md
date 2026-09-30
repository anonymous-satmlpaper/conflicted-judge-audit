# Frozen held-out verifier evaluation

This protocol is for the strongest remaining experiment. It must be run on cases and model responses that were not used to design verifier version `satml-deterministic-v1`.

1. Freeze `scripts/deterministic_audit.py`, `tests/test_deterministic_audit.py`, and `scoring/satml/fixture_validation_v1.json`. Record their SHA-256 hashes and the freeze date.
2. Author 60 or more new synthetic cases using the existing JSON schema. Include natural opportunities for every check, but do not edit the verifier after seeing responses.
3. Before model generation, have a person who did not write the verifier label each case's C1--C4 applicability from structured artifacts.
4. Run at least one frontier and one compact endpoint on every held-out case with the same prompt and recorded inference settings.
5. Run the frozen verifier once. Preserve complete outputs, applicability decisions, flags, witnesses, case hashes, prompt hashes, and verifier hashes.
6. Give all flags and a random sample of at least 25 applicable non-flags to two blinded independent reviewers. Use the definitions in `HUMAN_VALIDATION.md`.
7. Report per-check applicable counts, flags, consensus true positives, consensus false positives, sampled misses, and exact binomial intervals. Do not tune rules on this split.
8. If a rule change is necessary, version it as a new verifier and treat the current held-out set as development data. Obtain a new untouched test set before making a confirmatory claim.

Until this protocol is completed, the manuscript correctly describes the current verifier as a post-hoc audit on one synthetic dataset.

