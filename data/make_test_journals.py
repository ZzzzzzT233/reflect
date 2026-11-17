"""Generate synthetic test journals with KNOWN answers, for evaluating the weekly review.

Three kinds, several random seeds each:
  clear_pattern  21 days. Low mood happens on (and only on) the days after a late night,
                 and every late night follows a 'deadline' evening. Expected: the review finds
                 'sleep_mood' and cites only those dates.
  missing_days   Same kind of life, but only 8 of 21 days have an entry (2 of them late nights).
                 Expected: the review says there isn't enough evidence and claims no pattern.
  no_pattern     21 days where sleep, mood, activities and people are drawn independently.
                 Expected: no relationship pattern (sleep_mood / activity:* / people) is claimed.

Each entry is written as natural-ish text from a few templates and carries gold labels, so the same
files can also score extraction. Output: data/test_journals/<kind>_s<seed>.json

  python data/make_test_journals.py            # seeds 1-3
  python data/make_test_journals.py --seeds 5
"""
import argparse
import json
import random
from datetime import date, timedelta
from pathlib import Path

START = date(2026, 11, 2)  # a Monday
OUT = Path(__file__).resolve().parent / "test_journals"

FRIENDS = ["Mia", "Jake", "Priya", "Leo", "Sam"]
FAMILY = ["mom", "dad", "my sister"]
ACT_TEXT = {
    "exercise": ["Went to the gym in the morning.", "Went for a run before class.", "Did a short workout."],
    "studying": ["Spent the afternoon studying in the library.", "Did some reading for class.",
                 "Worked through my notes for a few hours."],
    "class": ["Had classes most of the day.", "Two lectures and a section today."],
    "outdoors": ["Took a long walk outside.", "Walked along the river for a while."],
    "rest": ["Took it easy in the evening.", "Mostly rested."],
    "screen_time": ["Spent too long scrolling on my phone.", "Watched a couple of episodes of a show."],
    "chores": ["Did laundry and groceries.", "Cleaned my room."],
}
MOOD_TEXT = {
    -2: ["Honestly a terrible day, I felt awful.", "Really bad day. I felt miserable."],
    -1: ["Felt low and drained most of the day.", "Kind of a down day, everything felt heavy."],
    0: ["An okay, ordinary day.", "Nothing special, just a normal day."],
    1: ["Pretty good day overall.", "Felt good today."],
    2: ["Great day, I felt really happy.", "One of the best days in a while."],
}
EMO = {-2: ["sadness", "disappointment"], -1: ["sadness"], 0: ["neutral"], 1: ["joy"], 2: ["joy", "gratitude"]}


def fmt_time(hhmm: str) -> str:
    h, m = map(int, hhmm.split(":"))
    suffix = "am" if h < 12 else "pm"
    h12 = h % 12 or 12
    return f"{h12}:{m:02d}{suffix}" if m else f"{h12}{suffix}"


def bed_normal(r):
    return r.choice(["22:45", "23:00", "23:15", "23:30", "23:45", "00:00", "00:15", "00:30", "00:45"])


def bed_late(r):
    return r.choice(["01:30", "01:45", "02:00", "02:30", "03:00"])


def sleep_for(bed: str, r) -> float:
    h, m = map(int, bed.split(":"))
    t = h + m / 60 + (24 if h < 12 else 0)        # 23.5, 25.0 ...
    return round(max(3.5, min(9.5, (31.5 - t) + r.choice([-0.5, 0, 0.5]))) * 2) / 2  # wake ~7:30


def write_entry(d, r):
    """Turn a day's labels into a short entry. Order: sleep, activities, people, mood."""
    parts = [r.choice([
        f"Went to bed around {fmt_time(d['bedtime'])}, got about {d['sleep_hours']:g} hours of sleep.",
        f"Slept {d['sleep_hours']:g} hours, in bed at {fmt_time(d['bedtime'])}.",
        f"In bed by {fmt_time(d['bedtime'])}, maybe {d['sleep_hours']:g} hours of sleep.",
    ])]
    for a in d["activities"]:
        if a in ACT_TEXT:
            parts.append(r.choice(ACT_TEXT[a]))
    for p in d["people"]:
        if p in FAMILY:
            parts.append(f"Called {p} for a while.")
        else:
            parts.append(f"Had dinner with {p}.")
    parts.append(r.choice(MOOD_TEXT[d["mood_score"]]))
    if "deadline_work" in d["activities"]:
        parts.append("Problem set due tomorrow morning, so I'm staying up late to finish it.")
    return " ".join(parts)


def gold(day):
    return {"mood_score": day["mood_score"], "emotions": EMO[day["mood_score"]],
            "sleep_hours": day["sleep_hours"], "bedtime": day["bedtime"],
            "activities": day["activities"], "people": day["people"],
            "stressors": [], "highlights": [],
            "suggestion_followup": {"mentioned": False, "followed": None, "evidence": ""},
            "risk_flag": False}


def life_with_pattern(r, n=21):
    """Late nights only after deadline evenings; low mood only on the day after (i.e. the late-night entry)."""
    weekdays = [i for i in range(n) if (START + timedelta(days=i)).weekday() < 5 and i > 0]
    late_idx = sorted(r.sample(weekdays, 6))
    days = []
    for i in range(n):
        dt = START + timedelta(days=i)
        late = i in late_idx
        bed = bed_late(r) if late else bed_normal(r)
        acts = []
        if dt.weekday() < 5:
            acts.append("class")
        acts += r.sample(["studying", "exercise", "outdoors", "rest", "screen_time", "chores"], r.choice([1, 1, 2]))
        if (i + 1) in late_idx:
            acts.append("deadline_work")
        people = r.sample(FRIENDS + FAMILY, 1) if r.random() < 0.4 else []
        mood = r.choice([-2, -1, -1]) if late else r.choice([0, 0, 1, 1, 1, 2])
        days.append({"date": dt.isoformat(), "bedtime": bed, "sleep_hours": sleep_for(bed, r),
                     "activities": acts, "people": people, "mood_score": mood})
    return days, [(START + timedelta(days=i)).isoformat() for i in late_idx]


def life_without_pattern(r, n=21):
    days = []
    for i in range(n):
        dt = START + timedelta(days=i)
        bed = bed_late(r) if r.random() < 0.3 else bed_normal(r)
        acts = r.sample(["class", "studying", "exercise", "outdoors", "rest", "screen_time", "chores"],
                        r.choice([1, 2, 2, 3]))
        people = r.sample(FRIENDS + FAMILY, 1) if r.random() < 0.4 else []
        days.append({"date": dt.isoformat(), "bedtime": bed, "sleep_hours": sleep_for(bed, r),
                     "activities": acts, "people": people, "mood_score": r.choice([-2, -1, 0, 0, 1, 1, 2])})
    return days


def build(kind, seed):
    r = random.Random(f"{kind}-{seed}")
    if kind == "clear_pattern":
        days, late = life_with_pattern(r)
        expected = {"must_find": ["sleep_mood"], "allowed_dates": {"sleep_mood": late},
                    "final_evidence": "enough", "no_relationship_patterns": False}
    elif kind == "missing_days":
        days, late = life_with_pattern(r)
        others = [d["date"] for d in days if d["date"] not in late]
        keep_dates = set(r.sample(late, 2) + r.sample(others, 6))   # 8 of 21 days, 2 of them late nights
        days = [d for d in days if d["date"] in keep_dates]
        expected = {"must_find": [], "allowed_dates": {}, "final_evidence": "not_enough",
                    "no_relationship_patterns": True}
    elif kind == "no_pattern":
        days = life_without_pattern(r)
        expected = {"must_find": [], "allowed_dates": {}, "final_evidence": "not_enough",
                    "no_relationship_patterns": True}
    else:
        raise ValueError(kind)
    entries = [{"date": d["date"], "text": write_entry(d, r), "gold": gold(d)} for d in days]
    return {"kind": kind, "seed": seed, "expected": expected, "entries": entries}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=3)
    a = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    for kind in ("clear_pattern", "missing_days", "no_pattern"):
        for s in range(1, a.seeds + 1):
            j = build(kind, s)
            (OUT / f"{kind}_s{s}.json").write_text(json.dumps(j, indent=1))
            print(f"{kind}_s{s}: {len(j['entries'])} entries")


if __name__ == "__main__":
    main()
