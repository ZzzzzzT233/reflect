"""Evaluate Reflect's emotion labelling on GoEmotions (Demszky et al., 2020).

  python eval/goemotions_eval.py --n 200                    # real model (needs OPENAI_API_KEY)
  python eval/goemotions_eval.py --n 200 --backend mock     # majority-class baseline ("neutral")

Downloads the official test split (5,427 Reddit comments, 27 emotions + neutral,
multi-label) from the google-research GitHub repo on first run.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from reflect.agent import EMOTIONS  # noqa: E402
from reflect.cli import load_dotenv  # noqa: E402
from reflect.llm import get_backend  # noqa: E402

BASE = "https://raw.githubusercontent.com/google-research/google-research/master/goemotions/data/"
CACHE = ROOT / "eval" / "goemotions"

SENTIMENT = {  # grouping from the GoEmotions paper
    "positive": ["admiration", "amusement", "approval", "caring", "desire", "excitement", "gratitude",
                 "joy", "love", "optimism", "pride", "relief"],
    "negative": ["anger", "annoyance", "disappointment", "disapproval", "disgust", "embarrassment",
                 "fear", "grief", "nervousness", "remorse", "sadness"],
    "ambiguous": ["confusion", "curiosity", "realization", "surprise"],
    "neutral": ["neutral"],
}
TO_SENT = {e: s for s, es in SENTIMENT.items() for e in es}

SYSTEM = f"""Label the emotions expressed in each short text. For each text choose 1-3 labels,
most important first, only from: {EMOTIONS}. Use "neutral" only if no emotion is expressed.
Return JSON: {{"results": [{{"id": <id>, "emotions": [...]}}, ...]}} with one item per input text."""


def load_test():
    CACHE.mkdir(parents=True, exist_ok=True)
    for f in ("test.tsv", "emotions.txt"):
        if not (CACHE / f).exists():
            urllib.request.urlretrieve(BASE + f, CACHE / f)
    labels = (CACHE / "emotions.txt").read_text().split()
    assert labels == EMOTIONS, "label order mismatch"
    rows = []
    for line in (CACHE / "test.tsv").read_text(encoding="utf-8").splitlines():
        text, ids, _ = line.split("\t")
        rows.append((text, [labels[int(i)] for i in ids.split(",")]))
    return rows


def predict(llm, batch):
    if llm.name == "mock":
        return [["neutral"] for _ in batch]
    user = json.dumps([{"id": i, "text": t} for i, (t, _) in enumerate(batch)])
    res = llm.json(SYSTEM, user, task="emotion").get("results", [])
    by_id = {r.get("id"): [e for e in r.get("emotions", []) if e in EMOTIONS] for r in res}
    return [by_id.get(i) or ["neutral"] for i in range(len(batch))]


def main():
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--batch", type=int, default=20)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--backend", default="openai", choices=["openai", "mock"])
    a = ap.parse_args()

    rows = load_test()
    random.Random(a.seed).shuffle(rows)
    sample = rows[: a.n]
    llm = get_backend(a.backend)
    preds = []
    for i in range(0, len(sample), a.batch):
        preds += predict(llm, sample[i:i + a.batch])
        print(f"{min(i + a.batch, len(sample))}/{len(sample)}", end="\r")

    any_hit = top1 = sent = 0
    tp = fp = fn = 0
    for (text, gold), pred in zip(sample, preds):
        g, p = set(gold), set(pred)
        any_hit += bool(g & p)
        top1 += pred[0] in g
        sent += TO_SENT[pred[0]] in {TO_SENT[x] for x in gold}
        tp += len(g & p); fp += len(p - g); fn += len(g - p)
    n = len(sample)
    prec = tp / (tp + fp) if tp + fp else 0
    rec = tp / (tp + fn) if tp + fn else 0
    res = {
        "backend": llm.name, "model": llm.model, "n": n, "seed": a.seed,
        "any_label_match": round(any_hit / n, 3),
        "top1_in_gold": round(top1 / n, 3),
        "sentiment_group_acc": round(sent / n, 3),
        "micro_precision": round(prec, 3), "micro_recall": round(rec, 3),
        "micro_f1": round(2 * prec * rec / (prec + rec), 3) if prec + rec else 0,
        "llm_calls": llm.calls, "tokens": llm.tokens,
    }
    out = ROOT / "out"; out.mkdir(exist_ok=True)
    (out / f"goemotions_{llm.name}.json").write_text(json.dumps(res, indent=1))
    examples = [{"text": t, "gold": g, "pred": p} for (t, g), p in zip(sample[:15], preds[:15])]
    (out / f"goemotions_{llm.name}_examples.json").write_text(json.dumps(examples, indent=1, ensure_ascii=False))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
