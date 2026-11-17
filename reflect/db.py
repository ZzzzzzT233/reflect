"""Long-term memory: a single SQLite file."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
    date TEXT PRIMARY KEY,          -- YYYY-MM-DD, one entry per day
    text TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS extractions (
    date TEXT PRIMARY KEY REFERENCES entries(date),
    data TEXT NOT NULL              -- JSON produced by the extractor
);
CREATE TABLE IF NOT EXISTS reviews (
    week_start TEXT PRIMARY KEY,    -- Monday, YYYY-MM-DD
    stats TEXT NOT NULL,            -- JSON computed in Python
    review TEXT NOT NULL            -- JSON written by the LLM
);
CREATE TABLE IF NOT EXISTS suggestions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    week_start TEXT NOT NULL,       -- week it was given in
    text TEXT NOT NULL,
    check_rule TEXT,                -- how we will know it was followed
    active INTEGER NOT NULL DEFAULT 1
);
"""


class Memory:
    def __init__(self, path: str | Path):
        self.conn = sqlite3.connect(str(path), check_same_thread=False)  # Streamlit reruns on other threads
        self.conn.executescript(SCHEMA)

    # entries -------------------------------------------------------------
    def add_entry(self, date: str, text: str):
        self.conn.execute("INSERT OR REPLACE INTO entries VALUES (?,?)", (date, text))
        self.conn.commit()

    def entry(self, date: str) -> str | None:
        r = self.conn.execute("SELECT text FROM entries WHERE date=?", (date,)).fetchone()
        return r[0] if r else None

    # extractions ---------------------------------------------------------
    def save_extraction(self, date: str, data: dict):
        self.conn.execute("INSERT OR REPLACE INTO extractions VALUES (?,?)", (date, json.dumps(data)))
        self.conn.commit()

    def extractions(self, start: str | None = None, end: str | None = None) -> dict[str, dict]:
        q, args = "SELECT date, data FROM extractions", []
        if start and end:
            q += " WHERE date BETWEEN ? AND ?"
            args = [start, end]
        q += " ORDER BY date"
        return {d: json.loads(x) for d, x in self.conn.execute(q, args)}

    # reviews & suggestions -----------------------------------------------
    def save_review(self, week_start: str, stats: dict, review: dict):
        self.conn.execute("INSERT OR REPLACE INTO reviews VALUES (?,?,?)",
                          (week_start, json.dumps(stats), json.dumps(review)))
        self.conn.commit()

    def reviews(self) -> list[tuple[str, dict, dict]]:
        return [(w, json.loads(s), json.loads(r)) for w, s, r in
                self.conn.execute("SELECT * FROM reviews ORDER BY week_start")]

    def active_suggestion(self) -> dict | None:
        r = self.conn.execute(
            "SELECT id, week_start, text, check_rule FROM suggestions WHERE active=1 ORDER BY id DESC LIMIT 1").fetchone()
        return dict(zip(["id", "week_start", "text", "check"], r)) if r else None

    def set_suggestion(self, week_start: str, text: str, check: str):
        self.conn.execute("UPDATE suggestions SET active=0")
        self.conn.execute("INSERT INTO suggestions (week_start, text, check_rule) VALUES (?,?,?)",
                          (week_start, text, check))
        self.conn.commit()
