"""Closed-book control: answer the gold questions with NO retrieval.

Isolates how much of the RAG system's `correct` score is retrieval doing work
vs. the base model already knowing CMS boilerplate. Scored with the SAME rule
as answer_eval.py (expect_answer substring), so the numbers are comparable.
"""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rag.llm import chat

MODEL = os.environ.get("GEN_MODEL", "qwen2.5:7b")
rows = [json.loads(l) for l in open(os.path.join(os.path.dirname(__file__), "gold.jsonl")) if l.strip()]

hits, out = 0, []
for i, g in enumerate(rows, 1):
    ans = chat([
        {"role": "system", "content": "Answer the question directly and concisely."},
        {"role": "user", "content": g["query"]},
    ], model=MODEL)
    ok = g["expect_answer"].lower() in ans.lower()
    hits += ok
    out.append({"query": g["query"], "expect_answer": g["expect_answer"], "correct": ok, "answer": ans})
    print(f"{i:2}. {'C' if ok else '.'}  {g['expect_answer']!r}", flush=True)

print(f"\nclosed-book ({MODEL}, no retrieval): {hits}/{len(rows)} = {hits/len(rows):.2f}")
with open(os.path.join(os.path.dirname(__file__), f"closed_book_{MODEL.replace(':','-')}.json"), "w") as f:
    json.dump(out, f, indent=2)
