# medicare-rag-eval

The evaluation harness, question sets, and raw results behind the essay
[The manual says 15 months. It hasn't been 15 months since 2006.](https://dnakitare.github.io/writing/the-manual-says-15-months.html)

Published so the numbers in that essay are checkable. Every claim it makes about
Medicare is verifiable against the public CMS documents named below; every claim
it makes about the system is verifiable against `eval/grading_dump.json`.

## What this is

A local RAG system was built over three CMS documents to answer questions about
durable medical equipment and telehealth: hybrid retrieval (dense + BM25 with RRF),
a cross-encoder reranker, and a 7B model producing structured answers with citations,
running entirely on a laptop with no hosted inference.

This repository contains the evaluation side of that project, not the pipeline.

## The corpus

Three public CMS publications, not redistributed here. Download them directly:

| document | revision |
|---|---|
| Medicare Benefit Policy Manual, Chapter 15 (`100-02`) | Rev. 13774, issued 05-08-26 |
| Medicare Claims Processing Manual, Chapter 20 (`100-04`) | Rev. 12557, issued 03-28-24 |
| MLN901705, Telehealth and Remote Monitoring | December 2025 edition |

`fixtures/` holds two synthetic files that were left in the index by mistake. They
are here because the essay discusses them: one of them is the top-ranked citation
for a question in the evaluation set, which means one scored answer came from a
smoke-test fixture rather than from CMS. Each file says so on its first line.

## The evaluation set

- `eval/gold.jsonl` — 16 questions answerable from the corpus
- `eval/gold_oos.jsonl` — 7 questions verified absent from it, where abstaining is correct
- `eval/gold.example.jsonl` — an earlier 7-question fixture set, used before the real corpus was indexed

Six of the sixteen `expect_answer` strings appear verbatim in their own `query`
(`medical purpose`, `prosthetic`, `service contracts`, `physiologic`, `audio-only`,
`RTM`). That leak is why a stub which merely restates the question scores 6/16 on the metric below.
The essay does not cover the baseline work; it is here and in `eval/RESULTS.md`.

## Scripts

| file | what it does |
|---|---|
| `answer_eval.py` | the original scoring harness: substring `correct`, cited-source, grounded-in-passage, abstention |
| `retrieval_eval.py` | retrieval quality against `expect_source` |
| `closed_book.py` | answers every gold question with no retrieval, to establish what the model already knows |
| `threshold_sweep.py` | top rerank score per question, swept across abstention thresholds |
| `grading_dump.py` | runs all 23 items through the real pipeline and dumps outputs for hand grading |

The scripts import a `rag` package that is not in this repository. They are here to
show how each number was produced and what was measured, not to run as-is.

## Results

`eval/RESULTS.md` has the full tables. The three that matter:

**The metric's floor is not zero.** Scored with the harness's own rule
(`expect_answer.lower() in answer.lower()`):

| condition | harness | correct |
|---|---|---|
| empty string | n/a | 0/16 |
| stub that restates the question | n/a | 6/16 |
| 1.5B, no retrieval | `closed_book.py` | 5/16 |
| 7B, no retrieval | `closed_book.py` | 10/16 |
| top-1 retrieved chunk pasted verbatim, no generation | retrieval only | 15/16 |
| 1.5B fine-tuned, with retrieval | FT harness, raw prompt | 10/16 |
| 1.5B base, with retrieval | FT harness, raw prompt | 15/16 |
| 7B, with retrieval | FT harness, raw prompt | 15/16 |
| 7B, real structured pipeline | `grading_dump.py` | 12/16 |

**These are not all one experiment.** Three different scripts produced these rows and only
the ones sharing a harness are directly comparable. The structured pipeline scores lower
than the raw-prompt path because it can abstain and because its terse answers miss the
literal expected string; that gap is the point of the hand grading below, not a regression.
The `grading_dump.json` in this repo is the structured-pipeline run, so 12/16 is the number
you can reproduce from published data. The 15/16 rows come from a fine-tuning comparison
whose per-item outputs were not retained.

**The system quotes, and 2 of its quotes are fabricated.** 15 of 23 answers fill the
`supporting_quote` field; 13 of those 15 appear verbatim in a cited passage. The other two are
paraphrases presented as quotations, with a correct citation attached. See `quote_verbatim` in
`eval/grading_dump.json`.

**Hand grading disagrees with the metric.** On the 16 in-scope items the metric
scored 12 correct and a human scored 13, disagreeing on 3 in both directions.
The essay does not enumerate them; `eval/grading_dump.json` has every item's output. No agreement statistic is quoted,
because at n=16 with these marginals none of them supports anything: a bootstrap
of Cohen's kappa spans [-0.14, 1.00]. The human grading was also not blinded to
the metric's verdict, which anchors it.

**A relevance score is not an answerability signal.** `eval/threshold_scores.json`
has the top rerank score for all 23 questions. "Is bariatric surgery covered by
Medicare," which appears nowhere in the corpus, scores 0.916, higher than three
of the sixteen genuine questions.

## Scope and limits

Sixteen answerable questions and seven unanswerable ones, one run, temperature 0.
Enough to show these failures exist, nowhere near enough to say how often they
happen. The questions were written by one person from passages he had already read,
which is the known way to produce lexical-overlap artifacts, and the 6/16 leak is
that mechanism showing up.

This is benefit-category policy, claims processing, and billing guidance. It contains
no National or Local Coverage Determinations and no Policy Articles, so nothing here
can answer whether an item is covered for a patient. It is also fee-for-service only.

No patient data was involved at any point.

## License

MIT for the code. The CMS documents are US government works and are not included here.
