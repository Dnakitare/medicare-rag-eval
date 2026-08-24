"""Answer-quality eval — free-text (default) or --structured (wk7).

Programmatic checks (deterministic, trustworthy — ADR-0004):
  correct    : answer contains expect_answer
  cited_src  : a cited passage is from expect_source
  grounded   : a cited passage contains expect_substring
  abstained  : model declined (answer_found=false / "not found")
Structured mode (--structured) adds:
  quote_ok   : supporting_quote appears verbatim in a cited passage (the model's
               own evidence is real, not hallucinated)
--judge adds the noisy local-model faithfulness check (use as a signal, not truth).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rag.llm import chat  # noqa: E402


def get_answer(question: str, structured: bool):
    if structured:
        from rag.extract import grounded_answer
        return grounded_answer(question)
    from rag.answer import answer
    return answer(question)


def load_gold() -> list[dict]:
    for name in ("gold.jsonl", "gold.example.jsonl"):
        p = ROOT / "eval" / name
        if p.exists():
            return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    sys.exit("No gold set found.")


def load_oos() -> list[dict]:
    p = ROOT / "eval" / "gold_oos.jsonl"
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []


def abstained(a) -> bool:
    return getattr(a, "answer_found", True) is False or "not found in the provided sources" in a.text.lower()


def judge_faithful(a) -> bool:
    if not a.cited:
        return False
    ctx = "\n\n".join(a.passages[n - 1]["text"] for n in a.cited if 1 <= n <= len(a.passages))
    msg = [
        {"role": "system", "content": "You check faithfulness. Reply with exactly YES or NO."},
        {"role": "user", "content": f"CONTEXT:\n{ctx}\n\nANSWER:\n{a.text}\n\n"
                                    "Is every factual claim in ANSWER supported by CONTEXT? Reply YES or NO."},
    ]
    return chat(msg).strip().upper().startswith("YES")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--structured", action="store_true", help="use schema-constrained answers (wk7)")
    ap.add_argument("--judge", action="store_true", help="add local-LLM faithfulness check")
    ap.add_argument("--no-oos", action="store_true", help="skip the out-of-scope abstention set")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    gold = load_gold()
    keys = ["correct", "cited_src", "grounded", "abstained"]
    if args.structured:
        keys += ["fact_aq", "quote_ok"]
    if args.judge:
        keys.append("faithful")
    tally = {k: 0 for k in keys}

    for g in gold:
        a = get_answer(g["query"], args.structured)
        txt = a.text.lower()
        cited_idx = [n for n in a.cited if 1 <= n <= len(a.passages)]
        abst = abstained(a)
        correct = g["expect_answer"].lower() in txt
        cited_src = any(a.passages[n - 1]["source"] == g["expect_source"] for n in cited_idx)
        grounded = any(g["expect_substring"].lower() in a.passages[n - 1]["text"].lower() for n in cited_idx)

        tally["correct"] += correct
        tally["cited_src"] += cited_src
        tally["grounded"] += grounded
        tally["abstained"] += abst
        if args.structured:
            q = getattr(a, "supporting_quote", "").lower().strip()
            # format-appropriate correctness: terse structured answers often omit the
            # verbose expect_answer phrase but their cited quote carries the fact.
            tally["fact_aq"] += g["expect_answer"].lower() in (txt + " " + q)
            tally["quote_ok"] += bool(q) and any(q in a.passages[n - 1]["text"].lower() for n in cited_idx)
        if args.judge:
            tally["faithful"] += judge_faithful(a)

        if args.verbose:
            flags = "".join(c if v else "·" for c, v in
                            [("C", correct), ("S", cited_src), ("G", grounded), ("A", abstained)])
            print(f"[{flags}] {g['query']}\n      {a.text.strip()[:150]}")

    n = len(gold)
    mode = "structured" if args.structured else "free-text"
    print(f"\nAnswer eval ({mode}) over {n} gold QAs:")
    labels = {"correct": "correct (answer only)", "cited_src": "cited expected source",
              "grounded": "citation grounded", "abstained": "abstained",
              "fact_aq": "correct (answer+quote)", "quote_ok": "supporting-quote real",
              "faithful": "faithful (local judge)"}
    for k in keys:
        print(f"  {labels[k]:26} {tally[k] / n:.2f}  ({tally[k]}/{n})")

    # Out-of-scope: the correct behavior is to ABSTAIN, not invent an answer.
    oos = [] if args.no_oos else load_oos()
    if oos:
        ok = 0
        for g in oos:
            a = get_answer(g["query"], args.structured)
            if abstained(a):
                ok += 1
            elif args.verbose:
                print(f"[HALLUCINATED] {g['query']}\n      {a.text.strip()[:150]}")
        m = len(oos)
        print(f"\nOut-of-scope ({mode}) over {m} unanswerable queries:")
        print(f"  {'abstained (correct)':26} {ok / m:.2f}  ({ok}/{m})")
        print(f"  {'hallucinated an answer':26} {(m - ok) / m:.2f}  ({m - ok}/{m})")


if __name__ == "__main__":
    main()
