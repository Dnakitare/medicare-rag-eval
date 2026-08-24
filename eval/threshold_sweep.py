"""Threshold sweep: publish the abstention/over-abstention curve instead of one
tuned constant. Retrieval only — no generation — so it's fast and deterministic.

For each gold question (in-scope + out-of-scope) record the top rerank score,
then sweep RELEVANCE_MIN and report what each threshold would do.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rag.answer import retrieve

here = os.path.dirname(__file__)
ins = [json.loads(l) for l in open(os.path.join(here, "gold.jsonl")) if l.strip()]
oos = [json.loads(l) for l in open(os.path.join(here, "gold_oos.jsonl")) if l.strip()]

def top(q):
    ps = retrieve(q, k=5, use_rerank=True, use_hybrid=True)
    s = [p["_rerank_score"] for p in ps if "_rerank_score" in p]
    return max(s) if s else 0.0

print("scoring in-scope...", flush=True)
in_s = [(g["query"], top(g["query"])) for g in ins]
print("scoring out-of-scope...", flush=True)
oo_s = [(g["query"], top(g["query"])) for g in oos]

print("\nIN-SCOPE top rerank scores (sorted):")
for q, s in sorted(in_s, key=lambda x: x[1]): print(f"  {s:.4f}  {q[:66]}")
print("\nOUT-OF-SCOPE top rerank scores (sorted, desc):")
for q, s in sorted(oo_s, key=lambda x: -x[1]): print(f"  {s:.4f}  {q[:66]}")

print(f"\n{'threshold':>10} {'OOS abstained':>16} {'in-scope lost':>16}")
for t in [0.05,0.10,0.20,0.30,0.40,0.50,0.60,0.70,0.80,0.90]:
    ab = sum(1 for _, s in oo_s if s < t)
    lost = sum(1 for _, s in in_s if s < t)
    print(f"{t:>10.2f} {ab:>10}/{len(oo_s)}     {lost:>10}/{len(in_s)}")
json.dump({"in_scope": in_s, "oos": oo_s}, open(os.path.join(here, "threshold_scores.json"), "w"), indent=2)
