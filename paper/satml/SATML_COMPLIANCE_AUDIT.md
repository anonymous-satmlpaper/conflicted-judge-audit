# SaTML 2027 compliance audit

Audit date: 28 September 2026

Official source: <https://satml.org/call-for-papers/>. The full Call for Papers
takes precedence over any third-party review or summary.

## Implemented

- Corrected “three questions” to “four questions” for RQ1--RQ4.
- Retained the IEEE conference class at default 10pt geometry.
- Confirmed the review PDF is eight pages total, below the research-paper limit
  of 12 pages of body text. References and appendices have no stated limit.
- Kept the required Open Science and LLM Usage Considerations sections.
- Retained the order `Open Science` → `LLM Usage Considerations` → `Ethical
  Considerations` → `References`. The CFP simultaneously says Open Science is
  immediately before references, requires LLM Usage after Open Science and before
  references, and says optional Ethical Considerations is immediately before
  references. Those three literal statements cannot all hold. The manuscript
  follows the more specific LLM ordering and puts Ethics directly before the
  references. Moving Open Science last, as suggested in the supplied critique,
  would directly violate the LLM-after-Open-Science rule.
- Verified all 14 bibliography records. Replaced outdated preprint citations
  with archival publication records where available and added page/DOI details.
- Verified that abstract and table values pass the repository's offline claim
  checker.
- Verified the final PDF has no author metadata and no matches for the tested
  identity strings.
- Created `output/artifact/satml-reviewer-A-anonymized.xlsx`. Reviewer ID and
  background are withheld, the cover-sheet assistance note reflects the authors'
  confirmed process, and all claim, flag, and miss-review cells are byte-for-byte
  equivalent at the value level to the internal workbook.
- Describes the author audit as two separately completed, model-blinded manual
  reviews and releases one anonymized completed record for each reviewer.

## Submission-system actions

- Make the final PDF title and abstract match the registered HotCRP record. The
  CFP permits no substantial post-registration changes.
- Confirm fixed authors and affiliations, topics, ORCIDs, author certifications,
  and all conflicts. Re-check conflicts during the final 24 hours.
- Enter `N/A` in the mandatory “New Insights” field for this research paper.
- Confirm the author-reviewer nomination and the nominee's conflicts.
- Add a fully anonymous artifact-repository URL in HotCRP, update it by 2 October
  2026, then keep it accessible and unchanged during review.
- Have every author approve the PDF, disclosure, and artifact before upload.

## Unresolved policy conflict

The paper previously received a NeurIPS workshop review. SaTML's full CFP says
that prior reviews from the last submission must be appended, anonymized but
otherwise complete and unedited, together with a description of how they were
addressed. It applies whenever a paper was previously submitted and received
reviews; it is not limited to archival venues. The current PDF omits those reviews
at the authors' explicit direction. Therefore the current PDF is **not fully
compliant with the published prior-review rule** and carries a desk-rejection
risk even if the workshop was non-archival. Only the SaTML PC chairs can grant or
confirm an exception.

## Remaining deadline facts

- Paper deadline: 29 September 2026, 11:59 PM AoE.
- Anonymous artifact update deadline: 2 October 2026, 11:59 PM AoE.
- By submitting, authors commit to the full review process and generally cannot
  withdraw before the decision.
