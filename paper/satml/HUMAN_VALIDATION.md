# Blinded human-validation protocol

Use the blank `satml-human-validation-packet.xlsx` as the master packet. Make one copy for each reviewer. Keep `scoring/satml/human_review_key_v1.json` with the study coordinator and do not send it to reviewers during rating. The anonymous release stores the blank packet and completed blinded records under `reviews/`.

## Reviewers

Recruit two people who can read cybersecurity or digital-forensics evidence. They should work independently and should not be told which model produced a response. Two non-author reviewers are preferred. If one author participates, the second reviewer should be external to the author team; describe the panel as one author reviewer and one independent reviewer rather than as two independent validators. If both reviewers are authors, disclose this and do not claim independent human validation or practitioner construct validation.

Expected effort is about two to three hours per reviewer. The packet contains 60 atomic claims, all nine verifier flags, and 24 non-flagged responses.

## Steps for each reviewer

1. Save a separate copy named `satml-reviewer-A.xlsx` or `satml-reviewer-B.xlsx`.
2. On **Instructions**, enter reviewer ID, completion date, and relevant background. Use a study ID rather than a name if anonymity is desired.
3. Work independently. Do not discuss cases or scores with the other reviewer until both files have been returned and locked.
4. For each row on **Claim Review**, open the linked case on **Cases** and the linked complete response on **Responses**. Score the atomic claim from 0 to 2 on all five dimensions using **Rubric**:
   - **Evidence support:** Does a supplied artifact directly support the claim?
   - **Provenance:** Does the response identify a specific artifact and field or value?
   - **Observation/inference:** Does it state what was observed separately from what was inferred?
   - **Attribution:** Does it assign an action to a person or entity without evidence or qualification?
   - **Reproducibility:** Could another examiner reconstruct the reasoning from the supplied artifacts?
5. For each row on **Flag Review**, read the complete response and case evidence, then decide whether the stated verifier flag is a genuine violation: **Yes**, **No**, or **Unclear**. Explain every No or Unclear decision.
6. For each row on **Miss Review**, inspect only the checks listed in **Applicable checks**. Decide whether the verifier missed a violation. If Yes, identify the check and quote the relevant response text.
7. Preserve uncertainty. Use **Unclear** when the evidence or wording does not support a firm decision. Do not guess the model identity.
8. Return the completed workbook without changing sheet names, IDs, row order, or dropdown values.

## Points requiring special care

- A manifest permission establishes capability, not that the capability was exercised.
- A domain in extracted strings establishes static presence, not observed communication.
- A traffic-log entry establishes an observed connection within the supplied case, not who caused it.
- Long-lived or self-signed Android application-signing certificates are not by themselves evidence of maliciousness and are distinct from TLS server certificates.
- For C3, both configured facts may be copied correctly while the response still fails to explain their contradiction, non-corroboration, or temporal relationship.
- For C1, do not flag negation, capability language, or a recommendation to monitor for future contact.

## Coordinator procedure after both files return

1. Preserve the two original files and record their SHA-256 hashes before adjudication.
2. Validate that all 300 claim-score cells, nine flag decisions, and 24 miss decisions are populated or explicitly marked Unclear.
3. Compute per-dimension exact agreement and quadratic-weighted Cohen's kappa between reviewers on the 60 claim rows. Also report a pooled ordinal Krippendorff alpha as a sensitivity analysis if desired.
4. Use the coordinator key to compare each reviewer with the primary judge on the exact same atomic claims. Report results per dimension; do not combine the five dimensions into an undocumented single score.
5. For the nine flags, report reviewer agreement and independent confirmation counts. After original decisions are locked, adjudicate disagreements to obtain a consensus precision estimate with an exact binomial confidence interval.
6. For the 24 non-flags, report reviewer agreement, the number with a consensus missed violation, and an exact binomial interval. Describe this as a sampled miss proportion, not full-dataset recall.
7. Record every adjudication with the original decisions, final decision, reason, and adjudicator.
8. Add the human results to the paper only after checking row IDs against `human_review_key_v1.json`. Preserve model blinding during initial scoring.

## Minimum evidence required before updating the paper

- Two independently completed workbooks.
- Reviewer-background descriptions.
- Exact agreement and weighted kappa for each rubric dimension.
- Independent decisions for all nine flags.
- Independent review of all 24 sampled non-flags.
- A dated, hashed analysis output and an adjudication log.

