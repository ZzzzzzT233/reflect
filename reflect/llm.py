"""LLM backends.

`OpenAIBackend` is the real one. `MockBackend` exists only so the pipeline can be
tested end-to-end without an API key: it returns the hand-written gold labels that
ship with the demo journal (for extraction) and a template (for reviews). It is
NOT the product and its output should never be presented as model output.
"""
from __future__ import annotations

import json
import os
import time


class LLMError(RuntimeError):
    pass


class OpenAIBackend:
    name = "openai"

    def __init__(self, model: str | None = None):
        try:
            from openai import OpenAI
        except ImportError as e:  # pragma: no cover
            raise LLMError("pip install openai") from e
        if not os.environ.get("OPENAI_API_KEY"):
            raise LLMError("OPENAI_API_KEY is not set (put it in your shell or a .env file).")
        self.client = OpenAI()
        self.model = model or os.environ.get("REFLECT_MODEL", "gpt-4o-mini")
        self.calls = 0
        self.tokens = 0

    def json(self, system: str, user: str, task: str = "") -> dict:
        """One chat call that must return a JSON object. Retries once on bad JSON."""
        last_err = None
        for attempt in range(3):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    temperature=0.2,
                    response_format={"type": "json_object"},
                    messages=[{"role": "system", "content": system},
                              {"role": "user", "content": user}],
                )
                self.calls += 1
                if resp.usage:
                    self.tokens += resp.usage.total_tokens
                return json.loads(resp.choices[0].message.content)
            except json.JSONDecodeError as e:
                last_err = e
            except Exception as e:  # network / rate limit / bad model name
                last_err = e
                msg = str(e)
                if "model" in msg and ("not found" in msg or "does not exist" in msg):
                    raise LLMError(f"Model '{self.model}' is not available to your key. "
                                   "Set REFLECT_MODEL to one you can use.") from e
                time.sleep(2 * (attempt + 1))
        raise LLMError(f"LLM call failed after retries: {last_err}")


class MockBackend:
    """Offline stand-in for testing the plumbing. See module docstring."""
    name = "mock"
    model = "mock"

    def __init__(self, gold: dict[str, dict] | None = None):
        self.gold = gold or {}
        self.calls = 0
        self.tokens = 0

    def json(self, system: str, user: str, task: str = "") -> dict:
        self.calls += 1
        if task.startswith("extract:"):
            date = task.split(":", 1)[1]
            g = self.gold.get(date)
            if g is None:
                return {"mood_score": 0, "emotions": ["neutral"], "sleep_hours": None,
                        "bedtime": None, "activities": [], "people": [], "stressors": [],
                        "highlights": [], "suggestion_followup": {"mentioned": False, "followed": None, "evidence": ""}}
            return json.loads(json.dumps(g))
        if task.startswith("review"):
            data = json.loads(user.split("DATA:\n", 1)[1].split("\n\nYOUR PREVIOUS DRAFT", 1)[0])
            pats = data["computed_patterns"]
            enough = bool(pats) and data["data_quality"]["enough_for_patterns"]
            tw = data["this_week"]
            return {
                "summary": f"[mock] {tw.get('entries', 0)} entries this week"
                           + (f", avg mood {tw['avg_mood']}" if tw.get("entries") else "")
                           + ("" if enough else ". Not enough evidence for a pattern yet."),
                "evidence_level": "enough" if enough else "not_enough",
                "patterns": [{"key": p["key"], "finding": p["finding"], "evidence_dates": p.get("dates", [])}
                             for p in pats[:3]] if enough else [],
                "last_suggestion_check": "[mock] " + (data.get("last_suggestion_followup") or {}).get("summary", "no previous suggestion"),
                "suggestion": {"text": "[mock] Stop deadline work by 00:30 on weeknights.",
                               "check": "bedtime before 01:00 on weeknights",
                               "rule": {"type": "bedtime_before", "time": "01:00", "weeknights_only": True}},
            }
        if task.startswith("question"):
            return {"question": "[mock] Did you manage this week's suggestion today?"}
        if task.startswith("emotion"):
            return {"emotions": ["neutral"]}
        return {}


def get_backend(kind: str, gold: dict | None = None):
    if kind == "mock":
        return MockBackend(gold)
    if kind == "openai":
        return OpenAIBackend()
    raise ValueError(kind)
