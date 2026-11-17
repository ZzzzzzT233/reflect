"""Automatic checks on a weekly review.

agent.py runs find_problems() on every review the model writes. If it finds problems, the model is asked
to rewrite (up to MAX_REWRITES times). If problems are still left, scrub() removes them deterministically
(drops unsupported patterns and dates, fixes evidence_level, deletes offending sentences).
eval/review_eval.py uses the same definitions to score reviews.
"""
from __future__ import annotations

import re

MAX_REWRITES = 2

# wording that claims cause ("because of late nights", "exercise boosts your mood")
CAUSAL = re.compile(r"\b(caus(e|es|ed|ing)|because of|led to|leads to|due to|boost(s|ed|ing)?|"
                    r"improv(e|es|ed) your mood|makes? you|made you|result(s|ed)? in)\b", re.I)
# wording that suggests a relationship; only allowed when there IS enough evidence
HINT = re.compile(r"\b(affect(s|ed|ing)?|impact(s|ed)?|linked|link between|related to|associated|"
                  r"contribut\w*|tend(s|ed)? to)\b", re.I)
# wording that says there is no evidence; contradicts evidence_level == "enough"
NOT_ENOUGH = re.compile(r"(not enough (evidence|data|entries)|isn['’]t enough (evidence|data)|"
                        r"too few entries|no clear pattern)", re.I)


def expected_evidence(stats: dict) -> str:
    ok = stats["data_quality"]["enough_for_patterns"] and bool(stats["computed_patterns"])
    return "enough" if ok else "not_enough"


def review_texts(review: dict) -> dict[str, str]:
    s = review.get("suggestion") or {}
    out = {"summary": review.get("summary", ""), "last_suggestion_check": review.get("last_suggestion_check", ""),
           "suggestion": s.get("text", ""), "suggestion check": s.get("check", "")}
    for i, p in enumerate(review.get("patterns", [])):
        out[f"pattern {i + 1}"] = p.get("finding", "")
    return {k: v for k, v in out.items() if isinstance(v, str) and v}


def find_problems(review: dict, stats: dict) -> list[str]:
    probs = []
    exp = expected_evidence(stats)
    if review.get("evidence_level") != exp:
        probs.append(f'evidence_level must be "{exp}"')
    computed = {p["key"]: set(p["dates"]) for p in stats["computed_patterns"]} if exp == "enough" else {}
    if exp == "not_enough" and review.get("patterns"):
        probs.append("patterns must be [] because evidence is not enough")
    elif exp == "enough":
        for p in review.get("patterns", []):
            k = p.get("key")
            if k not in computed:
                probs.append(f'pattern "{k}" is not in DATA.computed_patterns; remove it')
                continue
            bad = [d for d in p.get("evidence_dates", []) if d not in computed[k]]
            if bad:
                probs.append(f'pattern "{k}" cites dates that are not in its evidence: {bad}')
    for field, text in review_texts(review).items():
        for m in CAUSAL.finditer(text):
            probs.append(f'causal wording "{m.group(0)}" in {field}; say "linked to" or describe what happened')
        if exp == "not_enough":
            for m in HINT.finditer(text):
                probs.append(f'relationship hint "{m.group(0)}" in {field}, but evidence is not enough')
    if exp == "enough" and NOT_ENOUGH.search(review.get("summary", "")):
        probs.append('summary says there is not enough evidence, but evidence_level is "enough"')
    return probs


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]


def scrub(review: dict, stats: dict) -> tuple[dict, list[str]]:
    """Last resort: fix what code can fix and delete sentences that still break the wording rules."""
    exp = expected_evidence(stats)
    review = dict(review)
    review["evidence_level"] = exp
    computed = {p["key"]: set(p["dates"]) for p in stats["computed_patterns"]} if exp == "enough" else {}
    pats = []
    for p in review.get("patterns", []) if exp == "enough" else []:
        if p.get("key") in computed:
            p = dict(p)
            p["evidence_dates"] = [d for d in p.get("evidence_dates", []) if d in computed[p["key"]]]
            pats.append(p)
    review["patterns"] = pats

    removed = []

    def clean(text: str, is_summary: bool) -> str:
        keep = []
        for s in _sentences(text):
            bad = CAUSAL.search(s) or (exp == "not_enough" and HINT.search(s)) or \
                  (exp == "enough" and is_summary and NOT_ENOUGH.search(s))
            (removed if bad else keep).append(s)
        return " ".join(keep)

    review["summary"] = clean(review.get("summary", ""), True)
    if not review["summary"]:  # everything was removed: fall back to a plain factual line
        tw = stats.get("this_week", {})
        review["summary"] = (f"This week you wrote {tw.get('entries', 0)} entries"
                             + (f", with an average mood of {tw['avg_mood']:+}." if tw.get("entries") else "."))
    if exp == "not_enough" and not NOT_ENOUGH.search(review["summary"]):
        review["summary"] = (review["summary"] + " There isn't enough evidence for a pattern yet.").strip()
    review["last_suggestion_check"] = clean(review.get("last_suggestion_check", ""), False)
    for p in review["patterns"]:
        p["finding"] = clean(p.get("finding", ""), False) or p.get("finding", "")
    s = dict(review.get("suggestion") or {})
    if s:
        s["text"] = clean(s.get("text", ""), False) or "Keep journaling every day, including your bedtime."
        s["check"] = clean(s.get("check", ""), False)
        review["suggestion"] = s
    return review, removed
