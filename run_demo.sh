#!/usr/bin/env bash
# One-shot: install, run the 3-week demo and the GoEmotions eval with your OpenAI key.
set -e
cd "$(dirname "$0")"
python3 -m pip install -q -r requirements.txt
python3 -m reflect.cli demo
python3 eval/goemotions_eval.py --n 200
python3 data/make_test_journals.py
python3 eval/review_eval.py
echo; echo "Done. Open out/demo_report_openai.md, out/review_eval_openai.md and out/goemotions_openai.json"
