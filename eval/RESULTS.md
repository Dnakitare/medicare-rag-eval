# Re-run 2026-08-23: baselines the original arc never established

Run against the archived pipeline, same index, same models, temp 0.
New scripts: `eval/closed_book.py`, `eval/threshold_sweep.py`.

> **Note on harnesses.** The rows below were produced by three different scripts and are
> only comparable within a group. `closed_book.py` uses a plain system prompt and no
> retrieval. The fine-tuning comparison ("FT harness") used a bare Context/Question/Answer
> prompt with retrieval but no structured output and no relevance gate. `grading_dump.py`
> runs the real structured pipeline, which emits typed citations and can abstain. The
> ADRs referenced below are design records from the original project and are not published.

## 1. The `correct` metric has a floor of 0.38, not 0

Scored with the exact rule in `answer_eval.py` (`expect_answer.lower() in answer.lower()`):

| condition | correct |
|---|---|
| empty string | 0/16 (0.00) |
| **echo stub — answer is literally the question restated** | **6/16 (0.38)** |
| closed-book qwen2.5:1.5b, no retrieval | 5/16 (0.31) |
| closed-book qwen2.5:7b, no retrieval | 10/16 (0.62) |
| ft-1.5b + retrieval (FT harness) | 10/16 (0.62) |
| base-1.5b + retrieval (FT harness) | 15/16 (0.94) |
| prompted-7b + retrieval (FT harness) | 15/16 (0.94) |

**6 of 16 `expect_answer` strings appear verbatim in their own `query`**: `medical purpose`,
`prosthetic`, `service contracts`, `physiologic`, `audio-only`, `RTM`.

Consequences:
- The 0.94 "tie" in the FT harness sits on a metric whose null baseline is 0.38.
- **The fine-tuned 1.5B *with* retrieval (0.62) scored exactly what a 7B scores with no
  retrieval at all (0.62).** FT didn't just fail to help, it erased retrieval's contribution.
- **The 1.5B closed-book (0.31) scores BELOW the echo stub (0.38).**

## 2. The threshold sweep contradicts the justification originally given for 0.30

| threshold | OOS abstained | in-scope lost |
|---|---|---|
| 0.05 | 4/7 | **0/16** |
| 0.20 | 4/7 | 1/16 |
| **0.30 (shipped)** | **5/7** | **1/16** |
| 0.40–0.60 | 5/7 | 2/16 |
| 0.70–0.90 | 6/7 | 2/16 |

- **Nearly all the benefit is free at 0.05: 4/7 OOS abstained at zero in-scope cost.**
  Moving 0.05 → 0.30 buys one more OOS abstention and costs one real answer.
- **The original distribution claim was incomplete.** It says in-scope is "mostly 0.91–0.999
  (one outlier 0.399)". There are **two** in-scope outliers: 0.3992 (service contracts) and
  **0.1543 (the ABN question), which the shipped 0.30 gate silently sacrifices.** The ADR
  never mentions it.
- **Bariatric surgery — not in the corpus — scores 0.9160, higher than 12 of the 16 real
  questions.** No threshold separates it. This is "topical relevance, not answerhood" with
  a number on it.

## Hand grading
All 23 items were subsequently hand-graded. In-scope: the substring metric scored 12/16,
a human scored 13/16, disagreeing on 3 items in both directions. See the README.

## 3. The retrieval-only null: the generator contributes nothing measurable

Return the **top-1 reranked chunk verbatim** as the answer. No generation at all. Scored with the same rule.

| condition | correct |
|---|---|
| top-1 chunk dumped verbatim, no LLM | **15/16** |
| FT-harness raw-prompt path, 7B + retrieval | **15/16** |
| **real structured pipeline, 7B** (`grading_dump.py`) | **12/16** |

**Identical.** On this metric the generator adds nothing over pasting the retrieved passage.
This is the real null for a RAG pipeline, and it is far more damaging than the echo stub.

## 4. Three metrics from the same harness, same 16 outputs (zero new inference)

| metric | score | floor (echo stub) |
|---|---|---|
| substring on answer only (the one I reported) | 12/16 | **6/16** |
| answer+quote (`fact_aq`) | 12/16 | 6/16 |
| grounded in cited passage | 13/16 | **0/16** |
| human | 13/16 | n/a |

The harness already contained a metric with a real floor and near-perfect agreement with hand
grading. I steered on the one with a floor of 6.

## 5. Correction to an earlier claim about the gate

Bariatric (0.9160) sits between in-scope 0.9147 and 0.9472. A threshold anywhere in
(0.9160, 0.9472] declines **all 7** out-of-scope at a cost of **3/16** in-scope.
So "the gate has no way to tell the difference" is FALSE on this data. The honest claim:
the shipped 0.30 catches neither hard case, a much higher threshold catches both but costs
3 real questions, and that ordering was read off the same 23 items.

## 6. Stale-policy probe (2026-08-23) — the system DOES serve dead policy, at high confidence

Asked the questions a supplier would actually ask, rather than the gold-set phrasing:

| query | answer | top cite | rerank |
|---|---|---|---|
| "How many months of continuous use is the cap for capped rental DME?" | **"The cap for capped rental DME is 15 months of continuous use."** | Ch.20 PDF | **0.9988** |
| "What is the purchase option for capped rental equipment?" | **"The purchase option is given to beneficiaries during the 10th month of continuous rental use."** | Ch.20 PDF | 0.5989 |

Both answers describe policy eliminated by DRA 2005 §5101(a) effective 2006-01-01... i.e. **twenty years dead**, sourced from the genuine current chapter, top-ranked.

**Why the gold set missed this:** gold item #8 asks "after how many months does ownership pass," whose top citation is `_sample_dme.txt` (a SYNTHETIC FIXTURE) answering "13 months." The gold phrasing accidentally routed around the stale text. **The natural phrasing goes straight to it.**

## 7. ⚠️ INDEX CONTAMINATION

`_sample_dme.txt` and `_sample_rpm.txt` are in the live index. Both open
"SYNTHETIC FIXTURE — not real CMS guidance. For smoke-testing the pipeline only."
`_sample_dme.txt` is the **top citation for gold item #8**. Any claim that the corpus
is "three CMS documents" is inaccurate as to what was actually indexed.

## 8. ⚠️ The `quote` field is EMPTY on all 23 items
So the system never produced a verbatim supporting quote, on any item, including the
ones scored correct. No inference can be drawn from an empty quote field on any single item.
