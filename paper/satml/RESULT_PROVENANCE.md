# Result provenance audit

The manuscript numbers are calculations over concrete local records. They are not invented prose. Their evidentiary strength differs by result type.

| Manuscript claim | Direct source | What was independently rechecked | Provenance limitation |
|---|---|---|---|
| 30 cases | `cases/AND-001.json` through `AND-030.json` | File count, identifiers, prompt reconstruction | Cases are synthetic by design |
| 180 responses, six systems | 120 files in `outputs/harness/` and 60 GPT files in `outputs/satml/legacy/` | Every case/model pair exists; prompts match cases; responses are nonempty and have 180 unique text hashes | The 120 legacy records lack provider request IDs and token usage |
| GPT-5.5 and GPT-5.4 Mini: 30 each | 60 GPT response records | 60 unique provider response IDs; status completed; exact served snapshot; usage and hashes present | Local files still require trustworthy artifact custody |
| 830 primary-rated claims | `scoring/all_scores.json` | Count, 0/1/2 range, 120-response coverage, and case-weighted table means | Raw primary-rater API objects were not preserved, so the aggregation is reproducible but historical rater execution is not independently authenticated |
| Cross-rater diagnostic, 30 responses | `outputs/second_rater/*.json` and `scoring/satml/legacy_audit.json` | Count, score ranges, case coverage, and statistics | Raw local-rater transcripts and per-run timestamps were not preserved; the unit mismatch remains |
| Nine natural-output flags | `outputs/satml/deterministic_audit_v1.json` | The verifier was run again over all 180 stored responses; every flag and witness matched | Rules are narrow and post-hoc |
| 9/9 confirmation | `scoring/satml/flag_validation_v1.json` | All nine decisions and rationales exist | This is author judgment and is not blinded or independent |
| 160 controls; 80/80 positive and 80/80 negative | `tests/test_deterministic_audit.py` and `scoring/satml/fixture_validation_v1.json` | Tests execute the production verifier functions and pass | These are synthetic unit controls, not 160 model executions and not natural-language recall |

Run the complete local check with:

```powershell
.\.tools\python313\python.exe scripts\deterministic_audit.py --inputs outputs/harness outputs/satml/legacy --include-model claude-opus-5 --include-model claude-sonnet-5 --include-model claude-haiku-4-5 --include-model qwen2.5:7b --include-model gpt-5.5-2026-04-23 --include-model gpt-5.4-mini-2026-03-17 --output tmp/provenance_audit_rerun.json
.\.tools\python313\python.exe tests\test_deterministic_audit.py -v
.\.tools\python313\python.exe scripts\verify_manuscript_claims.py
.\.tools\python313\python.exe scripts\audit_execution_provenance.py
```

The generated audit is `scoring/satml/execution_provenance_audit_v1.json`.

