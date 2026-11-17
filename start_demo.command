#!/bin/zsh
# Double-click to open Reflect in DEMO mode (synthetic journal, separate database).
cd "$(dirname "$0")"
source ~/.zshrc 2>/dev/null   # load conda so python3 has streamlit installed
python3 -m streamlit run app.py --server.port 8502 -- --demo
