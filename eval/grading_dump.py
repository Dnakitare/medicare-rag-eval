"""Dump every gold item through the real structured pipeline for HAND GRADING.

Captures what the system actually said, the cited passage text, and what the
automated substring metric concluded — so a human can score correctness
independently of the metric that has already been shown to be gameable.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rag.extract import grounded_answer

here = os.path.dirname(__file__)
ins = [json.loads(l) for l in open(os.path.join(here, "gold.jsonl")) if l.strip()]
oos = [json.loads(l) for l in open(os.path.join(here, "gold_oos.jsonl")) if l.strip()]

out = []
for kind, rows in (("in_scope", ins), ("out_of_scope", oos)):
    for i, g in enumerate(rows, 1):
        q = g["query"]
        a = grounded_answer(q)
        txt = (a.text or "")
        exp = g.get("expect_answer", "")
        cited_txt = []
        for n in (a.cited or []):
            if 1 <= n <= len(a.passages):
                p = a.passages[n - 1]
                cited_txt.append({"n": n, "source": p.get("source", "?"),
                                  "text": p.get("text", "")})
        top = max([p["_rerank_score"] for p in a.passages if "_rerank_score" in p] or [0.0])
        rec = {
            "kind": kind, "idx": i, "query": q,
            "expect_answer": exp, "expect_substring": g.get("expect_substring", ""),
            "answer_found": bool(a.answer_found),
            "answer": txt,
            "quote": a.supporting_quote or "",
            "cited": cited_txt,
            "top_rerank": round(top, 4),
            "metric_correct": (exp.lower() in txt.lower()) if exp else None,
            "quote_verbatim": bool(a.supporting_quote) and any(
                a.supporting_quote.lower() in (c["text"] or "").lower() for c in cited_txt),
        }
        out.append(rec)
        print(f"{kind[:3]} {i:2}  found={rec['answer_found']}  metric={rec['metric_correct']}  {q[:50]}", flush=True)

json.dump(out, open(os.path.join(here, "grading_dump.json"), "w"), indent=2)
print(f"\nwrote {len(out)} items -> eval/grading_dump.json")
