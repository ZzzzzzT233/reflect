"""The Reflect agent: extract -> remember -> find patterns -> review -> follow up.

Design choice: the LLM does the language work (reading entries, writing the
review), while counting and pattern statistics are computed in plain Python so
the review can only cite patterns that are actually in the data.
"""
from __future__ import annotations

import json
import random
from datetime import date, timedelta
from statistics import mean

from .checks import MAX_REWRITES, find_problems, scrub
from .db import Memory

ACTIVITIES = ["exercise", "studying", "deadline_work", "class", "social", "family_call",
              "outdoors", "rest", "screen_time", "chores"]
EMOTIONS = ["admiration", "amusement", "anger", "annoyance", "approval", "caring", "confusion",
            "curiosity", "desire", "disappointment", "disapproval", "disgust", "embarrassment",
            "excitement", "fear", "gratitude", "grief", "joy", "love", "nervousness", "optimism",
            "pride", "realization", "relief", "remorse", "sadness", "surprise", "neutral"]

EXTRACT_SYSTEM = f"""You read one private journal entry and return structured data as JSON.
Return exactly these keys:
- mood_score: integer from -2 (very bad) to 2 (very good), overall mood of the day
- emotions: 1-3 labels, only from {EMOTIONS}
- sleep_hours: number of hours slept LAST NIGHT if stated or clearly implied, else null
- bedtime: time they went to bed LAST NIGHT as "HH:MM" 24h (e.g. "01:30"), else null
- activities: only from {ACTIVITIES}
- people: short names/roles of people they spent time with or talked to (e.g. "Mia", "mom"), [] if none
- stressors: 0-3 short phrases naming EXTERNAL causes of stress (e.g. "problem set", "midterm",
  "group project", "argument with roommate"). Never feelings or mood words ("tired", "felt awful",
  "everything felt heavy" are NOT stressors; they belong in mood_score/emotions). [] if none
- highlights: 0-2 short phrases
- suggestion_followup: {{"mentioned": bool, "followed": true/false/null, "evidence": short quote or ""}}
  about the ACTIVE SUGGESTION given below (mentioned=false if the entry says nothing about it)
- risk_flag: true only if the entry suggests self-harm or a crisis
Do not invent facts that are not in the entry."""

QUESTION_SYSTEM = """You are Reflect, a warm, brief journaling companion. Given today's extracted data,
what is missing, and the user's active goal, ask ONE short follow-up question (max 20 words)
that would most help the weekly review. Prefer asking about the active goal if today's entry didn't
mention it. Return JSON: {"question": "..."}"""

REVIEW_SYSTEM = """You are Reflect, a warm but concrete journal coach writing a student's weekly review.
Rules:
- Patterns: ONLY those listed in DATA.computed_patterns (they passed a statistical check). Never invent one,
  and never turn a single day into a pattern. For each, copy its "key" and cite dates ONLY from its "dates".
- DATA.observations are simple counts (e.g. a stressor that came up 4 times). You may mention them in the
  summary, but they are NOT patterns: never put them in "patterns" and they never make evidence "enough".
- If DATA.computed_patterns is empty, or DATA.data_quality.enough_for_patterns is false, return
  "patterns": [] and set "evidence_level": "not_enough". Say plainly in the summary that there isn't
  enough evidence yet for a pattern (and why: too few entries, missing days, or no clear relationship).
  Otherwise set "evidence_level": "enough".
- Mood is on a -2..+2 scale: -2 very bad, -1 low, 0 neutral, +1 good, +2 very good. So an average of
  +1 is a GOOD week, 0 is neutral, below 0 is low. Describe averages accordingly.
- Patterns are exploratory: say "linked to" / "tended to". Never say or imply cause: avoid "causes",
  "because of", "led to", "due to", "boosts", "improves your mood", "makes you".
- When evidence_level is "not_enough", do not hint at ANY relationship either (no "late nights may have
  affected your mood", no "linked", "related", "tended to"). Just describe what happened and say more
  entries are needed.
- Start by checking last week's suggestion using DATA.last_suggestion_followup (be honest, kind, specific).
- End with exactly ONE small, specific suggestion for next week that the user can verify from their journal.
  If evidence is not enough, the suggestion can simply be to keep journaling (e.g. include bedtime every day).
- Plain, friendly English. No therapy jargon. Not medical advice. If any day has risk_flag=true,
  gently encourage reaching out to someone they trust or a professional.
Return JSON: {"summary": "2-3 sentences", "evidence_level": "enough" | "not_enough",
"patterns": [{"key": "<key from computed_patterns>", "finding": "...", "evidence_dates": ["YYYY-MM-DD"]}],
"last_suggestion_check": "1-2 sentences",
"suggestion": {"text": "...", "check": "how the journal will show it", "rule": <one rule below>}}
The suggestion's "rule" must let the app check it from the journal data. Use exactly one of:
  {"type": "bedtime_before", "time": "HH:MM", "weeknights_only": true|false}
  {"type": "sleep_at_least", "hours": <number>}
  {"type": "activity", "activity": <one of %s>, "min_days": <int>}
  {"type": "log_field", "field": "bedtime" | "sleep_hours"}
  {"type": "none"}   (only if nothing above fits)
For last_suggestion_check, rely on DATA.last_suggestion_followup.rule_check when it is present.""" % ACTIVITIES


# ---------------------------------------------------------------- helpers
def week_start(d: str) -> str:
    x = date.fromisoformat(d)
    return (x - timedelta(days=x.weekday())).isoformat()


def week_days(ws: str) -> list[str]:
    s = date.fromisoformat(ws)
    return [(s + timedelta(days=i)).isoformat() for i in range(7)]


def bedtime_minutes(hhmm: str | None) -> int | None:
    """Minutes after 18:00, so 23:00 -> 300 and 01:30 -> 450."""
    if not hhmm:
        return None
    try:
        h, m = map(int, hhmm.split(":"))
    except ValueError:
        return None
    t = h * 60 + m
    if t < 12 * 60:
        t += 24 * 60
    return t - 18 * 60


LATE = bedtime_minutes("01:00")


def is_late_night(x: dict) -> bool:
    b = bedtime_minutes(x.get("bedtime"))
    s = x.get("sleep_hours")
    return (b is not None and b >= LATE) or (s is not None and s < 6)


# ---------------------------------------------------------------- agent
class Reflect:
    def __init__(self, memory: Memory, llm, scripted_goal: dict | None = None):
        self.mem = memory
        self.llm = llm
        self.scripted_goal = scripted_goal  # {"text", "check", "rule"}; only used by evaluations

    # 1. daily: extract + remember + follow-up question
    def add_entry(self, d: str, text: str) -> tuple[dict, str | None]:
        self.mem.add_entry(d, text)
        sugg = self.mem.active_suggestion()
        user = (f"ACTIVE SUGGESTION: {sugg['text'] if sugg else 'none'}\n"
                f"DATE: {d}\nENTRY:\n{text}")
        data = self.llm.json(EXTRACT_SYSTEM, user, task=f"extract:{d}")
        data = self._clean(data)
        self.mem.save_extraction(d, data)
        return data, self._follow_up(d, data, sugg)

    def _clean(self, x: dict) -> dict:
        x["mood_score"] = max(-2, min(2, int(x.get("mood_score", 0) or 0)))
        x["emotions"] = [e for e in x.get("emotions", []) if e in EMOTIONS][:3] or ["neutral"]
        x["activities"] = [a for a in x.get("activities", []) if a in ACTIVITIES]
        x.setdefault("people", [])
        x["stressors"] = [s.strip().lower() for s in x.get("stressors", []) if isinstance(s, str) and s.strip()][:3]
        x.setdefault("highlights", [])
        x.setdefault("suggestion_followup", {"mentioned": False, "followed": None, "evidence": ""})
        x["risk_flag"] = bool(x.get("risk_flag", False))
        return x

    def _follow_up(self, d: str, data: dict, sugg: dict | None) -> str | None:
        missing = [k for k in ("sleep_hours", "bedtime") if data.get(k) is None]
        # only nudge about the goal if it hasn't come up today or in the previous entry
        prev = (date.fromisoformat(d) - timedelta(days=1)).isoformat()
        prev_x = self.mem.extractions(prev, prev).get(prev, {})
        goal_unmentioned = bool(sugg) and not data["suggestion_followup"].get("mentioned") \
            and not prev_x.get("suggestion_followup", {}).get("mentioned")
        if not missing and not goal_unmentioned:
            return None
        user = json.dumps({"today": data, "missing": missing,
                           "active_goal": sugg["text"] if sugg else None})
        return self.llm.json(QUESTION_SYSTEM, user, task="question").get("question")

    # 2. weekly: compute stats in Python, let the LLM write the review
    def weekly_review(self, ws: str) -> tuple[dict, dict]:
        days = week_days(ws)
        week = self.mem.extractions(days[0], days[-1])
        history = self.mem.extractions(None, None)
        history = {d: x for d, x in history.items() if d <= days[-1]}
        sugg = self.mem.active_suggestion()
        quality = data_quality(history, days)
        patterns = find_patterns(history) if quality["enough_for_patterns"] else []
        stats = {
            "week_start": ws,
            "this_week": self._week_stats(week),
            "data_quality": quality,
            "previous_weeks": [{"week_start": w, **s["this_week"]} for w, s, _ in self.mem.reviews() if w < ws],
            "computed_patterns": patterns,
            "observations": recurring_stressors(history),
            "last_suggestion_followup": followup_summary(sugg, week),
            "days": {d: {k: x[k] for k in ("mood_score", "emotions", "sleep_hours", "bedtime",
                                           "activities", "people", "stressors", "risk_flag")}
                     for d, x in week.items()},
        }
        review = self.llm.json(REVIEW_SYSTEM, "DATA:\n" + json.dumps(stats), task="review")
        review = self._check_and_rewrite(review, stats)
        self.mem.save_review(ws, stats, review)
        s = review.get("suggestion") or {}
        if self.scripted_goal:              # evaluation mode: keep a fixed goal so follow-up can be scored
            g = self.scripted_goal
            self.mem.set_suggestion(ws, g["text"], g["check"], validate_rule(g["rule"]))
        elif s.get("text"):
            self.mem.set_suggestion(ws, s["text"], s.get("check", ""), validate_rule(s.get("rule")))
        return stats, review

    def _check_and_rewrite(self, review: dict, stats: dict) -> dict:
        """Check the draft against the rules in checks.py. If it breaks any, send it back with the list of
        problems (up to MAX_REWRITES times). Anything still wrong is fixed by checks.scrub()."""
        problems = first = find_problems(review, stats)
        rewrites = 0
        while problems and rewrites < MAX_REWRITES:
            rewrites += 1
            user = ("DATA:\n" + json.dumps(stats) + "\n\nYOUR PREVIOUS DRAFT:\n" + json.dumps(review) +
                    "\n\nThe draft broke these rules:\n- " + "\n- ".join(problems) +
                    "\nRewrite the whole JSON so every problem is fixed. Keep everything that was fine.")
            review = self.llm.json(REVIEW_SYSTEM, user, task="review")
            problems = find_problems(review, stats)
        removed = []
        if problems:
            review, removed = scrub(review, stats)
            problems = find_problems(review, stats)
        review["checks"] = {"first_draft_problems": first, "rewrites": rewrites,
                            "removed_sentences": removed, "final_problems": problems}
        return review

    @staticmethod
    def _week_stats(week: dict) -> dict:
        if not week:
            return {"entries": 0}
        moods = [x["mood_score"] for x in week.values()]
        sleeps = [x["sleep_hours"] for x in week.values() if x.get("sleep_hours") is not None]
        acts: dict[str, int] = {}
        for x in week.values():
            for a in x["activities"]:
                acts[a] = acts.get(a, 0) + 1
        return {
            "entries": len(week),
            "avg_mood": round(mean(moods), 2),
            "avg_sleep": round(mean(sleeps), 1) if sleeps else None,
            "low_mood_days": sum(m <= -1 for m in moods),
            "low_mood_dates": [d for d, x in week.items() if x["mood_score"] <= -1],
            "late_nights": sum(is_late_night(x) for x in week.values()),
            "activity_counts": dict(sorted(acts.items(), key=lambda kv: -kv[1])),
        }


# ---------------------------------------------------------------- evidence rules
MIN_ENTRIES = 10        # need at least this many entries in total before claiming any pattern
MIN_GROUP = 3           # each side of a comparison needs at least this many days
P_MAX = 0.05            # permutation-test threshold: how often chance alone gives a gap this big
N_PERM = 2000


def data_quality(history: dict[str, dict], week: list[str]) -> dict:
    dates = sorted(history)
    span = (date.fromisoformat(dates[-1]) - date.fromisoformat(dates[0])).days + 1 if dates else 0
    return {
        "total_entries": len(dates),
        "days_covered": span,
        "coverage": round(len(dates) / span, 2) if span else 0.0,
        "entries_this_week": sum(d in history for d in week),
        "missing_days_this_week": [d for d in week if d not in history],
        "enough_for_patterns": len(dates) >= MIN_ENTRIES,
        "rule": f"patterns need >= {MIN_ENTRIES} entries in total, >= {MIN_GROUP} days on each side of a "
                f"comparison, and a permutation test p < {P_MAX} divided by the number of comparisons",
    }


def _perm_p(values: list[float], in_group: list[bool], observed: float, stat) -> float:
    """Share of random relabelings (same group sizes) whose statistic is >= the observed one."""
    rng = random.Random(0)          # deterministic, so tests are repeatable
    labels = list(in_group)
    hits = 0
    for _ in range(N_PERM):
        rng.shuffle(labels)
        if stat(values, labels) >= observed - 1e-12:
            hits += 1
    return (hits + 1) / (N_PERM + 1)


def _mean_gap(values, labels):
    a = [v for v, l in zip(values, labels) if l]
    b = [v for v, l in zip(values, labels) if not l]
    return abs(mean(a) - mean(b))


# ---------------------------------------------------------------- pattern finding
def find_patterns(h: dict[str, dict], min_n: int = MIN_GROUP) -> list[dict]:
    """Explainable statistics over all history. A candidate is kept only if it has enough days on
    both sides AND a permutation test says chance alone rarely produces a gap that big."""
    out = []          # candidates with a p-value
    n_tests = 0       # every comparison we were allowed to run counts (multiple-testing correction)
    dates = sorted(h)
    if len(dates) < MIN_ENTRIES:
        return out
    moods = [h[d]["mood_score"] for d in dates]

    # (a) low mood linked to a late night (bed after 01:00 or < 6h sleep)
    late = [is_late_night(h[d]) for d in dates]
    low = [m <= -1 for m in moods]
    n_low, n_late = sum(low), sum(late)
    if n_low >= 2 and n_late >= 2 and len(dates) - n_low >= min_n:
        n_tests += 1
        def late_gap(_, labels):  # labels = "is low" relabeled; compare late-night rates
            lo = [l for l, x in zip(late, labels) if x]
            ot = [l for l, x in zip(late, labels) if not x]
            return sum(lo) / len(lo) - sum(ot) / len(ot)
        obs = late_gap(None, low)
        if obs >= 0.3:
            p = _perm_p(moods, low, obs, late_gap)
            if True:
                ln_low = [d for d, l, x in zip(dates, late, low) if l and x]
                causes: dict[str, int] = {}
                for d in ln_low:
                    prev = (date.fromisoformat(d) - timedelta(days=1)).isoformat()
                    for a in h.get(prev, {}).get("activities", []):
                        causes[a] = causes.get(a, 0) + 1
                base = {a: sum(a in h[d]["activities"] for d in dates) / len(dates) for a in causes}
                causes = {a: c for a, c in causes.items() if c >= 2}
                top = max(causes, key=lambda a: causes[a] * (causes[a] / len(ln_low)) / max(base[a], 1e-9)) \
                    if causes else None
                out.append({
                    "key": "sleep_mood",
                    "finding": f"{len(ln_low)} of {n_low} low-mood days came after a late night "
                               f"(bed after 01:00 or <6h sleep), vs {sum(l for l, x in zip(late, low) if not x) / (len(dates) - n_low):.0%} of other days"
                               + (f"; the day before was usually '{top}' ({causes[top]} times)" if top else ""),
                    "dates": ln_low, "p_value": round(p, 3), "strength": round(obs, 2),
                })

    # (b) activities linked to better / worse mood
    for a in ACTIVITIES:
        grp = [a in h[d]["activities"] for d in dates]
        if min_n <= sum(grp) <= len(dates) - min_n:
            n_tests += 1
            obs = _mean_gap(moods, grp)
            if obs >= 0.7:
                p = _perm_p(moods, grp, obs, _mean_gap)
                if True:
                    w = [m for m, g in zip(moods, grp) if g]
                    wo = [m for m, g in zip(moods, grp) if not g]
                    out.append({"key": f"activity:{a}",
                                "finding": f"Mood averages {mean(w):+.1f} on days with '{a}' vs {mean(wo):+.1f} "
                                           f"without ({len(w)} vs {len(wo)} days)",
                                "dates": [d for d, g in zip(dates, grp) if g],
                                "p_value": round(p, 3), "strength": round(obs / 2, 2)})

    # (c) time with people
    grp = [bool(h[d]["people"]) for d in dates]
    if min_n <= sum(grp) <= len(dates) - min_n:
        n_tests += 1
        obs = _mean_gap(moods, grp)
        if obs >= 0.7:
            p = _perm_p(moods, grp, obs, _mean_gap)
            if True:
                w = [m for m, g in zip(moods, grp) if g]
                wo = [m for m, g in zip(moods, grp) if not g]
                out.append({"key": "people",
                            "finding": f"Mood averages {mean(w):+.1f} on days you saw or talked to someone vs "
                                       f"{mean(wo):+.1f} on days you didn't",
                            "dates": [d for d, g in zip(dates, grp) if g],
                            "p_value": round(p, 3), "strength": round(obs / 2, 2)})

    # keep only candidates that survive a Bonferroni correction over all comparisons we ran
    alpha = P_MAX / max(1, n_tests)
    out = [c for c in out if c["p_value"] < alpha]
    for c in out:
        c["tests_run"] = n_tests

    return sorted(out, key=lambda p: -p["strength"])


def recurring_stressors(h: dict[str, dict], min_n: int = MIN_GROUP) -> list[dict]:
    """Descriptive counts ("'midterm' came up 4 times"). These are observations, not patterns:
    they say nothing about a relationship, so they never make the evidence level 'enough'."""
    st: dict[str, list[str]] = {}
    for d in sorted(h):
        for s in h[d]["stressors"]:
            st.setdefault(s.lower(), []).append(d)
    return [{"key": f"stressor:{s}", "finding": f"'{s}' came up {len(ds)} times", "dates": ds}
            for s, ds in sorted(st.items(), key=lambda kv: -len(kv[1])) if len(ds) >= min_n]


def validate_rule(rule) -> dict:
    """Keep only rules the app can check from extracted data; anything else becomes {"type": "none"}."""
    if not isinstance(rule, dict):
        return {"type": "none"}
    t = rule.get("type")
    try:
        if t == "bedtime_before" and bedtime_minutes(rule.get("time")) is not None:
            return {"type": t, "time": rule["time"], "weeknights_only": bool(rule.get("weeknights_only", False))}
        if t == "sleep_at_least" and 3 <= float(rule.get("hours")) <= 12:
            return {"type": t, "hours": float(rule["hours"])}
        if t == "activity" and rule.get("activity") in ACTIVITIES:
            return {"type": t, "activity": rule["activity"], "min_days": max(1, min(7, int(rule.get("min_days", 1))))}
        if t == "log_field" and rule.get("field") in ("bedtime", "sleep_hours"):
            return {"type": t, "field": rule["field"]}
    except (TypeError, ValueError):
        pass
    return {"type": "none"}


def check_rule_day(rule: dict, d: str, x: dict) -> bool | None:
    """Did this day's entry meet the rule? None = rule doesn't apply or the data is missing."""
    t = rule.get("type")
    if t == "bedtime_before":
        # an entry reports LAST night's bedtime, so Mon-Fri entries are the Sun-Thu "weeknights"
        if rule.get("weeknights_only") and date.fromisoformat(d).weekday() > 4:
            return None
        b = bedtime_minutes(x.get("bedtime"))
        return None if b is None else b < bedtime_minutes(rule["time"])
    if t == "sleep_at_least":
        s = x.get("sleep_hours")
        return None if s is None else s >= rule["hours"]
    if t == "activity":
        return rule["activity"] in x.get("activities", [])
    if t == "log_field":
        return x.get(rule["field"]) is not None
    return None


def followup_summary(sugg: dict | None, week: dict) -> dict | None:
    """How last week's suggestion went. The rule check is computed from data; the self-report is what
    the extractor read in the entries ("I stopped at 12:30 like I planned")."""
    if not sugg:
        return None
    f = [x["suggestion_followup"] for x in week.values()]
    yes = sum(1 for x in f if x.get("mentioned") and x.get("followed") is True)
    no = sum(1 for x in f if x.get("mentioned") and x.get("followed") is False)
    rule = sugg.get("rule") or {"type": "none"}
    res = {"suggestion": sugg["text"], "check": sugg["check"], "rule": rule,
           "self_report": f"said they followed it on {yes} day(s), missed on {no}, "
                          f"didn't mention it on {len(f) - yes - no}"}
    if rule["type"] != "none":
        vals = [check_rule_day(rule, d, x) for d, x in sorted(week.items())]
        met, n = sum(v is True for v in vals), sum(v is not None for v in vals)
        if rule["type"] == "activity":
            ok = met >= rule["min_days"]
            res["rule_check"] = (f"'{rule['activity']}' on {met} day(s) this week (goal {rule['min_days']}): "
                                 f"{'met' if ok else 'not met'}")
        else:
            res["rule_check"] = f"met on {met} of {n} applicable day(s)" if n else "no data to check"
        res["rule_met_days"], res["rule_applicable_days"] = met, n
    res["summary"] = res.get("rule_check") or res["self_report"]
    return res
