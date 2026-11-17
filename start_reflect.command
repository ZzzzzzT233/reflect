#!/bin/zsh
# Double-click to open Reflect with YOUR journal in the browser. Close this window to stop it.
cd "$(dirname "$0")"
source ~/.zshrc 2>/dev/null   # load conda so python3 has streamlit installed
python3 -m streamlit run app.py
