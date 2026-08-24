"""Retrieval eval: recall@k against a gold set. THE keystone in miniature.

Gold file (eval/gold.jsonl), one JSON object per line:
    {"query": "...", "expect_source": "file.pdf", "expect_substring": "..."}

A retrieved chunk counts as a hit when it comes from `expect_source` AND its
text contains `expect_substring` (case-insensitive). recall@k = fraction of
gold queries with at least one hit in the top-k.

This is the number every wk2-6 change must move. Add real gold lines as you
read the corpus; ship `eval/gold.example.jsonl` is just the seed.
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", message=r'Field "model_')

import lancedb

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ingest.embed import embed_query, l2_normalize  # noqa: E402

DB_PATH = ROOT / "data" / "lancedb"
KS = (1, 3, 5, 10)


def load_gold() -> list[dict]:
    for name in ("gold.jsonl", "gold.example.jsonl"):
        p = ROOT / "eval" / name
        if p.exists():
            return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]
    sys.exit("No eval/gold.jsonl or gold.example.jsonl found.")


def hit(rows: list[dict], g: dict) -> bool:
    sub = g["expect_substring"].lower()
    return any(
        r["source"] == g["expect_source"] and sub in r["text"].lower() for r in rows
    )


def main() -> None:
    gold = load_gold()
    tbl = lancedb.connect(str(DB_PATH)).open_table("chunks")
    maxk = max(KS)

    recall = {k: 0 for k in KS}
    for g in gold:
        rows = tbl.search(l2_normalize(embed_query(g["query"]))).metric("cosine").limit(maxk).to_list()
        for k in KS:
            if hit(rows[:k], g):
                recall[k] += 1

    n = len(gold)
    print(f"Retrieval eval over {n} gold queries:")
    for k in KS:
        print(f"  recall@{k:<2} = {recall[k] / n:.2f}  ({recall[k]}/{n})")


if __name__ == "__main__":
    main()
