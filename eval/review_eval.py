"""Evaluate the WEEKLY REVIEW itself on test journals with known answers.

  python data/make_test_journals.py              # create the journals (once)
  python eval/review_eval.py                     # real model (needs OPENAI_API_KEY)
  python eval/review_eval.py --backend mock      # offline: tests the statistics + plumbing only

For each journal: feed the entries day by day, write a review at the end of each week, then check

  found        did the review report the pattern that is really there?        (clear_pattern)
  admits       did it say "not enough evidence" when it should?               (missing_days, no_pattern)
  false        did it claim a relationship that isn't there?                  (missing_days, no_pattern)
  invented     did it name a pattern the statistics never produced?           (all)
  bad dates    did it cite a day with no entry (a missing day)?               (all)
  ungrounded   did it cite a day that isn't part of that pattern's evidence?  (all)
  cite P / R   for the real pattern: share of cited dates that are true / share of true dates cited

The statistics layer (which patterns Python finds) is reported separately from what the LLM writes.
Output: out/review_eval_<backend>.md and .json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from reflect.agent import Reflect, week_start  # noqa: E402
from reflect.cli import load_dotenv, score_extraction  # noqa: E402
from reflect.db import Memory  # noqa: E402
from reflect.llm import get_backend  # noqa: E402

RELATIONSHIP = ("sleep_mood", "activity:", "people")
from reflect.checks import CAUSAL, HINT  # noqa: E402  (same definitions the agent's checker uses)


def review_text(review: dict) -> str:
    parts = [review.get("summary", ""), review.get("last_suggestion_check", "")]
    parts += [p.get("finding", "") for p in review.get("patterns", [])]
    s = review.get("suggestion") or {}
    parts += [s.get("text", ""), s.get("check", "")]
    return " ".join(x for x in parts if isinstance(x, str))


def is_relationship(key: str) -> bool:
    return key == "sleep_mood" or key == "people" or key.startswith("activity:")


def run_journal(path: Path, backend: str, out_dir: Path) -> dict:
    j = json.loads(path.read_text())
    entries = j["entries"]
    gold = {e["date"]: e["gold"] for e in entries}
    llm = get_backend(backend, gold)
    db = out_dir / f"{path.stem}_{backend}.sqlite"
    db.unlink(missing_ok=True)
    agent = Reflect(Memory(db), llm)

    first = date.fromisoformat(entries[0]["date"])
    weeks = sorted({week_start(e["date"]) for e in entries} | {week_start("2026-11-02")})
    last_week = week_start("2026-11-22")
    weeks = [w for w in _all_weeks(weeks[0], last_week)]
    entry_dates = {e["date"] for e in entries}

    preds, reviews = {}, []
    for ws in weeks:
        for e in [e for e in entries if week_start(e["date"]) == ws]:
            x, _ = agent.add_entry(e["date"], e["text"])
            preds[e["date"]] = x
        stats, review = agent.weekly_review(ws)
        reviews.append((ws, stats, review))

    exp = j["expected"]
    per_week = []
    for ws, stats, review in reviews:
        computed = {p["key"]: set(p["dates"]) for p in stats["computed_patterns"]}
        rkeys = [p.get("key", "") for p in review.get("patterns", [])]
        invented = [k for k in rkeys if k not in computed]
        cited = [(p.get("key", ""), d) for p in review.get("patterns", []) for d in p.get("evidence_dates", [])]
        bad_dates = [d for _, d in cited if d not in entry_dates]
        ungrounded = [d for k, d in cited if k in computed and d not in computed[k]]
        per_week.append({
            "week": ws, "entries_so_far": stats["data_quality"]["total_entries"],
            "stats_keys": sorted(computed), "review_keys": rkeys,
            "observations": [o["key"] for o in stats.get("observations", [])],
            "evidence_level": review.get("evidence_level"),
            "invented": invented, "bad_dates": bad_dates, "ungrounded": ungrounded,
            "summary": review.get("summary", ""),
            "first_draft_problems": (review.get("checks") or {}).get("first_draft_problems", []),
            "rewrites": (review.get("checks") or {}).get("rewrites", 0),
            "removed": (review.get("checks") or {}).get("removed_sentences", []),
            "causal": [m.group(0) for m in CAUSAL.finditer(review_text(review))],
            "hints": [m.group(0) for m in HINT.finditer(review_text(review))]
                     if review.get("evidence_level") == "not_enough" else [],
        })

    final = per_week[-1]
    final_review = reviews[-1][2]
    res = {"journal": path.stem, "kind": j["kind"], "entries": len(entries), "weeks": per_week,
           "invented": sum(len(w["invented"]) for w in per_week),
           "bad_dates": sum(len(w["bad_dates"]) for w in per_week),
           "ungrounded": sum(len(w["ungrounded"]) for w in per_week),
           "causal": sum(len(w["causal"] or []) for w in per_week),
           "hints": sum(len(w["hints"]) for w in per_week),
           "first_draft_problems": sum(len(w["first_draft_problems"]) for w in per_week),
           "rewrites": sum(w["rewrites"] for w in per_week),
           "removed": sum(len(w["removed"]) for w in per_week)}

    # what the statistics layer found at the end (independent of the LLM)
    res["stats_found"] = final["stats_keys"]
    res["stats_false"] = [k for k in final["stats_keys"] if is_relationship(k) and exp["no_relationship_patterns"]]

    # what the review says
    res["final_evidence"] = final["evidence_level"]
    res["admits_ok"] = final["evidence_level"] == exp["final_evidence"]
    if exp["final_evidence"] == "not_enough":
        # every week should admit it, not only the last one
        res["admits_ok"] = all(w["evidence_level"] == "not_enough" for w in per_week)
    res["found"] = [k for k in exp["must_find"] if k in final["review_keys"]]
    res["found_ok"] = len(res["found"]) == len(exp["must_find"])
    res["false_claims"] = [k for w in per_week for k in w["review_keys"]
                           if is_relationship(k) and exp["no_relationship_patterns"]]

    # citation precision / recall for the true pattern
    if exp["allowed_dates"]:
        truth = set(exp["allowed_dates"]["sleep_mood"])
        cited = {d for p in final_review.get("patterns", []) if p.get("key") == "sleep_mood"
                 for d in p.get("evidence_dates", [])}
        res["cite_precision"] = round(len(cited & truth) / len(cited), 2) if cited else None
        res["cite_recall"] = round(len(cited & truth) / len(truth), 2)

    res["pass"] = (res["found_ok"] and res["admits_ok"] and not res["false_claims"]
                   and res["invented"] == 0 and res["bad_dates"] == 0 and res["ungrounded"] == 0
                   and (res.get("cite_precision") in (None, 1.0) or not exp["allowed_dates"]))
    res["extraction"] = score_extraction(preds, gold)
    res["llm_calls"], res["tokens"] = llm.calls, llm.tokens
    return res


def _all_weeks(first_ws: str, last_ws: str):
    d = date.fromisoformat(first_ws)
    end = date.fromisoformat(last_ws)
    while d <= end:
        yield d.isoformat()
        d = date.fromordinal(d.toordinal() + 7)


def report(results: list[dict], backend: str, model: str) -> str:
    md = [f"# Weekly review evaluation — backend: {backend} ({model})", ""]
    if backend == "mock":
        md += ["> MOCK RUN: extraction returns the gold labels and the review text is a template that copies "
               "the computed patterns. This tests the **statistics layer and the plumbing** only. "
               "Run with the real model to test what the LLM writes.", ""]
    md += ["| journal | entries | stats found | review evidence | found real pattern | false claims | invented | "
           "bad dates | ungrounded | cite P / R | causal words | hints w/o evidence | 1st-draft problems | "
           "rewrites | sentences removed | pass |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        cp = f"{r.get('cite_precision')} / {r.get('cite_recall')}" if "cite_recall" in r else "–"
        md.append(f"| {r['journal']} | {r['entries']} | {', '.join(r['stats_found']) or '—'} | {r['final_evidence']} | "
                  f"{'✓' if r['found_ok'] else '✗'} | {len(r['false_claims'])} | {r['invented']} | {r['bad_dates']} | "
                  f"{r['ungrounded']} | {cp} | {r['causal']} | {r['hints']} | {r['first_draft_problems']} | {r['rewrites']} | {r['removed']} | "
                  f"{'✅' if r['pass'] else '❌'} |")
    md += ["", "*causal words* = phrases like “because of”, “boosts”, “led to” in any review; "
           "*hints w/o evidence* = “affected”, “linked”, “tended to”… in a review that said evidence is not enough. "
           "Both are reported, not part of pass/fail. *1st-draft problems* = rule breaks the checker found in the "
           "model's first draft (all weeks); *rewrites* = times the review was sent back; *sentences removed* = "
           "deleted by the last-resort scrub.", "", "## Pass rate by kind", "", "| kind | passed |", "|---|---|"]
    for kind in ("clear_pattern", "missing_days", "no_pattern"):
        rs = [r for r in results if r["kind"] == kind]
        if rs:
            md.append(f"| {kind} | {sum(r['pass'] for r in rs)} / {len(rs)} |")
    md += ["", "## What each review said (final week)", ""]
    for r in results:
        md.append(f"- **{r['journal']}** — {r['weeks'][-1]['summary']}")
    md += ["", "## Extraction accuracy on these journals", "", "| journal | mood ±1 | sleep ±0.5h | bedtime | activities F1 |",
           "|---|---|---|---|---|"]
    for r in results:
        e = r["extraction"]
        md.append(f"| {r['journal']} | {e['mood_within_1']} | {e['sleep_within_0.5h']} | {e['bedtime_exact']} | "
                  f"{e['activities_f1']} |")
    md += ["", f"LLM calls: {sum(r['llm_calls'] for r in results)} · tokens: {sum(r['tokens'] for r in results)}"]
    return "\n".join(md)


def main():
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="openai", choices=["openai", "mock"])
    ap.add_argument("--only", help="substring filter on journal file names")
    a = ap.parse_args()
    files = sorted((ROOT / "data" / "test_journals").glob("*.json"))
    if a.only:
        files = [f for f in files if a.only in f.name]
    if not files:
        sys.exit("No test journals. Run: python data/make_test_journals.py")
    out = ROOT / "out"
    out.mkdir(exist_ok=True)
    results = []
    for f in files:
        print("running", f.stem, "...", flush=True)
        results.append(run_journal(f, a.backend, out))
    model = get_backend(a.backend, {}).model
    (out / f"review_eval_{a.backend}.json").write_text(json.dumps(results, indent=1))
    md = report(results, a.backend, model)
    (out / f"review_eval_{a.backend}.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
