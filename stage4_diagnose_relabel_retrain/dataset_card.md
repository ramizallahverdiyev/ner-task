---
license: unknown
task_categories:
- token-classification
language:
- en
pretty_name: NER Stage 4 - Diagnose, Relabel, Retrain
---

# NER Stage 4 — Diagnose, Relabel, Retrain

Published at: https://huggingface.co/datasets/ramiz0/ner-stage4-diagnose-relabel-retrain

This is the Stage 4 output of a 4-stage applied NER project: Stage 2's
dataset ([`ramiz0/ner-stage2-dataset-expansion`](https://huggingface.co/datasets/ramiz0/ner-stage2-dataset-expansion),
748 records) plus 219 new records targeting the 10 concrete problem
patterns found in Stage 3's out-of-dataset wild QA (documented in
`stage3_first_model_run/report.md` in the
[project repo](https://github.com/ramizallahverdiyev/ner-task)).

**Fields:** `unique_index` (not present; carried over as `source`),
`source_text`, `privacy_mask` (list of `{start, end, label, value}`).

**Stats:** 967 total records (748 Stage 1+2 + 219 new). Train: 773 / Test:
194 (79.9% / 20.1%) — the existing 748 records' train/test membership is
unchanged from Stage 2; only the 219 new records were freshly split.

| Label | Stage 1+2 | Stage 4 final | Floor | Ceiling | OK? |
|---|---|---|---|---|---|
| PERSON | 600 | 600 | 200 | 600 | yes |
| ORGANIZATION | 600 | 600 | 200 | 600 | yes |
| LOCATION | 600 | 600 | 200 | 600 | yes |
| TIMEDATE | 600 | 600 | 200 | 600 | yes |
| AMOUNT | 262 | 600 | 200 | 600 | yes |
| JOB | 449 | 572 | 200 | 600 | yes |
| WORKOFART | 278 | 291 | 200 | 600 | yes |
| PRODUCT | 88 | 112 | 200 | 600 | **NO** |

PRODUCT still falls short of the 200 floor despite dedicated Stage 4
sourcing effort (aircraft/vehicle/brand-targeted categories) — same
persistent shortfall first identified in Stage 2 (decision 11), now
confirmed to survive a second, targeted attempt. Documented as an ongoing
known limitation, not chased further in this round.

## What changed from Stage 2 (see stage4_decisions.md / report.md for full reasoning)

Diagnosis of Stage 3's 10 wild-QA problem patterns resolved to: 9 of 10
as data-coverage gaps (closed via targeted new sourcing + templated
reinforcement examples), 1 (pattern 6, generic common-noun phrases
over-tagged ORGANIZATION) as already covered by the existing baseline
definition of ORGANIZATION, enforced here with one additional mechanical
filter (drop ORGANIZATION candidates with no capitalized token) rather
than a new policy rule. **No new policy rule was added in Stage 4** — the
full policy below is unchanged from Stage 1.

New sourcing/generation for Stage 4:
- Targeted Wikipedia/Wikinews categories for rare/non-Western proper nouns,
  neighborhoods, brand articles, and aircraft/vehicle designators.
- Extended JOB gazetteer (broader medical/professional role vocabulary).
- New `PRODUCT_ALPHANUMERIC_PATTERN` regex for vehicle/aircraft/equipment
  model designators (e.g. "RC-135U", "F-16").
- New `BRAND_PERSON_NAMES` gazetteer forcing brand names shaped like
  personal names (e.g. "Hugo Boss") to ORGANIZATION.
- 26 templated synthetic reinforcement records for multi-word span
  consistency (JOB titles, "the <Country>", relative TIMEDATE phrases,
  currency AMOUNT) and same-entity labeling consistency ("U.S." /
  "United States", "CNN").

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

No new policy rule was added in Stage 4 (see stage4_decisions.md pattern 6:
the one candidate gap was already covered by the existing baseline
definition of ORGANIZATION). Full rule text with examples:
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

## Corrections/additions summary

- 219 new records added on top of Stage 1+2's 748, selected via the same
  scarcity-weighted greedy algorithm and 200/600 floor/ceiling balance
  criterion as Stage 2 (decision 2), applied to a pool built from
  targeted Wikipedia/Wikinews sourcing + templated synthetic examples.
- Dedupe: exact-match + substring against the full existing dataset
  (Stage 2 decision 3), dropping 20 exact and 3 substring duplicates from
  the new pool.
- All new records passed the same mechanical policy-correction pass as
  Stage 1/2 (baseline + 14 rules), plus one Stage-4-specific filter
  enforcing the existing ORGANIZATION definition (drop candidate
  ORGANIZATION spans with no capitalized token).
- Source: targeted Wikipedia/Wikinews categories (see
  `fetch_wiki_sources.py`) + 26 templated synthetic records (see
  `synthetic_reinforcement.py`), reusing Stage 2's WikiANN/Wikipedia base.
