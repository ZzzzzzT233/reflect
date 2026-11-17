"""Command line entry point.

  python -m reflect.cli demo                  # 3-week demo with the real model (needs OPENAI_API_KEY)
  python -m reflect.cli demo --backend mock   # same pipeline, offline stand-in (plumbing test only)
  python -m reflect.cli add "Slept 6h, ..."   # add today's entry to your own journal
  python -m reflect.cli review                # weekly review for the current week
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from .agent import Reflect, week_start
from .db import Memory
from .llm import LLMError, get_backend
from .privacy import LoggedBackend, forget_day, read_log, wipe

ROOT = Path(__file__).resolve().parent.parent


def load_dotenv():
    env = ROOT / ".env"
    if env.exists():
        import os
        for line in env.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"'))


# ---------------------------------------------------------------- scoring
def f1(pred, gold):
    p, g = {x.lower() for x in pred}, {x.lower() for x in gold}
    if not p and not g:
        return 1.0
    if not p or not g:
        return 0.0
    tp = len(p & g)
    return 0.0 if tp == 0 else 2 * tp / (len(p) + len(g))


def score_extraction(pred: dict[str, dict], gold: dict[str, dict]) -> dict:
    n = len(gold)
    s = {"mood_exact": 0, "mood_within_1": 0, "sleep_within_0.5h": 0, "bedtime_exact": 0,
         "activities_f1": 0.0, "people_f1": 0.0, "followup_correct": 0}
    for d, gd in gold.items():
        pd = pred[d]
        s["mood_exact"] += pd["mood_score"] == gd["mood_score"]
        s["mood_within_1"] += abs(pd["mood_score"] - gd["mood_score"]) <= 1
        gs, ps = gd["sleep_hours"], pd.get("sleep_hours")
        s["sleep_within_0.5h"] += (gs is None and ps is None) or (gs is not None and ps is not None and abs(gs - ps) <= 0.5)
        s["bedtime_exact"] += (pd.get("bedtime") or None) == gd["bedtime"]
        s["activities_f1"] += f1(pd["activities"], gd["activities"])
        s["people_f1"] += f1(pd["people"], gd["people"])
        gf, pf = gd["suggestion_followup"], pd["suggestion_followup"]
        s["followup_correct"] += (gf["mentioned"] == bool(pf.get("mentioned"))) and \
                                 (not gf["mentioned"] or gf["followed"] == pf.get("followed"))
    return {k: round(v / n, 2) for k, v in s.items()}


# ---------------------------------------------------------------- report
def _checks_line(review: dict) -> str:
    c = review.get("checks") or {}
    if not c:
        return ""
    return (f"*checks: {len(c['first_draft_problems'])} problem(s) in first draft · {c['rewrites']} rewrite(s) · "
            f"{len(c['removed_sentences'])} sentence(s) removed · {len(c['final_problems'])} left*")


def review_md(ws: str, stats: dict, review: dict) -> str:
    t = stats["this_week"]
    head = (f"*{t['entries']} entries · avg mood {t['avg_mood']:+} · avg sleep {t['avg_sleep']}h · "
            f"{t['low_mood_days']} low-mood day(s) · {t['late_nights']} late night(s)*"
            if t.get("entries") else "*no entries this week*")
    q = stats.get("data_quality", {})
    lines = [f"### Weekly review — week of {ws}", head,
             f"*evidence: {review.get('evidence_level', '?')} · {q.get('total_entries', '?')} entries so far*",
             _checks_line(review), "",
             review.get("summary", ""), ""]
    if stats.get("last_suggestion_followup"):
        fu = stats["last_suggestion_followup"]
        lines += [f"**Last week’s suggestion:** {fu['suggestion']}  ",
                  f"**From the data:** {fu.get('rule_check', 'no checkable rule')} · {fu['self_report']}  ",
                  f"**Check-in:** {review.get('last_suggestion_check', '')}", ""]
    obs = stats.get("observations") or []
    if obs:
        lines.append("**Observations** (counts, not patterns): " + "; ".join(o["finding"] for o in obs))
        lines.append("")
    lines.append("**Patterns**")
    for p in review.get("patterns", []):
        lines.append(f"- {p.get('finding')} _({', '.join(p.get('evidence_dates', []))})_")
    s = review.get("suggestion") or {}
    lines += ["", f"**Suggestion for next week:** {s.get('text', '')}  ",
              f"_How we’ll check:_ {s.get('check', '')}", ""]
    return "\n".join(lines)


# The demo journal's follow-up labels assume this goal is active from week 2 on, so by default the demo
# keeps it fixed instead of using whatever the model suggests. --free-goal lets the model choose.
SCRIPTED_GOAL = {"text": "No deadline work after 12:30am on weeknights.",
                 "check": "bedtime before 01:00 on weeknights",
                 "rule": {"type": "bedtime_before", "time": "01:00", "weeknights_only": True}}


def cmd_demo(args):
    data = json.loads((ROOT / "data" / "demo_journal.json").read_text())
    gold = {e["date"]: e["gold"] for e in data}
    llm = get_backend(args.backend, gold)
    out = ROOT / "out"
    out.mkdir(exist_ok=True)
    db_path = out / f"demo_{args.backend}.sqlite"
    db_path.unlink(missing_ok=True)
    agent = Reflect(Memory(db_path), llm, scripted_goal=None if args.free_goal else SCRIPTED_GOAL)

    md = [f"# Reflect — 3-week demo run", "",
          f"Backend: **{llm.name}** · model: **{llm.model}** · journal: 21 synthetic entries "
          f"(fictional student, written for testing)", ""]
    if llm.name == "mock":
        md += ["> ⚠️ MOCK RUN: extraction returns the hand-written gold labels and the review is a "
               "template. This only proves the plumbing (memory, statistics, follow-up loop). "
               "Run with `--backend openai` for real model output.", ""]
    preds = {}
    for e in data:
        d, text = e["date"], e["text"]
        x, q = agent.add_entry(d, text)
        preds[d] = x
        print(f"{d}  mood {x['mood_score']:+d}  sleep {x.get('sleep_hours')}  bed {x.get('bedtime')}  "
              f"{','.join(x['activities'])}")
        md += [f"**{d}** — {text}  ",
               f"→ mood {x['mood_score']:+d} ({', '.join(x['emotions'])}) · sleep {x.get('sleep_hours')}h · "
               f"bed {x.get('bedtime')} · {', '.join(x['activities'])}"
               + (f" · with {', '.join(x['people'])}" if x['people'] else "")]
        if q:
            md.append(f"→ 🤖 *Reflect asks:* “{q}”")
            print(f"    Reflect asks: {q}")
        md.append("")
        if date.fromisoformat(d).weekday() == 6:  # Sunday -> weekly review
            ws = week_start(d)
            stats, review = agent.weekly_review(ws)
            md += ["---", review_md(ws, stats, review), "---", ""]
            print("\n" + review_md(ws, stats, review))

    sc = score_extraction(preds, gold)
    md += ["## Extraction accuracy vs hand labels (21 entries)", "",
           "| metric | score |", "|---|---|"] + [f"| {k} | {v} |" for k, v in sc.items()]
    md += ["", f"LLM calls: {llm.calls} · tokens: {llm.tokens}"]
    report = out / f"demo_report_{args.backend}.md"
    report.write_text("\n".join(md))
    print("\nExtraction accuracy:", sc)
    print(f"LLM calls: {llm.calls}, tokens: {llm.tokens}")
    print(f"Report written to {report}")


PERSONAL_DB = ROOT / "reflect.sqlite"
PERSONAL_LOG = ROOT / "api_log.jsonl"


def personal_agent(backend: str) -> Reflect:
    return Reflect(Memory(PERSONAL_DB), LoggedBackend(get_backend(backend), PERSONAL_LOG))


def cmd_add(args):
    agent = personal_agent(args.backend)
    d = args.date or date.today().isoformat()
    x, q = agent.add_entry(d, args.text)
    print(json.dumps(x, indent=1))
    if q:
        print("\nReflect asks:", q)


def cmd_review(args):
    agent = personal_agent(args.backend)
    ws = week_start(args.date or date.today().isoformat())
    stats, review = agent.weekly_review(ws)
    print(review_md(ws, stats, review))


def cmd_delete(args):
    res = forget_day(Memory(PERSONAL_DB), PERSONAL_LOG, args.date)
    print(f"Deleted {args.date}: {res['entries']} entry, {res['reviews']} review, {res['log_lines']} API-log lines.")


def cmd_wipe(args):
    if not args.yes:
        sys.exit("This deletes your whole journal and API log. Re-run with --yes to confirm.")
    res = wipe(Memory(PERSONAL_DB), PERSONAL_LOG)
    print(f"Deleted {res['entries']} entries, {res['reviews']} reviews, {res['log_lines']} API-log lines.")


def cmd_log(args):
    recs = read_log(PERSONAL_LOG)
    print(f"{len(recs)} calls to the model API logged in {PERSONAL_LOG.name}")
    for r in recs[-args.n:]:
        print(f"{r['time']}  {r['task']:<22} {r['chars_sent']:>6} chars")
        if args.show:
            print("   " + r["sent"][:500].replace("\n", "\n   "))


def main(argv=None):
    load_dotenv()
    ap = argparse.ArgumentParser(prog="reflect")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("demo"); p.add_argument("--backend", default="openai", choices=["openai", "mock"])
    p.add_argument("--free-goal", action="store_true", help="let the model set each week's goal")
    p.set_defaults(fn=cmd_demo)
    p = sub.add_parser("add"); p.add_argument("text"); p.add_argument("--date")
    p.add_argument("--backend", default="openai"); p.set_defaults(fn=cmd_add)
    p = sub.add_parser("review"); p.add_argument("--date")
    p.add_argument("--backend", default="openai"); p.set_defaults(fn=cmd_review)
    p = sub.add_parser("delete", help="delete one day of your journal"); p.add_argument("--date", required=True)
    p.set_defaults(fn=cmd_delete)
    p = sub.add_parser("wipe", help="delete your whole journal and API log"); p.add_argument("--yes", action="store_true")
    p.set_defaults(fn=cmd_wipe)
    p = sub.add_parser("log", help="show what was sent to the model API"); p.add_argument("-n", type=int, default=20)
    p.add_argument("--show", action="store_true", help="also print the text that was sent"); p.set_defaults(fn=cmd_log)
    args = ap.parse_args(argv)
    try:
        args.fn(args)
    except LLMError as e:
        sys.exit(f"Error: {e}")


if __name__ == "__main__":
    main()
