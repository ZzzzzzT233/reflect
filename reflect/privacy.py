"""Privacy controls: a local log of everything sent to the model API, and deleting data.

What leaves the computer (only to the model API, nowhere else):
  extract:<date>     the raw text of that day's entry, its date, and the active goal's text
  question:<date>    that day's EXTRACTED fields (mood, sleep, activities...), not the raw text
  review:<week>      the week's extracted fields + computed statistics, not the raw text
Everything is stored locally: entries and reviews in a SQLite file, and the API log in a JSON-lines
file next to it. Deleting a day removes its entry, its extraction, every saved review that used it, and
the log lines that carried that day's text or data.
"""
from __future__ import annotations

import json
import time
from datetime import date, timedelta
from pathlib import Path


class LoggedBackend:
    """Wraps any backend and appends one JSON line per call: when, which task, what was sent."""

    def __init__(self, inner, log_path: str | Path):
        self.inner = inner
        self.log_path = Path(log_path)

    def __getattr__(self, name):          # name, model, calls, tokens come from the real backend
        return getattr(self.inner, name)

    def json(self, system: str, user: str, task: str = "") -> dict:
        out = self.inner.json(system, user, task)
        rec = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "backend": self.inner.name,
               "model": self.inner.model, "task": task,
               "chars_sent": len(system) + len(user), "sent": user}
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return out


def read_log(log_path: str | Path) -> list[dict]:
    p = Path(log_path)
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def _week_start(d: str) -> str:
    x = date.fromisoformat(d)
    return (x - timedelta(days=x.weekday())).isoformat()


def _touches_day(rec: dict, d: str) -> bool:
    """Did this API call carry data from day d? Extract/question calls name the day; a review call
    carries the whole week (and later reviews may include it in history statistics)."""
    t = rec.get("task", "")
    if t in (f"extract:{d}", f"question:{d}"):
        return True
    if t.startswith("review:"):
        return d in rec.get("sent", "")
    return False


def forget_day(mem, log_path: str | Path, d: str) -> dict:
    """Delete one day: entry, extraction, every saved review that used it, and matching API-log lines."""
    c = mem.conn
    n_entry = c.execute("DELETE FROM entries WHERE date=?", (d,)).rowcount
    c.execute("DELETE FROM extractions WHERE date=?", (d,))
    # that week's review, plus any later review whose statistics or text mention this day
    n_rev = c.execute("DELETE FROM reviews WHERE week_start=? OR stats LIKE ? OR review LIKE ?",
                      (_week_start(d), f"%{d}%", f"%{d}%")).rowcount
    c.commit()
    recs = read_log(log_path)
    keep = [r for r in recs if not _touches_day(r, d)]
    if recs:
        Path(log_path).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in keep), encoding="utf-8")
    return {"entries": n_entry, "reviews": n_rev, "log_lines": len(recs) - len(keep)}


def wipe(mem, log_path: str | Path) -> dict:
    """Delete everything: all entries, extractions, reviews, goals, and the API log."""
    c = mem.conn
    counts = {t: c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ("entries", "extractions", "reviews", "suggestions")}
    for t in counts:
        c.execute(f"DELETE FROM {t}")
    c.commit()
    c.execute("VACUUM")                    # also clear deleted rows from the file itself
    p = Path(log_path)
    counts["log_lines"] = len(read_log(p))
    if p.exists():
        p.unlink()
    return counts
