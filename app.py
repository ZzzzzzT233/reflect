"""Reflect web app.

  streamlit run app.py              your own journal  (reflect.sqlite + api_log.jsonl, never uploaded)
  streamlit run app.py -- --demo    demo mode: synthetic test journal in a separate database
"""
import json
import os
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from reflect.agent import Reflect, week_start
from reflect.cli import ROOT, load_dotenv, review_md
from reflect.db import Memory
from reflect.llm import LLMError, get_backend
from reflect.privacy import LoggedBackend, forget_day, read_log, wipe

load_dotenv()
DEMO = "--demo" in sys.argv or os.environ.get("REFLECT_DEMO") == "1"
BACKEND = os.environ.get("REFLECT_BACKEND", "openai")
if DEMO:
    (ROOT / "out").mkdir(exist_ok=True)
    DB, LOG = ROOT / "out" / "demo_app.sqlite", ROOT / "out" / "demo_api_log.jsonl"
else:
    DB = Path(os.environ.get("REFLECT_DB", ROOT / "reflect.sqlite"))
    LOG = DB.with_name("api_log.jsonl")
DEMO_FILE = ROOT / "data" / "demo_journal.json"

st.set_page_config(page_title="Reflect" + (" (demo)" if DEMO else ""), page_icon="📓", layout="centered")


@st.cache_resource
def get_agent(db: str, log: str, demo: bool):
    gold = None
    if BACKEND == "mock":
        gold = {e["date"]: e["gold"] for e in json.loads(DEMO_FILE.read_text())}
    return Reflect(Memory(db), LoggedBackend(get_backend(BACKEND, gold), log))


try:
    agent = get_agent(str(DB), str(LOG), DEMO)
except LLMError as e:
    st.error(str(e))
    st.stop()

st.title("📓 Reflect")
st.caption("An AI journal coach that remembers you" + (" · ⚠️ mock backend" if BACKEND == "mock" else ""))
if DEMO:
    st.error("**DEMO MODE**: this shows a synthetic test journal (a fictional student). "
             "No real entries are loaded, and your own journal is not touched.")

tab_today, tab_trends, tab_review, tab_privacy = st.tabs(["Today", "Trends", "Weekly review", "Privacy"])

# ------------------------------------------------------------------ Today
with tab_today:
    sugg = agent.mem.active_suggestion()
    if sugg:
        st.info(f"**This week’s goal:** {sugg['text']}")
    d = st.date_input("Date", value=date.today(), max_value=date.today()).isoformat()
    existing = agent.mem.entry(d)
    if existing:
        st.caption("You already wrote this day. Saving replaces it.")
    text = st.text_area("How was your day? When did you go to bed, how did you sleep, who did you see?",
                        value=existing or "", height=180, key=f"text_{d}")
    if st.button("Save entry", type="primary", disabled=not text.strip()):
        with st.spinner("Reading your entry…"):
            x, q = agent.add_entry(d, text.strip())
        st.session_state["last"] = {"date": d, "x": x, "q": q}

    last = st.session_state.get("last")
    if last and last["date"] == d:
        x = last["x"]
        st.success(f"Saved. Mood {x['mood_score']:+d} · {', '.join(x['emotions'])} · "
                   f"sleep {x.get('sleep_hours')}h · bed {x.get('bedtime')} · "
                   f"{', '.join(x['activities']) or 'no activities'}")
        if x.get("risk_flag"):
            st.warning("It sounds like today was really hard. Please consider reaching out to someone "
                       "you trust or a counselor. You don’t have to handle it alone.")
        if last["q"]:
            st.markdown(f"🤖 **Reflect asks:** {last['q']}")
            ans = st.text_input("Your answer (optional)", key=f"ans_{d}")
            if st.button("Add answer", disabled=not ans.strip()):
                with st.spinner("Updating your entry…"):
                    new_text = (agent.mem.entry(d) or "") + f"\n\n(Reflect asked: {last['q']}) {ans.strip()}"
                    x, _ = agent.add_entry(d, new_text)
                st.session_state["last"] = {"date": d, "x": x, "q": None}
                st.rerun()

    ex = agent.mem.extractions()
    if ex:
        st.divider()
        st.subheader("Recent days")
        rows = [{"date": k, "mood": v["mood_score"], "sleep (h)": v.get("sleep_hours"),
                 "bed": v.get("bedtime"), "activities": ", ".join(v["activities"])}
                for k, v in sorted(ex.items(), reverse=True)[:7]]
        st.dataframe(pd.DataFrame(rows), hide_index=True)
        st.caption(f"{len(ex)} entries so far. Pick an earlier date above to fill in a day you missed.")

    if DEMO:
        with st.expander("Load the 3-week demo journal"):
            st.write("Runs the extractor on 21 synthetic entries (about 30 model calls).")
            if st.button("Import demo entries"):
                with st.spinner("Reading 21 entries…"):
                    for e in json.loads(DEMO_FILE.read_text()):
                        agent.add_entry(e["date"], e["text"])
                st.success("Imported 21 entries.")
                st.rerun()

# ------------------------------------------------------------------ Trends
with tab_trends:
    ex = agent.mem.extractions()
    if not ex:
        st.write("No entries yet.")
    else:
        df = pd.DataFrame([{"date": k, "mood": v["mood_score"], "sleep_hours": v.get("sleep_hours")}
                           for k, v in ex.items()]).set_index("date")
        st.subheader("Mood (−2 to +2)")
        st.line_chart(df["mood"])
        st.subheader("Sleep (hours)")
        st.bar_chart(df["sleep_hours"])

# ------------------------------------------------------------------ Weekly review
with tab_review:
    ex = agent.mem.extractions()
    weeks = sorted({week_start(k) for k in ex}, reverse=True)
    if not weeks:
        st.write("Write a few entries first.")
    else:
        ws = st.selectbox("Week starting", weeks)
        if st.button("Generate weekly review", type="primary"):
            with st.spinner("Looking for patterns…"):
                stats, review = agent.weekly_review(ws)
            st.markdown(review_md(ws, stats, review))
    for ws, stats, review in reversed(agent.mem.reviews()):
        with st.expander(f"Past review: week of {ws}"):
            st.markdown(review_md(ws, stats, review))

# ------------------------------------------------------------------ Privacy
with tab_privacy:
    st.subheader("Where your data is")
    st.markdown(
        f"- **Entries, extracted data, reviews, goals**: one file on this computer, `{DB.name}`.\n"
        f"- **Log of everything sent to the model**: `{LOG.name}`, also on this computer.\n"
        "- Both are listed in `.gitignore`, so they are never pushed to GitHub.\n"
        f"- {'This is the **demo** database. Your own journal is in a different file.' if DEMO else 'Demo mode uses a different database, so a demo never shows these entries.'}")
    st.subheader("What is sent to the model API")
    st.markdown(
        "| call | what is sent |\n|---|---|\n"
        "| `extract:<date>` | the text of that day’s entry, its date, and the text of the current goal |\n"
        "| `question:<date>` | that day’s extracted fields (mood, sleep, activities…), **not** the text |\n"
        "| `review:<week>` | the week’s extracted fields and statistics, **not** the text |\n")

    log = read_log(LOG)
    st.subheader(f"API log ({len(log)} calls)")
    if log:
        st.dataframe(pd.DataFrame([{k: r[k] for k in ("time", "task", "model", "chars_sent")} for r in log[::-1]]),
                     hide_index=True)
        with st.expander("Show exactly what was sent (last 10 calls)"):
            for r in log[::-1][:10]:
                st.caption(f"{r['time']} · {r['task']} · {r['chars_sent']} characters")
                st.code(r["sent"][:3000] + ("…" if len(r["sent"]) > 3000 else ""), language=None)
    else:
        st.caption("Nothing has been sent yet.")

    st.subheader("Delete data")
    dates = sorted(agent.mem.extractions(), reverse=True)
    if dates:
        day = st.selectbox("Delete one day", dates)
        sure = st.checkbox(f"Yes, delete {day}: the entry, that week’s review, and its API-log lines")
        if st.button("Delete this day", disabled=not sure):
            res = forget_day(agent.mem, LOG, day)
            st.session_state.pop("last", None)
            st.success(f"Deleted {day}: {res['entries']} entry, {res['reviews']} review, {res['log_lines']} log lines.")
            st.rerun()
    confirm = st.text_input("Delete EVERYTHING in this database and the API log. Type DELETE to confirm.")
    if st.button("Delete everything", disabled=confirm != "DELETE"):
        res = wipe(agent.mem, LOG)
        st.session_state.pop("last", None)
        st.success(f"Deleted {res['entries']} entries, {res['reviews']} reviews and {res['log_lines']} log lines.")
        st.rerun()
