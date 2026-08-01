# NER Task — Full Project Report

A 4-stage applied NER project: reviewing and correcting an annotated
starter dataset, expanding it, training a token-classification model,
then diagnosing and improving it based on model behavior on out-of-dataset
text.

## Hugging Face artifacts produced

| Stage | Type | URL |
|---|---|---|
| 1 | Dataset | https://huggingface.co/datasets/ramiz0/ner-stage1-rulecraft-cleanup |
| 2 | Dataset | https://huggingface.co/datasets/ramiz0/ner-stage2-dataset-expansion |
| 3 | Model | https://huggingface.co/ramiz0/ner-stage3-first-model-run |
| 4 | Dataset | https://huggingface.co/datasets/ramiz0/ner-stage4-diagnose-relabel-retrain |
| 4 | Model | https://huggingface.co/ramiz0/ner-stage4-diagnose-relabel-retrain-model |

Each stage's own `report.md` (in its folder) contains the same content as
the section below, plus is kept alongside its scripts/data for reference.

---

## Stage 1 — Rulecraft and Cleanup

**Dataset produced:** https://huggingface.co/datasets/ramiz0/ner-stage1-rulecraft-cleanup
**Source dataset:** https://huggingface.co/datasets/polygraf-ai/applied-nlp-ner-candidate-starter-100
**Scripts:** `stage1_rulecraft_cleanup/`

### Approach

The starter set was read in full before any correction was made — all 100
records, not a sample — specifically to find recurring ambiguities the
baseline rules don't settle, rather than guessing at fixes case by case. Each
ambiguity was checked against multiple examples in the dataset before being
treated as a real gap worth a rule, so that a rule wasn't written off a single
one-off case.

Once the policy (baseline + 14 added rules, below) was fixed, corrections were
applied programmatically: every span-level and label-level change is an
explicit, auditable operation (remove / relabel / respan / merge / add) keyed
to exact character offsets, checked by assertions so a correction can't
silently fail to apply, and validated afterward for two invariants across the
whole corrected set: every span's `value` matches `source_text[start:end]`
exactly, and no two spans in a record overlap. This traded some flexibility
for auditability — every single change is traceable to a rule or a stated
reason, which matters more here than typing speed.

A second full pass was done after the policy was finalized, specifically
re-checking every already-labeled span in the dataset against the finished
rule set, since some patterns only become visible once the rules exist to
test against. This caught several instances the first read missed (see
"Second-pass findings" below).

### Issues and patterns found

Recurring problems, roughly by frequency:

- **Vague temporal words tagged `TIMEDATE`.** Words like `now`, `moment`,
  `ever`, `already`, `always` carry no actual date/duration value — they mark
  tense, not time. This was the single most frequent issue (~30 instances).
- **Fragmented multi-word person names.** Full names were frequently split
  across 2-3 separate `PERSON` spans instead of one (e.g. "David" / "James" /
  "Thompson" as three spans) — a direct violation of the baseline's own
  multi-word-name rule, found in over 20 places.
- **Named businesses/venues mislabeled `LOCATION` instead of `ORGANIZATION`.**
  Restaurants, casinos, and studios were consistently tagged as places rather
  than institutions, even though baseline's own example (`Mayo Clinic` →
  ORGANIZATION) covers this exact case.
- **An invalid label, `COMPANY`, appearing 8 times** — not one of the 8
  defined labels at all, apparently left over from a different labeling
  schema.
- **Occupational-sounding nouns tagged `JOB` when they weren't describing
  anyone's actual role** — industry/sector/department names ("energy
  sector," "analytics team") and demographic/statistical count subjects
  ("13.3% of ... bricklayers") rather than a role being performed by
  someone.
- **Bare category words labeled on their own** — "product," "city," "movie,"
  "Company" — direct violations of the baseline's bare-category-descriptor
  rule.
- **Two records were pure spam/gibberish** (a drug-ad post that degrades into
  random word salad, and an entirely auto-generated nonsense essay), where
  every tagged entity sat inside meaningless text rather than real language.

### Policy: added rules

Five is stated as a good minimum; 14 were added, each closing a specific,
dataset-grounded gap and checked against the baseline and every other added
rule for contradictions. Full text with examples is in
`stage1_rulecraft_cleanup/dataset_card.md`; summarized here:

1. **TIMEDATE specificity** — only spans with a placeable value or measurable
   magnitude count; vague tense/recency words don't, even though they're
   "temporal" in a loose sense.
2. **PERSON via referring nickname** — a moniker counts as PERSON only if it
   functions as a fixed label for one specific individual, not a generic role
   word.
3. **JOB context-functional scope** — JOB applies to a role-in-action
   (individual or group), not to a role-word used as a demographic/
   statistical subject or an org-unit name.
4. **AMOUNT magnitude test** — same test as rule 1, applied to quantities:
   approximate-but-real magnitudes count ("hundred," "thousands"); zero-
   magnitude words ("many," "some") don't.
5. **Honorifics excluded from all labels** — "Dr.," "Ms.," "Cardinal" etc.
   never get PERSON or JOB; only the bare name is PERSON.
6. **PRODUCT extends to named technologies without a commercial owner** — SQL,
   open standards, etc. count the same as branded software.
7. **Countries/kingdoms are LOCATION** regardless of grammatical role
   (subject of an action or not) or fictionality.
8. **Age expressions are AMOUNT** — a measured quantity attached to a person,
   not a scheduling/timing duration.
9. **League/competition names are ORGANIZATION.**
10. **Named businesses/venues are ORGANIZATION, not LOCATION** — matches
    baseline's own Mayo Clinic example.
11. **Award/prize titles are left unlabeled** — none of the 8 labels actually
    fits an award name; the label set is fixed, so it's left uncovered rather
    than stretched.
12. **Institutional documents/reports are WORKOFART** — matches the "titled
    publication" wording directly.
13. **Legal citations require actual title text** — a bare citation locator
    (volume/page numbers) isn't a "titled publication"; a spelled-out case or
    code name is.
14. **Usernames/handles and transcript role-placeholders are PERSON** —
    extends rule 2 to formatted identifiers (usernames, "Person1"/"Person2"
    dialogue labels).

### Second-pass findings

After the policy was finalized, every labeled span in the dataset was
re-checked against all 14 rules. This surfaced more instances of rules
already decided (e.g. more vague TIMEDATE words, more mislabeled venues), a
batch of straightforward baseline-driven corrections not requiring a new rule
(an internal contradiction where "McDonald's" was tagged both LOCATION and
ORGANIZATION within the same record; a city name tagged ORGANIZATION in a
dateline; several event/activity nouns like "meeting with the board" mistagged
as TIMEDATE), and two new borderline cases resolved by applying the already-
established magnitude test consistently (`every time` and `course of the
research`, both excluded from TIMEDATE for the same reason `some time` is).

### Record removal

Two records (of the original 100) were removed: one is a drug-advertisement
post that degrades partway through into unrelated random words (a known spam
pattern — word-salad appended to evade filters), and one is an entirely
auto-generated nonsense essay (Markov-chain-style text with no real meaning).
In both, the tagged entities are real-looking words sitting inside text that
doesn't actually say anything — keeping them would train the model to extract
entities from noise rather than from context. All other records were kept and
corrected in place.

### Statistics

- **Records reviewed:** 100
- **Records removed:** 2 (see above)
- **Records changed:** 53 of the remaining 98
- **Records unchanged:** 45
- **Total entity spans:** 835 → 726

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
| `COMPANY` (invalid label) | 8 | 0 |

### Representative before/after examples

**Fictional country mislabeled as an institution (rule 7):**
Before: `Asta countered the <ORGANIZATION>Spade Kingdom</ORGANIZATION>'s
<JOB>commandor</JOB>'s poison attack...`
After: `Asta countered the <LOCATION>Spade Kingdom</LOCATION>'s
<JOB>commandor</JOB>'s poison attack...`

**Age never labeled, fragmented name, and a venue mislabeled as a place (rules 8, 10, plus baseline multi-word-name fix):**
Before: `West Ham are hoping to sign <ORGANIZATION>AC Milan</ORGANIZATION>
youngster <PERSON>M'Baye</PERSON> <PERSON>Niang</PERSON> on loan . 19-year-old
has attracted interest from <ORGANIZATION>Everton</ORGANIZATION>...`
After: `West Ham are hoping to sign <ORGANIZATION>AC Milan</ORGANIZATION>
youngster <PERSON>M'Baye Niang</PERSON> on loan . <AMOUNT>19-year-old</AMOUNT>
has attracted interest from <ORGANIZATION>Everton</ORGANIZATION>...`

**Demographic-statistic bricklayers vs. role-in-action bricklayers, and a
bare legal citation (rules 3, 13):**
Before: `...<AMOUNT>13.3</AMOUNT>% of the man-days on
<ORGANIZATION>Furnco</ORGANIZATION>'s <ORGANIZATION>Interlake</ORGANIZATION>
job were worked by black <JOB>bricklayers</JOB>. ...see 41
<WORKOFART>CFR</WORKOFART> § 60-11 et seq.`
After: `...<AMOUNT>13.3</AMOUNT>% of the man-days on
<ORGANIZATION>Furnco</ORGANIZATION>'s <ORGANIZATION>Interlake</ORGANIZATION>
job were worked by black bricklayers. ...see 41 CFR § 60-11 et seq.` (the
percentage-statistic mention loses JOB; the bare citation loses WORKOFART —
both stay JOB/WORKOFART elsewhere in the same record where they describe an
actual person or a spelled-out publication name)

**Named venue corrected from LOCATION to ORGANIZATION (rule 10):**
Before: `...a new spicy hot spot, <LOCATION>Joyride Taco House</LOCATION>
complete with festive decor...`
After: `...a new spicy hot spot, <ORGANIZATION>Joyride Taco House</ORGANIZATION>
complete with festive decor...`

---

## Stage 2 — Dataset Expansion

**Dataset produced:** https://huggingface.co/datasets/ramiz0/ner-stage2-dataset-expansion
**Base dataset:** https://huggingface.co/datasets/ramiz0/ner-stage1-rulecraft-cleanup (98 records)
**Additional source:** [`unimelb-nlp/wikiann`](https://huggingface.co/datasets/unimelb-nlp/wikiann) (English split)
**Scripts:** `stage2_dataset_expansion/`

### Approach

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

### QA process and problems found

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

### Statistics

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

### Representative examples

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

---

## Stage 3 — First Model Run

**Model produced:** https://huggingface.co/ramiz0/ner-stage3-first-model-run
**Dataset used:** https://huggingface.co/datasets/ramiz0/ner-stage2-dataset-expansion (598 train / 150 test, no validation split)
**Scripts:** `stage3_first_model_run/`

### Model and training setup

Base model: `distilbert-base-uncased` (chosen as the smallest reasonable
English token-classification model — a standard, well-supported distilled
BERT variant rather than a larger base/full-size model or an extremely tiny
variant that would be harder to defend as a fair baseline). Fine-tuned as a
17-label BIO token classifier (`O` + `B-`/`I-` for each of the 8 entity
types).

**Hyperparameters:** 5 epochs, batch size 16, learning rate 5e-5, weight
decay 0.01, warmup ratio 0.1, max sequence length 128 tokens (covers 95.7%
of records un-truncated across train+test; the remaining tail, up to 392
tokens, gets truncated). No validation split or early stopping, per the
task spec — evaluation is at the end of each epoch against the held-out
test set, with the epoch-5 checkpoint used as the final model.

### Resources

| Metric | Value |
|---|---|
| Parameters | 66,375,953 (~66.4M) |
| Model disk size | 253.9 MB |
| RSS after model load | 420.2 MB |
| RSS peak during inference | 607.0 MB |
| CPU threads used | 16 |
| Inference throughput (CPU, batch size 1) | 75.6 sentences/sec |

Measured with `measure_resources.py`: loads the saved model, runs 5 warm-up
inferences then times 50 single-sentence inferences over test-set text on
CPU.

### Train + test metrics

seqeval, entity-level (exact span + label match):

| Label | Train precision | Train recall | Train F1 | Test precision | Test recall | Test F1 |
|---|---|---|---|---|---|---|
| PERSON | 0.75 | 0.82 | 0.79 | 0.61 | 0.78 | 0.68 |
| ORGANIZATION | 0.55 | 0.64 | 0.59 | 0.25 | 0.30 | 0.27 |
| LOCATION | 0.78 | 0.85 | 0.81 | 0.60 | 0.63 | 0.61 |
| TIMEDATE | 0.69 | 0.82 | 0.75 | 0.63 | 0.72 | 0.67 |
| AMOUNT | 0.68 | 0.71 | 0.69 | 0.68 | 0.59 | 0.63 |
| JOB | 0.71 | 0.81 | 0.76 | 0.69 | 0.72 | 0.70 |
| WORKOFART | 0.47 | 0.59 | 0.52 | 0.14 | 0.19 | 0.16 |
| PRODUCT | 0.28 | 0.20 | 0.24 | 0.00 | 0.00 | 0.00 |
| **micro avg** | 0.66 | 0.75 | **0.70** | 0.52 | 0.58 | **0.55** |

The train/test gap (0.70 vs. 0.55 micro F1) reflects the small training set
(598 records) relative to an 8-class token-classification task. PRODUCT and
WORKOFART are the weakest labels by a wide margin, consistent with Stage
2's own finding that PRODUCT never reached its balance floor (88 of a
200-600 target) and that neither label has a reliable pretrained tagger
behind its first-pass labeling.

### Wild QA (out-of-dataset samples)

**Sample sourcing:** 30 sentences pulled from the CNN/DailyMail news
dataset (`abisee/cnn_dailymail`), a source distinct from all of Stage 1/2's
sourcing (starter set, WikiANN, Wikipedia, Wikinews). The selection
mechanism — evenly-spaced article sampling across the test split, then
within each article keeping sentences of 6-40 words containing at least one
capitalized token, capped at 2 per article — was adopted per explicit
instruction to pull from a different public source, rather than
independently re-derived. Full predictions: `data/wild_qa_predictions.txt`
/ `data/wild_qa_predictions.json`.

**The 10 problem patterns below were likewise adopted per explicit
instruction** ("select yourself, flag as my call") rather than originated
from independent analysis — flagged here per the project's stated norm
that judgment calls should be attributed accurately.

1. **Subword fragmentation on unfamiliar proper nouns**, splitting into
   wrong or multiple entity types mid-word.
   `<PERSON>Net</PERSON><ORGANIZATION>any</ORGANIZATION><PERSON>ahu</PERSON>`
   (Netanyahu); `<LOCATION>Ya</LOCATION><ORGANIZATION>rmouk</ORGANIZATION>`
   (Yarmouk); `<ORGANIZATION>Ob</ORGANIZATION><LOCATION>ock</LOCATION>`
   (Obock); `<PERSON>Ermenegil</PERSON><ORGANIZATION>do Ze</ORGANIZATION><PERSON>gna</PERSON>`
   (Ermenegildo Zegna).
2. **Adjacent same-type spans that should merge predicted as two separate
   spans instead of one.** `<JOB>Prime</JOB> <JOB>Minister</JOB>`;
   `<LOCATION>the</LOCATION> <LOCATION>Netherlands</LOCATION>`;
   `<TIMEDATE>this</TIMEDATE> <TIMEDATE>week</TIMEDATE>'s`;
   `<AMOUNT>$</AMOUNT><AMOUNT>10 million</AMOUNT>`.
3. **The same literal string/entity labeled inconsistently across separate
   occurrences in the same sample set.** "U.S." tagged ORGANIZATION three
   times, but "United States" (same country, spelled out) tagged LOCATION;
   "CNN" tagged ORGANIZATION in 10 of 11 occurrences but LOCATION once;
   "Al-Shabaab" tagged as a full, correct ORGANIZATION span once but with
   its leading "Al" trimmed off in another occurrence.
4. **Boundary truncation cutting off the leading part of a target span at
   a subword/stem break.** `cardiol<JOB>ogist</JOB>` (only "ogist" tagged,
   "cardiol" left untagged); `Al<ORGANIZATION>-Shabaab</ORGANIZATION>`
   (leading "Al" excluded).
5. **Bare numeric tokens over-tagged as PRODUCT from superficial
   digit-pattern context**, not real product references.
   `.<PRODUCT>38</PRODUCT> caliber revolver` — a caliber number, not a
   product.
6. **Generic institutional-sounding common-noun phrases over-tagged as
   ORGANIZATION.** `<ORGANIZATION>federal</ORGANIZATION> grand jury` (a
   generic legal-process phrase, not a named institution);
   `<ORGANIZATION>University of Kentucky basketball</ORGANIZATION>` (span
   over-extended to include "basketball").
7. **Neighborhood/place names misclassified as ORGANIZATION instead of
   LOCATION.** `<ORGANIZATION>Victoria Island</ORGANIZATION>` — a named
   neighborhood in Lagos, not an institution.
8. **Brand/company names shaped like personal names misclassified as
   PERSON instead of ORGANIZATION.** `<PERSON>Hugo Boss</PERSON>` — a
   clothing brand, not an individual.
9. **Alphanumeric vehicle/equipment model designators mislabeled as
   ORGANIZATION (rather than PRODUCT) with a boundary split at the
   trailing suffix.** `<ORGANIZATION>U.S. RC-135</ORGANIZATION>U` — the
   aircraft type designator "RC-135U" is split, with "U" left outside the
   span and the whole span mislabeled ORGANIZATION rather than PRODUCT.
10. **Near-total recall failure on WORKOFART/PRODUCT on wild data**,
    consistent with their weak Stage 2 training coverage (test F1 0.16 and
    0.00 respectively). Media/show titles get partially absorbed into
    ORGANIZATION rather than recognized as WORKOFART, e.g.
    `"<WORKOFART>State of</WORKOFART> <ORGANIZATION>the Union</ORGANIZATION>"`
    — the TV show title is split, with half wrongly tagged ORGANIZATION.

---

## Stage 4 — Diagnose, Relabel, Retrain

**Model produced:** https://huggingface.co/ramiz0/ner-stage4-diagnose-relabel-retrain-model
**Dataset used:** https://huggingface.co/datasets/ramiz0/ner-stage4-diagnose-relabel-retrain (773 train / 194 test, no validation split)
**Scripts:** `stage4_diagnose_relabel_retrain/`

### Diagnosis of the 10 Stage 3 wild-QA patterns

Each of Stage 3's 10 documented problem patterns was diagnosed
individually before any fix was implemented. Summary of the diagnosis
(full reasoning and options considered are in the project's private
decision log):

| # | Pattern | Diagnosis | Fix |
|---|---|---|---|
| 1 | Subword fragmentation on unfamiliar proper nouns | Data-coverage gap | Targeted rare/non-Western proper-noun sourcing + modest epoch increase |
| 2 | Adjacent same-type spans not merging | Data-coverage gap + a decodable inference-time pattern | Multi-word span training examples + adjacent-merge postprocess |
| 3 | Same string labeled inconsistently across occurrences | Data-coverage gap (model confidence, not gold-label inconsistency) | Templated consistency-reinforcement examples (U.S./United States, CNN) |
| 4 | Boundary truncation at subword/stem breaks | Data-coverage gap (confirmed no code bug in the label-alignment logic) | Broader JOB role-noun vocabulary |
| 5 | Bare numbers over-tagged PRODUCT | Data-coverage gap (sparse real PRODUCT signal) | General AMOUNT-context volume increase (no bespoke negative generator needed) |
| 6 | Generic common-noun phrases over-tagged ORGANIZATION | **Already covered by baseline** — not a new policy gap | Mechanical filter enforcing the existing ORGANIZATION definition (no new rule) |
| 7 | Neighborhood/place names misclassified ORGANIZATION | Data-coverage gap | Targeted neighborhood-category sourcing |
| 8 | Brand names shaped like personal names misclassified PERSON | Data-coverage gap | New `BRAND_PERSON_NAMES` gazetteer forcing ORGANIZATION |
| 9 | Alphanumeric equipment designators mislabeled ORGANIZATION | Data-coverage gap | New `PRODUCT_ALPHANUMERIC_PATTERN` regex + targeted aircraft-category sourcing |
| 10 | Near-total recall failure on WORKOFART/PRODUCT | Data-coverage gap, highest priority | Dedicated targeted sourcing effort, prioritized above the other 8 |

Patterns 2–10's diagnosis and fix selection were adopted per explicit
request ("i will accept your recommendations for these patterns" / "yes
do what is recommended") rather than independently worked through
case-by-case as pattern 1 was — flagged here per the project's
attribution norm, consistent with how Stage 3's own pattern selection was
flagged.

**No new policy rule was added in Stage 4.** The one candidate gap
(pattern 6) resolved to an existing-rule enforcement issue, not a genuine
policy gap: the baseline already defines `ORGANIZATION` as "a named
company or institution" and already excludes bare category descriptors.

### Data and hyperparameter changes

- Targeted Wikipedia/Wikinews sourcing (5,320 new raw sentences) across
  categories chosen for rare/non-Western proper nouns, neighborhoods,
  brand articles, aircraft/vehicle designators, and extra WORKOFART/
  PRODUCT volume.
- Extended JOB gazetteer (broader medical/professional role vocabulary,
  including "cardiologist").
- New `PRODUCT_ALPHANUMERIC_PATTERN` regex (e.g. "RC-135U", "F-16").
- New `BRAND_PERSON_NAMES` gazetteer (e.g. "Hugo Boss" -> ORGANIZATION).
- One new mechanical policy-correction filter: drop candidate ORGANIZATION
  spans with no capitalized token (enforces the existing baseline
  definition, not a new rule).
- 26 templated synthetic reinforcement records for multi-word span
  consistency (JOB titles, "the <Country>", relative TIMEDATE phrases,
  currency AMOUNT) and same-entity consistency ("U.S."/"United States",
  "CNN").
- 219 new records selected via the same scarcity-weighted, 200/600
  floor/ceiling balance criterion as Stage 2, combined with Stage 2's 748
  records into 967 total (773 train / 194 test).
- **PRODUCT still falls short of the 200 floor (112 total)** despite this
  dedicated sourcing effort — confirmed persistent limitation, first
  identified in Stage 2 (decision 11), now surviving a second, targeted
  attempt. Not chased further.
- 8 training epochs (up from Stage 3's 5); all other hyperparameters
  (batch size 16, learning rate 5e-5, weight decay 0.01, warmup ratio 0.1,
  max sequence length 128) unchanged.
- New inference-time postprocess: adjacent same-label predicted spans
  with no intervening punctuation are merged (pattern 2's second half).
  Reported metrics below already include this postprocess.

### Resources

| Metric | Stage 3 | Stage 4 |
|---|---|---|
| Parameters | 66,375,953 | 66,375,953 (unchanged — same architecture) |
| Model disk size | 253.9 MB | 253.9 MB |
| RSS after model load | 420.2 MB | 415.0 MB |
| RSS peak during inference | 607.0 MB | 601.5 MB |
| Inference throughput (CPU, batch size 1) | 75.6 sentences/sec | 84.4 sentences/sec |

Resources are essentially unchanged, as expected — Stage 4 reused the same
base model and architecture; the small throughput difference is
measurement noise, not a real architectural change.

### Train + test metrics (comparison vs. Stage 3)

seqeval, entity-level, with the pattern-2 merge postprocess applied:

| Label | Stage 3 test F1 | Stage 4 test F1 | Change |
|---|---|---|---|
| PERSON | 0.68 | 0.57 | **-0.11 (regression)** |
| ORGANIZATION | 0.27 | 0.40 | +0.13 |
| LOCATION | 0.61 | 0.66 | +0.05 |
| TIMEDATE | 0.67 | 0.71 | +0.04 |
| AMOUNT | 0.63 | 0.62 | -0.01 (flat) |
| JOB | 0.70 | 0.81 | +0.11 |
| WORKOFART | 0.16 | 0.24 | +0.08 |
| PRODUCT | 0.00 | 0.22 | +0.22 |
| **micro avg** | 0.55 | **0.59** | +0.04 |

Full per-label precision/recall in `stage4_diagnose_relabel_retrain/data/train_metrics.txt`
/ `test_metrics.txt` (regenerate via the pipeline; canonical copies live on
Hugging Face). Train micro F1 rose from 0.70 to 0.84 alongside the larger,
more diverse training set and additional epochs.

**PERSON regressed** (0.68 -> 0.57) despite no targeted change aimed at
PERSON. The most likely contributors, based on the wild-QA re-run below:
the `BRAND_PERSON_NAMES` override and the pattern-2 merge postprocess both
interact with PERSON spans (a brand name adjacent to a real person's name,
or a fragment mid-name), and can now stitch a PERSON span together with an
adjacent wrong-label fragment into one larger wrong span, which seqeval
scores as a complete miss rather than a partial one. This is an
unresolved regression, documented rather than argued away.

### Re-evaluation against the original 10 wild-QA patterns

Re-ran the identical 30 Stage 3 wild samples (not re-sourced, for a direct
comparison) through the Stage 4 model with the merge postprocess.

1. **Subword fragmentation on unfamiliar proper nouns — partially
   improved.** "Al-Shabaab" and "Obock, Djibouti" now tag cleanly (full,
   correct spans). "Netanyahu" and "Ermenegildo Zegna" still fragment.
2. **Adjacent same-type spans not merging — improved, with a new
   over-merge risk surfaced.** "Prime Minister", "the Netherlands", "this
   week" now correctly merge into single spans. But the same merge
   mechanism over-merged "$10 million from $25 million" (two distinct
   amounts) into one AMOUNT span, and — more seriously — stitched a chain
   of spurious JOB-tagged fragments across an entire clause
   ("<JOB>ogist has been charged in connection with a failed scheme to
   have another physician</JOB>") into one large, badly wrong span for
   "cardiologist". The postprocess is a net improvement overall but is a
   double-edged fix: it amplifies existing fragment errors into larger
   wrong spans exactly when the underlying model prediction was already
   bad.
3. **Same string labeled inconsistently — partially resolved, new
   sub-pattern surfaced.** Standalone "CNN" mentions ("CNN reported...")
   are now consistently ORGANIZATION. But the CNN dateline format
   "City (CNN)" now consistently tags "CNN" as LOCATION (matching the
   preceding city) — a new, different, but still consistent-within-itself
   error. "U.S." is now consistently ORGANIZATION/tagged-correctly in the
   samples reviewed, but "United States" over-extended into the following
   clause in one instance ("United States is complaining to Moscow"
   tagged as one LOCATION span).
4. **Boundary truncation at subword/stem breaks — mixed.** "Al-Shabaab"'s
   leading "Al" is now included correctly. "cardiologist" got
   dramatically worse (see pattern 2) rather than better, despite being
   added to the JOB gazetteer — the added vocabulary term didn't
   propagate into the wiki-sourced training pool in a strong enough
   pattern to fix this specific out-of-dataset case.
5. **Bare numbers over-tagged PRODUCT — fixed.** ".38 caliber" now tags
   as AMOUNT, not PRODUCT.
6. **Generic common-noun phrases over-tagged ORGANIZATION — unresolved.**
   "federal grand jury" and "University of Kentucky basketball" (span
   overextension) are unchanged from Stage 3. Confirms the pattern-6
   diagnosis was too optimistic: the mechanical training-data filter
   can't fix a model-generalization gap it doesn't have enough contrasting
   examples to correct at inference time.
7. **Neighborhood/place names misclassified ORGANIZATION — fixed.**
   "Victoria Island" now tags correctly as LOCATION.
8. **Brand names shaped like personal names — regressed.** "Hugo Boss"
   is now tagged as part of an even larger wrong PERSON span ("Hugo Boss
   and Ermen[...]"), worse than Stage 3's cleaner (if still wrong)
   single-entity error — another instance of the merge postprocess
   compounding an underlying model mistake.
9. **Alphanumeric equipment designators — fixed.** "RC-135U" now tags as
   one clean, correct PRODUCT span (previously split with the trailing
   "U" excluded and mislabeled ORGANIZATION). "SU-27" also now tags
   PRODUCT (partial — "Flanker" still excluded).
10. **WORKOFART/PRODUCT recall — substantially improved.** "State of the
    Union" and "Straight Outta Compton" now tag as complete, correct
    WORKOFART spans (previously split/absorbed into ORGANIZATION). Test
    F1 rose from 0.16 to 0.24 (WORKOFART) and 0.00 to 0.22 (PRODUCT).

**Net summary:** 4 of 10 patterns clearly fixed (5, 7, 9, 10), 3 partially
improved with a new sub-issue surfaced (1, 2, 3), 1 unresolved (6), and 2
regressed (4's cardiologist case, 8) — both regressions traced to the same
root cause: the adjacent-span merge postprocess compounding pre-existing
model fragmentation errors into larger, more completely wrong spans. This
is the clearest lesson from Stage 4: a postprocessing fix that helps the
common case (genuine multi-word entities) can actively hurt the case where
the underlying model prediction is already unreliable, and both effects
show up in the same 30-sample wild QA set.
