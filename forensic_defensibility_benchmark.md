# Beyond Textual Accuracy: Evaluating Evidence Grounding and Reliability in AI-Assisted Digital Forensics

**Status:** Working draft — Sections marked `[TODO: RUN EXPERIMENT]` require real data and must not be filled with invented numbers.
**Target format:** NeurIPS Datasets & Benchmarks Track style (rigor/structure), submission vehicle TBD (arXiv preprint first; D&B track, DFRWS, or an IEEE S&P workshop as realistic venues given timeline).

---

## 0. One-paragraph pitch (for yourself, not the paper)

Current evaluations of LLMs on digital forensic tasks measure how closely the model's output matches a reference answer in wording (BLEU/ROUGE) or general factual correctness. Neither captures whether a forensic *finding* is defensible — traceable to real evidence, correctly separating what was observed from what was inferred, and not over-attributing an action to a person without justification. We build a benchmark that measures this directly, using synthetic Android forensic cases with known ground truth, and test whether models that look good on conventional metrics actually hold up on forensic-specific ones.

---

## 1. Title options (pick one before you commit; don't keep switching after this)

1. **Beyond Textual Accuracy: Evaluating Evidence Grounding and Reliability in AI-Assisted Digital Forensics** ← recommended
2. Measuring Evidentiary Reliability of LLM-Generated Findings in Android Forensic Investigations
3. When Accuracy Isn't Enough: A Forensic Reliability Benchmark for AI-Assisted Digital Evidence Analysis

Use #1 in the paper. Use #2 if a reviewer/advisor pushes you to scope the title to match the (Android-only) experimental scope exactly — titles that promise more than the experiments deliver get dinged in review.

---

## 2. Abstract

> The increasing use of large language models (LLMs) to assist digital forensic investigations has outpaced the methodologies available to evaluate them. Existing evaluation efforts for LLM-assisted forensics measure output quality primarily through textual similarity to a reference summary (e.g., BLEU, ROUGE) or general-purpose factual correctness, approaches adapted from natural language generation that do not directly assess whether a forensic finding is *defensible*: traceable to authentic evidence, free of unsupported attribution, and correctly distinguishing observation from inference. A finding that closely matches a reference answer in wording may nonetheless be forensically unreliable — for instance, by attributing an action to a specific individual when the underlying evidence supports only an artifact-level observation. Existing benchmark efforts we are aware of evaluate forensic LLM performance primarily through task-specific output similarity (timeline reconstruction against reference summaries) or through the correctness of AI-generated forensic *code*, rather than the reliability of AI-generated forensic *findings*; we found limited evidence of systematic evaluation across dimensions such as provenance traceability, observation–inference separation, and attribution justification.
>
> This work introduces a benchmark for evaluating the evidentiary reliability of AI-generated forensic findings, independent of surface-level textual accuracy. We define reliability along five measurable dimensions — evidence support, provenance traceability, observation/inference separation, attribution justification, and reproducibility — and construct a dataset of 30 synthetic Android application forensic cases spanning four difficulty categories with known ground truth. Each case is analyzed by three LLMs (Claude Opus 5, Claude Sonnet 5, Claude Haiku 4.5) under a direct-prompting pipeline, and every generated finding (581 claims across 90 responses) is scored against the five dimensions. **`[PRELIMINARY — single annotator, inter-rater agreement not yet established]`** In this preliminary pass, the larger and mid-sized models cluster near ceiling on all five dimensions and are statistically indistinguishable from each other, while the smallest model scores significantly lower on evidence support, observation/inference separation, and reproducibility (Mann-Whitney U, p<0.000001, rank-biserial r=0.92) — driven substantially by a small number of outright factual errors against the provided evidence and a recurring pattern of treating ambiguous certificate metadata as confirmatory rather than neutral. Attribution-justification scores were at ceiling for all models across all cases, including all attribution-trap cases, a result we report but do not yet know how to generalize from. A preliminary, likely metric-confounded negative correlation between rubric score and a conventional text-similarity baseline (Spearman ρ=−0.32, p=0.002, n=90) is directionally consistent with — but not yet clean confirmation of — the paper's central claim. `[TODO: replace this paragraph once a second annotator's scores allow Krippendorff's alpha to be reported, and once RAG / claim-grounded pipeline conditions are run for RQ3.]` We discuss implications for the design of AI-assisted forensic tools intended to support, rather than replace, human examiner judgment.

**Note on wording:** every hedge above ("we are aware of," "limited evidence of," "we found") is intentional — do not tighten these to absolute claims ("no benchmark exists") until you've done the full systematic search in §9 and can defend it.

---

## 3. Introduction (full draft — safe to use as-is, no fabricated claims)

Large language models are increasingly used to assist digital forensic investigators in triaging and interpreting large volumes of digital evidence — application metadata, extracted strings, network artifacts, timelines, and communications. This assistance is valuable because investigations routinely involve more data than a human examiner can manually review, but it introduces a new evaluation problem: how do we know whether an AI-generated forensic finding can be trusted?

The digital forensics community has begun to evaluate LLMs on forensic tasks, but the evaluation methodology largely mirrors general-purpose NLP evaluation. Prior work on LLM-assisted forensic timeline analysis proposes ground-truth datasets and evaluates model output using BLEU and ROUGE — metrics that measure textual overlap with a reference summary, not whether the generated content is evidentially sound. Separately, benchmarking work for AI-generated forensic *tooling* (e.g., AutoDFBench) evaluates whether AI-generated code correctly performs forensic tasks such as string search or file carving, which is a software-correctness problem distinct from the reliability of an AI-generated forensic *finding* expressed in natural language.

Neither line of work directly measures the property that matters most in an investigative or evidentiary context: whether a stated finding is *defensible* — supported by evidence, correctly attributed, and distinguishable from speculation. Consider two superficially similar statements generated from the same underlying evidence (a network log showing a connection to a domain):

- "The application contacted `example[.]com`." — an observation, directly supported by the artifact.
- "The suspect accessed `example[.]com`." — an attribution claim, which may not be supported by the same evidence, since a device-level network event does not by itself establish which person initiated it.

A textual-similarity metric may score these two statements as nearly equivalent, since they share most of their words and structure. An investigator evaluating them for use in a report would not. This gap — between what conventional metrics capture and what forensic use actually requires — is the subject of this work.

We make the following contributions:

1. We identify a gap in existing LLM-forensics evaluation methodology: the absence of systematic measurement of evidentiary reliability (as opposed to textual or general factual accuracy) in AI-generated forensic findings.
2. We propose five measurable dimensions of forensic reliability — evidence support, provenance traceability, observation/inference separation, attribution justification, and reproducibility — with operational scoring criteria.
3. We construct a benchmark of synthetic Android application forensic cases with known ground truth, avoiding the use of real malware samples or law-enforcement case data.
4. We empirically evaluate multiple LLMs and pipeline configurations against this benchmark and report `[TODO: RUN EXPERIMENT]` whether conventional evaluation metrics correlate with, or diverge from, forensic-reliability scores.

---

## 4. Related work (draft — cite properly, do not copy phrasing from sources)

Structure this section around a **novelty matrix** (build the real one — template in §9) and organize the prose around these clusters. Paraphrase everything; these are pointers to what to read and cite, not text to lift.

**LLMs in digital forensics.** Cite the growing body of work applying LLMs to forensic tasks generally (local forensic LLMs, forensic log analysis, invocation-log forensic analysis of prompt-injection incidents). State plainly that LLM use in forensics is an active area, so your contribution is not "LLMs can help forensics" — that's established.

**LLM-forensics evaluation methodology.** This is your closest prior work — cite it carefully and specifically:
- The 2025 standardized-methodology/timeline-analysis paper (BLEU/ROUGE against ground-truth timelines). State explicitly what it measures and what it does not (textual similarity, single task domain).
- AutoDFBench (AI-generated forensic *code* evaluation against NIST CFTT-style ground truth). State explicitly this evaluates tool/code correctness, not natural-language finding reliability.
- Any ForensicLLM-style work reporting source-attribution or correctness/relevance metrics — read this closely before you finalize your novelty claim, since it's the paper most likely to already overlap with "attribution" as a dimension. Your job is to state precisely what it evaluates and how your attribution-justification dimension differs (if it differs).

**Claim grounding / provenance-aware AI reasoning (adjacent, non-forensic domains).** Cite ProvSEEK (provenance-grounded threat-intelligence agent) and GSAR (typed claim grounding for multi-agent diagnostic reports) as establishing that claim-level grounding against a provenance source is a known technique — used here to justify why you are *adapting*, not *inventing*, the grounding mechanism, and why your contribution is the forensic-specific evaluation framework built on top of it.

**Forensic admissibility and AI evidence (legal/governance literature).** Cite the doctrinal/legal papers on AI-generated forensic evidence admissibility and the practitioner "forensic readiness" literature to establish *why* this matters (regulatory and courtroom stakes), while being explicit that your contribution is empirical/technical evaluation, not legal analysis — this keeps you out of territory you're not qualified to claim.

---

## 5. Threat/problem framing

Not an attack framing — a reliability framing. State the pipeline plainly:

```
Digital evidence (Android artifact)
        ↓
Forensic parser / extractor
        ↓
Extracted evidence representation
        ↓
LLM (with or without RAG / grounding)
        ↓
Generated forensic finding(s)
        ↓
[THIS WORK] Reliability evaluation
        ↓
Investigator decision
```

State the assumption you're testing: that a finding scoring well on conventional metrics is assumed to be reliable, and that this assumption may not hold. Do not frame this as an "attacker" scenario — there is no adversary in this version of the idea; the risk is model unreliability under normal, non-adversarial use, which is arguably a more important problem to establish first (adversarial evidence injection remains a valid *follow-up* paper once this baseline exists, and you already have that framing worked out from earlier in this project if you want it later).

---

## 6. Research questions

- **RQ1:** Do conventional evaluation metrics (textual similarity, general factuality) correlate with forensic-reliability scores as defined in this work?
- **RQ2:** Which forensic-specific failure modes (unsupported attribution, inference mislabeled as observation, unresolved contradictions) are present in current LLM output, and how frequently?
- **RQ3:** Does pipeline configuration (direct prompting vs. RAG vs. claim-level grounding) affect forensic-reliability scores, and does it do so differently than it affects conventional metrics?
- **RQ4 (secondary/exploratory):** How consistently can human annotators apply the five-dimension rubric (inter-rater agreement)? — This one matters as much as the "real" RQs; if agreement is poor, that's a limitation you must report honestly, not bury.

---

## 7. The five-dimension rubric (operationalized)

Each dimension is scored per **finding** (an individual claim/sentence extracted from the model's output, not the response as a whole — you need claim-level granularity or the scoring is too coarse to be meaningful).

| # | Dimension | Definition | Scoring (3-point, per finding) |
|---|---|---|---|
| 1 | **Evidence support** | Is the finding stated as fact directly supported by an artifact in the case? | 0 = unsupported/fabricated; 1 = partially supported (plausible but not directly evidenced); 2 = fully supported |
| 2 | **Provenance traceability** | Can the finding be mapped to a specific source artifact and field? | 0 = no traceable source; 1 = traceable to artifact type only; 2 = traceable to specific field/value |
| 3 | **Observation/inference separation** | Does the finding correctly signal whether it is a direct observation or an inference/interpretation? | 0 = inference stated as fact with no hedge; 1 = ambiguous phrasing; 2 = clearly and correctly labeled |
| 4 | **Attribution justification** | If the finding attributes an action to a person/device/entity, is that attribution justified by the evidence? | 0 = unjustified attribution; 1 = weakly justified; 2 = well-justified or no attribution claim made |
| 5 | **Reproducibility** | Could a second examiner, given the same evidence bundle, arrive at the same finding through the same reasoning path? | 0 = not reproducible / reasoning not stated; 1 = partially reconstructable; 2 = fully reproducible |

**Annotator protocol:**
- Recruit 2–3 annotators with security/forensics background (classmates, colleagues, or yourself + 1–2 others — disclose exactly who in the paper's limitations; "the authors and N colleagues" is fine and common for small benchmark papers, just be honest about it).
- Annotators score independently, blind to which model/pipeline produced each finding (strip identifying formatting).
- Compute inter-rater agreement with **Krippendorff's alpha** (handles ordinal 3-point data and >2 raters better than Cohen's kappa).
- **Report the agreement number even if it's bad.** A benchmark paper that hides poor annotator agreement is far weaker than one that reports it honestly and discusses why (usually: dimension 3 and 4 are the hardest to agree on — expect this).

---

## 8. Benchmark construction — Android forensic cases

### 8.1 Case structure (template — reuse this exact schema for every case)

```json
{
  "case_id": "AND-001",
  "scenario": "short human-readable description",
  "artifacts": {
    "manifest": { "package_name": "...", "permissions": ["..."], "components": ["..."] },
    "strings": ["..."],
    "certificate": { "issuer": "...", "validity": "...", "self_signed": true },
    "network_indicators": [{ "domain": "...", "ip": "...", "source": "strings|manifest|traffic_log" }],
    "traffic_log": [{ "timestamp": "...", "domain": "...", "bytes": 0 }]
  },
  "ground_truth": {
    "supported_findings": ["The application requests INTERNET and READ_CONTACTS permissions.", "..."],
    "unsupported_claims_to_watch_for": ["Any claim that a specific person performed an action — no user-identity evidence exists in this case.", "..."],
    "known_contradictions": ["traffic_log shows no connection to domain X despite domain X appearing in strings — deliberate test of contradiction handling"]
  },
  "task_prompt": "Analyze this Android application's forensic artifacts and report security-relevant findings.",
  "difficulty_tag": "baseline | attribution_trap | contradiction | ambiguous_timestamp"
}
```

### 8.2 Case set composition (target: 30–50 cases for a first paper — do not over-scope)

- ~40% **baseline cases**: straightforward artifacts, clean ground truth, testing basic evidence-support and provenance.
- ~25% **attribution-trap cases**: evidence supports a device/app-level observation only; designed so a model *might* over-attribute to "the suspect" or "the user" — this is your RQ2 workhorse.
- ~20% **contradiction cases**: two artifacts that partially conflict (e.g., a string references a domain the traffic log never contacted) — tests dimension 3 and RQ2.
- ~15% **ambiguous/edge cases**: timezone ambiguity, missing fields, low-confidence indicators — tests whether models appropriately express uncertainty instead of asserting confidently.

### 8.3 Where the artifacts come from

- **Do not use real malware samples or real case data.** Build synthetic manifests/strings/certificates by hand or with a small generator script — you have the Android/APK domain knowledge to make these realistic (this is where your DroidScope experience is a direct asset, without needing to reference DroidScope itself).
- If you want realistic *structure*, you can pattern your synthetic manifests after publicly documented, well-known malware family behaviors described in public threat reports (cite the report, don't use the actual sample) — this keeps you legally and ethically clean while staying realistic.

---

## 9. Novelty matrix (fill this in yourself before writing the final Related Work — do not skip this)

| Paper | LLM+DF | Benchmark | Ground truth | Text-sim metrics | Evidence support | Provenance | Obs/Inference | Attribution | Reproducibility | Contradiction handling |
|---|---|---|---|---|---|---|---|---|---|---|
| Timeline analysis (2025) | ✅ | ✅ | ✅ | ✅ (BLEU/ROUGE) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| AutoDFBench | ✅ (code) | ✅ | ✅ | ❌ (F1/precision/recall on code output) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| ForensicLLM (Sharma et al., 2025) | ✅ (Q&A over forensic *literature*, not case evidence) | partial (2,244 held-out Q&A pairs, not forensic cases) | ✅ (reference answers from research papers + AGP artifact catalog) | ✅ (BERTScore, BGE-M3 embedding similarity, G-Eval-as-judge — all reference-answer-similarity metrics) | ❌ | ❌ (its "AGP" fields describe artifact *types*, not a specific case's evidence) | ❌ | ❌ *(see note)* | ❌ | ❌ |
| ProvSEEK | ❌ (CTI, not DF) | partial | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| GSAR | ❌ (ops, not DF) | partial | ✅ | ❌ | ✅ | partial | ✅ (typed claims) | ❌ | ❌ | ❌ |
| **This work** | ✅ | ✅ | ✅ | tracked for comparison | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

**ForensicLLM verification — done 2026-08-17.** Could not fetch the primary
PDF or ScienceDirect page directly (403 Forbidden on three independent
attempts — DFRWS-hosted PDF, ScienceDirect, LSU institutional repository
PDF). Findings below are from five independent secondary sources that
consistently corroborate each other: the LSU thesis repository landing
page (Binaya Sharma's thesis, which *is* this paper), the author's
personal academic site, DFRWS conference materials, and two independent
web searches pulling from the paper's own abstract/results text. This is
**not** a first-hand read of the full methodology section — treat the
conclusion below as well-supported but not 100%-verified, and re-check
directly if you get ScienceDirect/institutional access before finalizing
the paper.

- **What ForensicLLM's "source attribution" actually measures:** whether
  the model's answer correctly *cites the research paper* (author + title)
  it drew the answer from — reported as "86.6% of the time, with 81.2% of
  responses including both author and title." This is citation accuracy
  against a corpus of 1,082 digital-forensics research articles, not
  attribution of an observed action to a specific person or device within
  a case. It answers "did you cite the right paper," not "is it justified
  to say the suspect did this."
- **What the task actually is:** ForensicLLM is a RAFT-fine-tuned local
  LLaMA-3.1-8B trained on 6,739 Q&A pairs extracted from those research
  articles plus the Artifacts Genome Project (AGP) — a *catalog* of known
  artifact types (fields: Title, Type, Device, Path, Description,
  Comments, Search Tags, Data) used as reference knowledge for answering
  questions like "what artifact type is X" or "how does technique Y
  work." It is never given a specific case's evidence bundle and asked to
  produce a finding about that case — the AGP fields describe artifact
  *categories* in general, not one seized device's actual manifest,
  strings, or traffic log.
- **What "correctness" and "relevance" measure:** human-survey ratings of
  whether a Q&A answer is factually accurate and topically on-point
  relative to forensic literature — not whether a case finding is
  evidence-supported, correctly separates observation from inference, or
  avoids over-attributing an event to a person. The automated metrics
  (BERTScore, BGE-M3 cosine similarity, G-Eval) are all still
  reference-answer-similarity metrics, just semantic/embedding-based
  rather than n-gram-based like BLEU/ROUGE — the same category of
  evaluation this benchmark's whole pitch (§0) argues is insufficient,
  just a more sophisticated variant of it.
- **No source found any mention of:** observation/inference separation,
  evidence-to-specific-artifact-field traceability within a case,
  unsupported attribution of an action to a person/device, or
  reproducibility by a second examiner.

**Conclusion: limited overlap, no narrowing needed on this basis.**
ForensicLLM's "attribution" is a different construct from this
benchmark's attribution-justification dimension (citation-to-document vs.
action-to-person), and its task is literature Q&A, not case-artifact
analysis. If anything it *reinforces* the gap claim in §0/§2: it is
another example of forensic-LLM evaluation converging on
similarity-to-reference-answer (now via embeddings/G-Eval instead of
BLEU/ROUGE) rather than evidentiary reliability of case-level findings.
Cite it in Related Work as: closest attribution-adjacent prior work,
explicitly distinguished by task (literature Q&A vs. case-evidence
analysis) and by what "attribution" means in each.

**DFIR-Metric verification — done 2026-08-17.** Cherif, Bisztray,
Dubniczky, Aldahmani, Alshehhi & Tihanyi, *DFIR-Metric: A Benchmark
Dataset for Evaluating Large Language Models in Digital Forensics and
Incident Response*, ICONIP 2025 (spotlight); arXiv:2505.19973. Fetched
directly from arXiv (no access issues, unlike ForensicLLM above) --
higher confidence here.

- **Three modules, none of them open-ended finding generation.** Module
  I: 700 MCQ knowledge questions from certifications/documentation.
  Module II: 150 CTF-style tasks (log analysis, crypto puzzles) graded
  correct/incorrect against a solution key. Module III: 500 disk/memory
  cases from NIST's CFTT program, where the model must locate specific
  artifacts and emit a rigid structured output --
  `<inode>:<filename>` pairs prefixed `DELETED`/`LIVE` -- checked by an
  automated pipeline against a validated ground-truth baseline.
- **Metrics are all correctness-against-answer-key, not
  reliability-of-a-written-finding:** Confidence Index (did the model
  answer consistently across k samples), Reliability Score
  (+1 correct / 0 skip / -2 wrong), Task Understanding Score (fraction of
  rubric criteria met). None of these ask whether a natural-language
  finding is evidence-supported, correctly hedges inference, or avoids
  over-attribution -- they ask whether a structured extraction output
  matches ground truth.
- **The paper explicitly scopes out the stage this benchmark is about.**
  DFIR-Metric evaluates the first four stages of the NIST 800-86
  workflow (identify, collect, examine, analyze) and **explicitly
  excludes the final legal-reporting phase** -- the stage where an
  examiner writes the finding in prose and where over-attribution,
  unhedged inference, and provenance loss actually occur. This is about
  as clean a scope-boundary statement as a novelty matrix could ask for.
- **No mention of evidence-support scoring, provenance traceability,
  observation/inference separation, attribution justification, or
  second-examiner reproducibility** anywhere in the fetched content.

**Conclusion: no overlap, no narrowing needed.** DFIR-Metric measures
whether a model can correctly extract/classify structured artifacts and
answer knowledge/reasoning questions -- a real and useful but different
problem from whether a model's *written forensic finding* is defensible.
If anything this strengthens the gap claim further: it's a second,
more recent (2025), more rigorously-scoped benchmark that still stops
exactly at the boundary this work starts from. Cite alongside AutoDFBench
in Related Work as: benchmarks tool/task correctness for DFIR workflows,
explicitly excluding the reporting stage this work addresses.

| Paper | LLM+DF | Benchmark | Ground truth | Text-sim metrics | Evidence support | Provenance | Obs/Inference | Attribution | Reproducibility | Contradiction handling |
|---|---|---|---|---|---|---|---|---|---|---|
| DFIR-Metric (Cherif et al., ICONIP 2025) | ✅ | ✅ (700 MCQ + 150 CTF + 500 disk/memory cases) | ✅ | ❌ (structured-output exact-match + MCQ accuracy, not text similarity) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

---

## 10. Experimental design

**Systems compared:**
1. Baseline: direct prompting (evidence dump → LLM → findings)
2. RAG: evidence retrieved/structured before prompting
3. Claim-grounded: each generated claim checked against source evidence post-hoc (lightweight version of the grounding architectures discussed earlier in this project)

**Models:** at least 3, ideally spanning different providers/sizes to make the correlation result (RQ1) meaningful rather than a single-model anecdote. `[DECIDE: budget/API access constraints go here]`

**Independent variables:** model, pipeline configuration, case difficulty tag.
**Dependent variables:** five rubric scores (per finding, aggregated per case), conventional metrics (ROUGE-L or similar, plus a general factuality/grounding score using an existing off-the-shelf checker) for direct comparison.

**Statistical analysis plan:**
- Correlation (Spearman, since scores are ordinal) between conventional metric and each rubric dimension — this is the RQ1 result.
- Per-model, per-pipeline breakdown of rubric scores (descriptive + significance testing, e.g., Wilcoxon signed-rank for paired comparisons across pipelines on the same cases).
- Report effect sizes, not just p-values — reviewers increasingly expect this.

`[TODO: RUN EXPERIMENT — everything below this line in a real paper is empirical and must come from actual runs]`

---

## 11. Limitations (updated with real status as of 2026-08-17 — still refine after a second annotator's data lands)

- **Single annotator, zero inter-rater agreement computed.** This is the load-bearing limitation of the current draft, not a minor caveat. All scores in `scoring/PHASE3_RESULTS.md` (90 responses, 581 claims) come from one annotator. Krippendorff's alpha requires a second independent rater scoring a subset blind to model identity — this has not happened yet and cannot be simulated. Until it does, every quantitative result here is "one annotator's scores are internally consistent," not "the rubric is reliable across annotators."
- **Only Anthropic models tested (Opus 5, Sonnet 5, Haiku 4.5).** The plan called for models "ideally spanning different providers" — this didn't happen due to API access, not a methodological choice. The reported model-tier gap may not generalize to non-Anthropic models.
- **Only the direct-prompting pipeline was run.** RAG and claim-grounded pipeline configurations from §10 are designed but not executed — RQ3 (does pipeline configuration affect reliability scores differently than conventional metrics) is currently unanswered.
- **The conventional-metric baseline (ROUGE-L) has an unresolved confound.** The reference text (a joined bullet list) and candidate text (a full multi-section report) differ enough in structure that the observed negative correlation may be partly a verbosity artifact rather than a clean reliability-vs-similarity finding. See `scoring/PHASE3_RESULTS.md` RQ1 section for the specific fix needed before this number is trustworthy.
- Synthetic cases, not real investigative data — external validity to real casework is untested.
- Android-only scope — findings may not transfer to other artifact types (PDF, email, network capture) without further work.
- Rubric dimensions were designed by the authors, not validated against a larger forensic practitioner survey — state this as a threat to construct validity.
- Two cases (AND-002, AND-019) turned out to contain an unintentional evidentiary inconsistency (certificate expiry predating a logged traffic event) as a side effect of synthetic-date generation, discovered only because all three models independently flagged it. This means the `baseline` and `contradiction` case tags are not as cleanly separated in the current 30-case set as the design intended — a case-construction validation pass (checking all date fields for accidental inconsistencies before tagging) is needed before scaling further.

---

## 12. Ethics statement (short, required for most venues)

State plainly: no real case data, no real malware samples, no personally identifiable information used at any stage; synthetic cases were constructed to resemble realistic Android forensic scenarios without deriving from or including actual investigative material.

---

## 13. What you actually need — full checklist

**Data / content:**
- [ ] 30–50 synthetic Android forensic cases built to the schema in §8.1, spanning the four difficulty categories in §8.2
- [ ] Ground-truth findings and known "traps" (attribution/contradiction) written out per case, before running any model

**Access / infra:**
- [ ] API access to 3+ LLMs (budget for repeated runs across cases × pipelines × models)
- [ ] A lightweight evaluation harness: script that runs each case through each pipeline configuration and logs raw output
- [ ] A conventional-metric scorer (ROUGE implementation + an existing off-the-shelf grounding/factuality checker) for the comparison baseline

**People:**
- [ ] 2–3 annotators (yourself + colleagues) willing to score outputs against the rubric, blind to model identity
- [ ] Someone to sanity-check the rubric itself before full annotation begins (pilot on 5 cases first, refine rubric, then annotate the rest — don't skip the pilot)

**Writing/process:**
- [ ] The novelty matrix in §9 fully verified (read ForensicLLM in full — this is the one paper that could force a rescoping)
- [ ] A short pilot run (5 cases, 1 model) before committing to the full 30–50 case run, to catch schema/prompt problems early
- [ ] Decision on venue: arXiv preprint first (safe, fast, citable for CMU) → then target DFRWS / an IEEE S&P workshop / NeurIPS D&B 2027 depending on how strong the pilot results look

**Timeline (rough, fit to your August–October window):**
- Week 1: finalize rubric + pilot 5 cases + verify ForensicLLM overlap
- Weeks 2–3: build full case set (30–50) + evaluation harness
- Week 4: run full experiment, get annotator scores, compute inter-rater agreement
- Weeks 5–6: analysis, writing, figures
- Week 7: internal review, arXiv submission

This is tight but not impossible if you start the pilot this week rather than doing another round of idea-checking.
