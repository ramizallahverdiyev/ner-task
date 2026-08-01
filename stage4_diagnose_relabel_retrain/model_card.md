---
license: unknown
language:
- en
base_model: distilbert-base-uncased
pipeline_tag: token-classification
pretty_name: NER Stage 4 - Diagnose, Relabel, Retrain
---

# NER Stage 4 — Diagnose, Relabel, Retrain

Published at: https://huggingface.co/ramiz0/ner-stage4-diagnose-relabel-retrain-model

This is the Stage 4 output of a 4-stage applied NER project: a
`distilbert-base-uncased` token-classification model fine-tuned on
[`ramiz0/ner-stage4-diagnose-relabel-retrain`](https://huggingface.co/datasets/ramiz0/ner-stage4-diagnose-relabel-retrain)
(773 train / 194 test records, no validation split), retrained after
diagnosing the 10 concrete problem patterns found in
[Stage 3's](https://huggingface.co/ramiz0/ner-stage3-first-model-run) out-of-dataset wild QA.

## Model details

- **Base model:** `distilbert-base-uncased` (~66.4M parameters, 253.9 MB on
  disk) — unchanged from Stage 3.
- **Task:** token classification, 17-label BIO scheme (`O` + `B-`/`I-` per
  entity type).
- **Training:** 8 epochs (up from Stage 3's 5), batch size 16, learning
  rate 5e-5, weight decay 0.01, warmup ratio 0.1, max sequence length 128
  tokens.
- **Inference postprocess:** adjacent same-label predicted spans with no
  intervening punctuation are merged (e.g. "Prime" + "Minister" -> "Prime
  Minister"), fixing pattern 2 from Stage 3's wild QA. Reported metrics
  below already include this postprocess.
- **Resources (CPU):** 415 MB RSS after load, 601 MB peak during
  inference, 84.4 sentences/sec single-sentence throughput on 16 threads
  (comparable to Stage 3 — same architecture).

## Metrics (seqeval, entity-level, with merge postprocess applied)

| Split | Precision | Recall | F1 |
|---|---|---|---|
| Train | 0.86 | 0.82 | 0.84 |
| Test | 0.59 | 0.60 | 0.59 |

Test micro F1 improved from Stage 3's 0.55 to 0.59. Per-label test F1:
PERSON 0.57 (down from 0.68 — a regression, see report.md), ORGANIZATION
0.40 (up from 0.27), LOCATION 0.66 (up from 0.61), TIMEDATE 0.71 (up from
0.67), AMOUNT 0.62 (roughly flat), JOB 0.81 (up from 0.70), WORKOFART 0.24
(up from 0.16), PRODUCT 0.22 (up from 0.00).

Full diagnosis of the 10 Stage 3 patterns, fixes applied, and a pattern-by-
pattern re-evaluation (improved/regressed/unresolved) are in
`stage4_diagnose_relabel_retrain/report.md` in the
[project repo](https://github.com/ramizallahverdiyev/ner-task).

## Labels

- `PERSON`: a named person, including given names and surnames.
  Example: `<PERSON>Barack Obama</PERSON>` / `<PERSON>Sarah Chen</PERSON>`.
- `ORGANIZATION`: a named company or institution.
  Example: `<ORGANIZATION>Google</ORGANIZATION>` / `<ORGANIZATION>Mayo Clinic</ORGANIZATION>`.
- `LOCATION`: a named place such as a city, country, region, street, landmark, or geographic area.
  Example: `<LOCATION>Berlin</LOCATION>` / `<LOCATION>New York City</LOCATION>`.
- `TIMEDATE`: an expression that places something on a timeline, including dates, clock times, and durations used as time.
  Example: `<TIMEDATE>March 15, 2024</TIMEDATE>` / `<TIMEDATE>50 minutes</TIMEDATE>`.
- `PRODUCT`: a named commercial product, device, or branded good.
  Example: `<PRODUCT>iPhone 15</PRODUCT>` / `<PRODUCT>MacBook Pro</PRODUCT>`.
- `WORKOFART`: a named creative or published work such as a book, film, song, or titled publication.
  Example: `<WORKOFART>Oppenheimer</WORKOFART>` / `<WORKOFART>Spider-Man: Brand New Day</WORKOFART>`.
- `JOB`: an occupational title or formal work role when it functions as such in the sentence.
  Example: `<JOB>software engineer</JOB>` / `<JOB>CEO</JOB>`.
- `AMOUNT`: a measurable or countable quantity, not a time or date expression.
  Example: `<AMOUNT>50</AMOUNT>` tickets / `<AMOUNT>120,000</AMOUNT>`.

## Baseline labeling rules

These are the fixed main rules (unedited from the source task spec).

- A labeled mention should cover the entity itself, not the surrounding grammar.
  Correct: `She visited <LOCATION>Paris</LOCATION> yesterday.` Incorrect: labeling `visited Paris yesterday` as one span.
- Articles, prepositions, conjunctions, and other function words should stay outside the span unless they are truly part of the proper name.
  Correct: `He works at <ORGANIZATION>Google</ORGANIZATION>.` Incorrect: `<ORGANIZATION>at Google</ORGANIZATION>`.
  `<ORGANIZATION>The New York Times</ORGANIZATION>` should keep `The` when it belongs to the established name.
- Bare type-words and category descriptors (words that name a category rather than a specific entity) should not be labeled on their own. Examples include "person", "company", "organization", "team", "hospital", "city", "product", "book", and "quantity".
  `The company hired 200 people.` should leave `company` unlabeled.
  `She joined <ORGANIZATION>Acme Corp</ORGANIZATION>.` should still label the named organization.
  `The person who called did not leave a name.` should leave `person` unlabeled.
- A multi-word name should be one span when it forms one real named entity; separate entities should be labeled separately.
  `<PERSON>Barack Obama</PERSON>` should be one span. `<PERSON>Barack</PERSON> and <PERSON>Michelle</PERSON>` should be two spans.
- Coordinated names should be separate spans, unless the conjunction is part of one established name.
  `<ORGANIZATION>Google</ORGANIZATION> and <ORGANIZATION>Microsoft</ORGANIZATION>` should be two spans.
  `<ORGANIZATION>Johnson & Johnson</ORGANIZATION>` should stay one span because `&` belongs to the name.
- Ordinary punctuation and stray whitespace should stay outside spans, unless the punctuation belongs to the name or abbreviation.
  `He moved to <LOCATION>Berlin</LOCATION>.` should leave the final period outside the span.
  `<ORGANIZATION>AT&T</ORGANIZATION>` should keep `&` inside the span.
- Possessive markers should stay outside the span unless the full possessive form is the name.
  `<PERSON>Maria</PERSON>'s laptop` should leave `'s` outside the span.
- Labels should follow context, not surface form alone. The same words may be an organization in one sentence and a place in another.
  `She works at <ORGANIZATION>Cambridge University</ORGANIZATION>.` / `The conference was held in <LOCATION>Cambridge</LOCATION>.`
- Quantities used as time should be labeled as `TIMEDATE`, not `AMOUNT`.
  `She bought <AMOUNT>50</AMOUNT> tickets.` / `The train arrives in <TIMEDATE>50 minutes</TIMEDATE>.`

## Full policy (baseline + 14 Stage 1 additions, unchanged through Stage 4)

No new policy rule was added in Stage 4. Full rule text with examples:
[`ramiz0/ner-stage1-rulecraft-cleanup`](https://huggingface.co/datasets/ramiz0/ner-stage1-rulecraft-cleanup)
dataset card.

1. TIMEDATE specificity — only placeable/measurable values count.
2. PERSON via referring nickname — a fixed individual label, not a generic role word.
3. JOB context-functional scope — role-in-action, not demographic/statistical or org-unit usage.
4. AMOUNT magnitude test — real approximate magnitudes count; zero-magnitude words don't.
5. Honorifics excluded from all labels.
6. PRODUCT extends to named technologies without a commercial owner.
7. Countries/kingdoms are LOCATION regardless of grammatical role or fictionality.
8. Age expressions are AMOUNT.
9. League/competition names are ORGANIZATION.
10. Named businesses/venues are ORGANIZATION, not LOCATION.
11. Award/prize titles are left unlabeled.
12. Institutional documents/reports are WORKOFART.
13. Legal citations require actual title text.
14. Usernames/handles and transcript role-placeholders are PERSON.

## Usage

```python
from transformers import pipeline

ner = pipeline("token-classification", model="ramiz0/ner-stage4-diagnose-relabel-retrain-model", aggregation_strategy="simple")
ner("Barack Obama visited Berlin on March 15, 2024.")
```

Note: the reported metrics include a post-processing merge step for
adjacent same-label spans (see `postprocess.py` in the project repo) that
the raw `pipeline()` output above does not apply automatically.
