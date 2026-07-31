# Stage 2 — Dataset Expansion

**Dataset produced:** https://huggingface.co/datasets/ramiz0/ner-stage2-dataset-expansion
**Base dataset:** https://huggingface.co/datasets/ramiz0/ner-stage1-rulecraft-cleanup (98 records)
**Additional source:** [`unimelb-nlp/wikiann`](https://huggingface.co/datasets/unimelb-nlp/wikiann) (English split)
**Scripts:** `stage2_dataset_expansion/`

## Approach

Stage 1's 98 records were expanded to 748 total, all under the same
annotation policy (baseline + 14 rules, unchanged from Stage 1). The
approach and every numeric target below (source mix, balance floor/ceiling,
dedupe method, split ratio, target record count, gazetteer scope) were
decided jointly, one decision at a time, before any code was written — the
full decision record with options considered and reasoning is preserved
alongside the pipeline scripts.

**Sourcing:** a mix strategy — remap an existing annotated dataset for the
labels it already covers well, and freshly label raw text under the full
policy for everything else. WikiANN (CC-licensed) supplied PERSON/
ORGANIZATION/LOCATION spans, already annotated, remapped directly onto our
schema. Wikipedia (targeted at categories chosen for JOB/WORKOFART density
— biographies, novelists, film directors, governors, foreign ministers,
paintings, sculptures, symphonies, product-brand articles) and Wikinews
supplied raw text for the other five labels, labeled fresh.

**First-pass labeling (hybrid):** spaCy (`en_core_web_sm`) covered PERSON,
ORGANIZATION, LOCATION, TIMEDATE and AMOUNT-adjacent categories (DATE,
MONEY, CARDINAL, PERCENT) and WORKOFART natively. JOB has no pretrained
equivalent, so a curated gazetteer of ~80 role/title terms flagged
candidates instead. Every candidate — regardless of source mechanism — was
then run through an automated policy-correction pass (the
mechanically-expressible subset of the 14 rules: bare category words,
vague TIMEDATE/AMOUNT words, honorifics, age expressions, venue/league
LOCATION→ORGANIZATION correction, award-title exclusion, demographic-JOB
exclusion) and validated for span-value and non-overlap invariants, same
auditable standard as Stage 1.

**Balance:** every label was targeted at a floor of 200 / ceiling of 600
total spans (Stage 1 + Stage 2 combined) — the floor forces deliberate
sourcing of rare labels (JOB, WORKOFART were the weakest in Stage 1) and
the ceiling stops easy-to-find labels (PERSON, TIMEDATE) from dominating.
Record selection prioritized records containing the scarcest-label spans
first.

**Dedupe:** exact-match plus substring dedupe (catches truncated/split
versions of the same underlying sentence from overlapping source corpora)
against Stage 1's 98 records and across the new candidate pool.

**Split:** stratified 80/20 train/test by each record's dominant label, so
both splits get proportional coverage of every label including rare ones.
Actual result: 598 train / 150 test (79.9% / 20.1%).

## QA process and problems found

A stratified manual spot-check (prioritizing JOB and WORKOFART — the two
labels with the weakest labeling foundation, since neither has a reliable
pretrained model behind it) was run before finalizing the dataset, per the
decided QA process. It surfaced two real problems that reshaped the
pipeline mid-build, both driven by data evidence rather than assumption:

1. **spaCy performs very unreliably on gaming/tech proper nouns.**
   Wikipedia categories initially added to boost PRODUCT/WORKOFART coverage
   (video games, consoles, smartphones, software) produced systematic
   mislabeling — `Xbox One` tagged PERSON, `PlayStation Store` tagged
   PERSON in one sentence and PRODUCT in another, section headings like
   `=== Multiplayer-only ===` producing nonsense spans. Fix: those
   categories were dropped entirely and replaced with categories in plain
   biographical/business/brand prose (paintings, sculptures, symphonies,
   novels, cosmetics/watch/perfume brand articles), which tested clean.
2. **spaCy's PRODUCT tag has near-zero precision, independent of domain.**
   A second spot-check across the *whole* pool (not just the dropped
   gaming categories) found the PRODUCT tag mislabeling countries
   (`Somaliland`), historical people (`Akbar`), award names (`the Honorary
   Shield`), and section headings (`Notes`) as PRODUCT. This wasn't fixable
   by changing source text — it's the tagger itself. PRODUCT was switched
   to the same trigger-word pattern approach already used for WORKOFART,
   which found only a handful of genuine hits. **PRODUCT did not reach the
   200 floor** — it landed at 88 total spans (Stage 1's 83 plus 5 new).
   This is documented as a known limitation rather than forced with bad
   data; it's flagged for Stage 3/4 QA to watch for as the likely
   weakest-performing label.

A separate implementation bug was also caught and fixed before publishing:
the initial greedy record-selection algorithm, ranked purely by label
scarcity, silently excluded WikiANN entirely (0 of 650 selected) because
Wikipedia/Wikinews records that also carried a scarce label always
outranked WikiANN's PERSON/ORGANIZATION/LOCATION-only records. A reserved
WikiANN quota was added so the decided source mix was actually honored;
the final selection includes 200 WikiANN, 417 Wikipedia, and 33 Wikinews
records.

## Statistics

- **Stage 1 records:** 98
- **New records added:** 650 (200 WikiANN, 417 Wikipedia, 33 Wikinews)
- **Combined total:** 748
- **Train / test split:** 598 / 150 (79.9% / 20.1%, stratified by dominant label)
- **Validation:** 0 span-value errors, 0 overlap errors, 0 duplicate texts, 0 train/test text overlap across all 748 records

| Label | Stage 1 | Final (combined) | Floor | Ceiling | Met? |
|---|---|---|---|---|---|
| PERSON | 121 | 600 | 200 | 600 | yes |
| ORGANIZATION | 99 | 600 | 200 | 600 | yes |
| LOCATION | 76 | 600 | 200 | 600 | yes |
| TIMEDATE | 129 | 600 | 200 | 600 | yes |
| AMOUNT | 80 | 262 | 200 | 600 | yes |
| JOB | 82 | 449 | 200 | 600 | yes |
| WORKOFART | 56 | 278 | 200 | 600 | yes |
| PRODUCT | 83 | 88 | 200 | 600 | **no** (documented limitation) |

## Representative examples

**WikiANN record, remapped to our schema:**
`<ORGANIZATION>Dyersburg High School</ORGANIZATION>, <LOCATION>Dyersburg</LOCATION>`

**Wikipedia, JOB freshly labeled via gazetteer, TIMEDATE via spaCy:**
`With the development of the <TIMEDATE>24-hour</TIMEDATE> news cycle and
dedicated cable news television channels, the role of the <JOB>anchor</JOB>
evolved.`

**Wikipedia, PRODUCT via trigger pattern (one of the small number of
genuine hits):**
`In <TIMEDATE>1987</TIMEDATE>, <AMOUNT>7</AMOUNT> Up introduced
<PRODUCT>Spot</PRODUCT>, the red-orange dot in the <AMOUNT>7</AMOUNT> Up
logo anthropomorphized into a mascot.`
