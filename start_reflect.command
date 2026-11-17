#!/bin/bash
# Double-click to open Reflect with YOUR journal in the browser. Close this window to stop it.
cd "$(dirname "$0")"
python3 -m streamlit run app.py
