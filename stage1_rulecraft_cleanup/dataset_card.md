---
license: unknown
task_categories:
- token-classification
language:
- en
pretty_name: NER Stage 1 - Rulecraft and Cleanup
---

# NER Stage 1 — Rulecraft and Cleanup

Published at: https://huggingface.co/datasets/ramiz0/ner-stage1-rulecraft-cleanup

This is the Stage 1 output of a 4-stage applied NER project: a corrected version
of the 100-record starter dataset
[`polygraf-ai/applied-nlp-ner-candidate-starter-100`](https://huggingface.co/datasets/polygraf-ai/applied-nlp-ner-candidate-starter-100),
relabeled under the annotation policy below, with 2 records removed (spam/gibberish
text where entity tags sat inside meaningless word-salad content, not real
language).

**Fields:** `unique_index`, `source_text`, `privacy_mask` (list of
`{start, end, label, value}`).

**Stats:** 98 records (100 - 2 removed). 726 total entity spans. 53 of the 98
records had at least one correction applied.

| Label | Before | After |
|---|---|---|
| PERSON | 153 | 121 |
| ORGANIZATION | 80 | 99 |
| LOCATION | 101 | 76 |
| TIMEDATE | 164 | 129 |
| PRODUCT | 87 | 83 |
| WORKOFART | 59 | 56 |
| JOB | 100 | 82 |
| AMOUNT | 83 | 80 |
| (invalid `COMPANY` label, eliminated) | 8 | 0 |
| **Total** | **835** | **726** |

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

## Full policy (baseline + Stage 1 additions)

The baseline rules above do not cover every case. The following rules were added
to close specific gaps found while reviewing the starter dataset. Each rule
targets a concrete ambiguity, is grounded in an example from the dataset, and
does not contradict the baseline or the other added rules.

1. **TIMEDATE specificity.** A span may only be labeled `TIMEDATE` if it denotes
   a specific, placeable point in time or a measurable duration — an explicit
   date, clock time, duration with a unit or count, or a named calendar period
   (holiday, quarter, season tied to context). Vague deictic or aspectual words
   that mark tense/recency without specifying an actual time value (e.g. `now`,
   `moment`, `again`, `ever`, `never`, `before`, `always`, `yet`, `just`,
   `already`, `initially`, `recent`, `latest`, `long`) must not be labeled, even
   though they are temporal in a loose grammatical sense.
   Test: does the span have a placeable value or measurable magnitude? (`past
   couple of days` passes — rough but real magnitude; `some time` fails — no
   magnitude at all.)

2. **PERSON via referring nickname.** A span may be labeled `PERSON` when it is
   a moniker, alias, or nickname used as a fixed referring label for one
   specific individual within the text — the same word used consistently to
   pick out that one person — even if it is not a conventional given or family
   name. Does not extend to generic role/category nouns referring to no
   particular individual (e.g. "waiter," "dealer"); those stay excluded under
   the bare-category-descriptor rule, or fall under `JOB` if functioning as an
   occupational title in context.
   Example: `<PERSON>Dreads</PERSON>: the only guy that can dance` — a
   nickname used repeatedly to refer to one specific performer.

3. **JOB context-functional scope.** `JOB` applies whenever an occupational
   noun functions as an occupational descriptor of who is doing/being something
   in the sentence — a named individual, a clear single referent, or a group
   acting collectively (e.g. "bouncers turned him away"). It does not apply
   when the same noun is used purely as a demographic/statistical count subject
   (e.g. "13.3% of the man-days... were worked by black bricklayers" — a
   percentage subject, not a role-in-action), nor to industry/sector/
   department/team nouns that name an organizational unit rather than an
   occupation (e.g. "energy sector," "analytics team").
   Example kept: `<JOB>bouncers</JOB> at the door` — group acting.

4. **AMOUNT magnitude test.** `AMOUNT` may be applied to approximate-but-real
   magnitude words/expressions that carry a genuine, even if imprecise,
   order-of-magnitude value (e.g. "hundred," "thousands," "dozens," "several
   hundred") in addition to exact numerals. It must not be applied to spans
   with zero resolvable magnitude (e.g. "many," "some," "a lot") or to words
   that are not quantities at all.
   Example kept: `<AMOUNT>hundred</AMOUNT> bears` — real order-of-magnitude
   value.

5. **Honorifics excluded from all labels.** Courtesy/professional honorifics
   attached to a name (`Mr.`, `Ms.`, `Mrs.`, `Dr.`, `Prof.`, `Cardinal`, etc.)
   are never labeled `PERSON` or `JOB` — only the bare name is `PERSON`. A bare
   honorific does not "function as" a role description; it is a form of
   address, not a description of what the person does.
   Example: `Ms. <PERSON>Charlie</PERSON>` — honorific stays outside the span.

6. **PRODUCT extends to named technologies without a commercial owner.**
   `PRODUCT` includes any specifically named, identifiable technology, tool,
   language, or platform that a person can use, install, or reference by name,
   regardless of whether it has a single commercial/brand owner. Open standards
   and specs (SQL, HTML) count the same as clearly branded software.
   Example: `<PRODUCT>SQL</PRODUCT> query engine` — no single commercial
   owner, still PRODUCT.

7. **Countries/kingdoms are LOCATION regardless of grammatical role or
   fictionality.** A named country- or kingdom-type political entity is
   labeled `LOCATION`, whether it is the grammatical subject of an action or
   referred to as a place, and whether it is real or fictional.
   Example: `<LOCATION>Spade Kingdom</LOCATION>'s commandor's poison attack`
   — a fictional kingdom, treated the same as a real country acting as an
   agent (e.g. "North Korea says...").

8. **Age expressions are AMOUNT.** Age expressions ("N-year-old," "aged N
   years old") are labeled `AMOUNT`. They are a measured quantity/count
   attached to a person, not a duration doing scheduling/timing work in the
   sentence.
   Example: a `<AMOUNT>19-year-old</AMOUNT>`.

9. **League/competition names are ORGANIZATION.** Named sports
   leagues/competitions are labeled `ORGANIZATION`, consistent with treating
   them as a named institution.
   Example: `<ORGANIZATION>La Liga</ORGANIZATION> side`.

10. **Named businesses/venues are ORGANIZATION, not LOCATION.** Any named
    business or venue with a proper name is `ORGANIZATION` — a named
    institution you visit is still an institution, not merely a place.
    Applies to restaurants, venues, casinos, clinics, studios, and similar
    named businesses.
    Example: `<ORGANIZATION>Joyride Taco House</ORGANIZATION>` — was
    LOCATION in the source data, corrected.

11. **Award/prize titles are left unlabeled.** Award and prize titles do not
    fit any of the 8 labels — `WORKOFART` is restricted to creative/published
    works, and an award/distinction is not one. Since the label set is fixed,
    an award name that doesn't fit any label is left unlabeled rather than
    stretched into the closest-sounding one.
    Example: `<ORGANIZATION>Costume Designers Guild</ORGANIZATION> Excellence
    Award` — the granting body stays labeled; the award title itself does
    not.

12. **Institutional documents/reports are WORKOFART.** Named formal
    institutional documents (strategy papers, audit reports, and similar
    titled publications) are labeled `WORKOFART`, matching the "titled
    publication" wording directly.
    Example: `<WORKOFART>Project Performance Audit Report</WORKOFART>
    (PPAR)`.

13. **Legal citations require actual title text.** A legal/regulatory
    citation is labeled `WORKOFART` only if actual title text is present
    (e.g. a spelled-out case name or written-out code name), not when it is a
    bare locator string of volume/section/page numbers with no title
    expressed (e.g. "462 U.S. 352, 358," "41 CFR § 60-11").
    Example excluded: `CFR` in "41 CFR § 60-11 et seq." — no title text, just
    a locator.

14. **Usernames/handles and transcript role-placeholders are PERSON.** A
    username or handle that functions as a fixed referring label for one
    specific individual is `PERSON` (extends rule 2 to formatted
    identifiers), and dialogue-transcript speaker labels ("Person1"/"Person2")
    are also `PERSON`, since each consistently refers to one specific speaker
    across the dialogue.
    Example: `<PERSON>otavio.telin</PERSON>`; `<PERSON>Person1</PERSON>:
    Which route are you interested in?`

## Corrections summary

- 98 of 100 source records retained; 2 removed (spam/gibberish text where
  tagged entities sat inside meaningless generated word-salad, not real
  language — training on them would teach entity extraction from noise).
- 53 of the 98 retained records had at least one label/span correction.
- Corrections included: removing the invalid `COMPANY` label (remapped to the
  correct label per baseline), fixing span boundary errors, merging
  multi-word person names that were fragmented into multiple spans (a direct
  baseline requirement, not a new policy call), and applying the 14 rules
  above.
- Source dataset: [`polygraf-ai/applied-nlp-ner-candidate-starter-100`](https://huggingface.co/datasets/polygraf-ai/applied-nlp-ner-candidate-starter-100).
