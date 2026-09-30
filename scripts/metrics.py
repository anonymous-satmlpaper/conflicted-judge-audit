"""
metrics.py -- conventional-metric baseline (ROUGE-L) for comparison against
the 5-dimension rubric scores. Implemented directly (LCS-based) rather than
via the `rouge-score` package so there's no external dependency to install.

reference text = the case's ground_truth.supported_findings, joined --
this is the closest thing to a "reference summary" the case schema
provides, matching how the 2025 timeline-analysis paper (this benchmark's
closest prior work) evaluates against reference summaries.
"""

import re


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _lcs_len(a: list[str], b: list[str]) -> int:
    # Standard O(len(a)*len(b)) LCS length via DP.
    if not a or not b:
        return 0
    prev = [0] * (len(b) + 1)
    for i in range(1, len(a) + 1):
        curr = [0] * (len(b) + 1)
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                curr[j] = prev[j - 1] + 1
            else:
                curr[j] = max(prev[j], curr[j - 1])
        prev = curr
    return prev[len(b)]


def rouge_l(candidate: str, reference: str) -> dict:
    """Sentence-level ROUGE-L (LCS-based precision/recall/F1) between a
    candidate response and a reference text."""
    cand_tokens = _tokenize(candidate)
    ref_tokens = _tokenize(reference)
    lcs = _lcs_len(cand_tokens, ref_tokens)
    precision = lcs / len(cand_tokens) if cand_tokens else 0.0
    recall = lcs / len(ref_tokens) if ref_tokens else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


if __name__ == "__main__":
    # sanity check
    r = rouge_l("the cat sat on the mat", "the cat is on the mat")
    print(r)
    assert 0.7 < r["f1"] < 1.0
    print("ok")
