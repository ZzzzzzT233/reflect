#!/bin/bash
# Double-click to open Reflect in DEMO mode (synthetic journal, separate database).
cd "$(dirname "$0")"
python3 -m streamlit run app.py --server.port 8502 -- --demo
