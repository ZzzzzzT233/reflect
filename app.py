"""Reflect web UI:  streamlit run app.py"""
import json
import os
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from reflect.agent import Reflect, week_start
from reflect.cli import ROOT, load_dotenv, review_md
from reflect.db import Memory
from reflect.llm import LLMError, get_backend

load_dotenv()
st.set_page_config(page_title="Reflect", page_icon="📓", layout="centered")
BACKEND = os.environ.get("REFLECT_BACKEND", "openai")
DB = Path(os.environ.get("REFLECT_DB", ROOT / "reflect.sqlite"))


@st.cache_resource
def get_agent():
    gold = None
    if BACKEND == "mock":
        gold = {e["date"]: e["gold"] for e in json.loads((ROOT / "data/demo_journal.json").read_text())}
    return Reflect(Memory(DB), get_backend(BACKEND, gold))


try:
    agent = get_agent()
except LLMError as e:
    st.error(str(e))
    st.stop()

st.title("📓 Reflect")
st.caption("An AI journal coach that remembers you" + (" · ⚠️ mock backend" if BACKEND == "mock" else ""))

tab_write, tab_trends, tab_review = st.tabs(["Today", "Trends", "Weekly review"])

with tab_write:
    sugg = agent.mem.active_suggestion()
    if sugg:
        st.info(f"**This week’s goal:** {sugg['text']}")
    d = st.date_input("Date", value=date.today()).isoformat()
    text = st.text_area("How was your day? How did you sleep? Who did you see?",
                        value=agent.mem.entry(d) or "", height=160)
    if st.button("Save entry", type="primary", disabled=not text.strip()):
        with st.spinner("Reading your entry…"):
            x, q = agent.add_entry(d, text.strip())
        st.success(f"Mood {x['mood_score']:+d} · {', '.join(x['emotions'])} · "
                   f"sleep {x.get('sleep_hours')}h · bed {x.get('bedtime')}")
        if x.get("risk_flag"):
            st.warning("It sounds like today was really hard. Please consider reaching out to someone "
                       "you trust or a counselor. You don’t have to handle it alone.")
        if q:
            st.markdown(f"🤖 **Reflect asks:** {q}")
    with st.expander("Load the 3-week demo journal"):
        if st.button("Import demo entries (runs the extractor on 21 entries)"):
            for e in json.loads((ROOT / "data/demo_journal.json").read_text()):
                agent.add_entry(e["date"], e["text"])
            st.success("Imported 21 entries.")

with tab_trends:
    ex = agent.mem.extractions()
    if not ex:
        st.write("No entries yet.")
    else:
        df = pd.DataFrame([{"date": d, "mood": x["mood_score"], "sleep_hours": x.get("sleep_hours")}
                           for d, x in ex.items()]).set_index("date")
        st.subheader("Mood (−2 to +2)")
        st.line_chart(df["mood"])
        st.subheader("Sleep (hours)")
        st.bar_chart(df["sleep_hours"])

with tab_review:
    ex = agent.mem.extractions()
    weeks = sorted({week_start(d) for d in ex}, reverse=True)
    if weeks:
        ws = st.selectbox("Week starting", weeks)
        if st.button("Generate weekly review", type="primary"):
            with st.spinner("Looking for patterns…"):
                stats, review = agent.weekly_review(ws)
            st.markdown(review_md(ws, stats, review))
    for ws, stats, review in reversed(agent.mem.reviews()):
        with st.expander(f"Past review — week of {ws}"):
            st.markdown(review_md(ws, stats, review))
