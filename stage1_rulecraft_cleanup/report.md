# Stage 1 — Rulecraft and Cleanup

**Dataset produced:** https://huggingface.co/datasets/ramiz0/ner-stage1-rulecraft-cleanup
**Source dataset:** https://huggingface.co/datasets/polygraf-ai/applied-nlp-ner-candidate-starter-100
**Scripts:** `stage1_rulecraft_cleanup/`

## Approach

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

## Issues and patterns found

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

## Policy: added rules

Five is stated as a good minimum; 14 were added, each closing a specific,
dataset-grounded gap and checked against the baseline and every other added
rule for contradictions. Full text with examples is in the dataset card and
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

## Second-pass findings

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

## Record removal

Two records (of the original 100) were removed: one is a drug-advertisement
post that degrades partway through into unrelated random words (a known spam
pattern — word-salad appended to evade filters), and one is an entirely
auto-generated nonsense essay (Markov-chain-style text with no real meaning).
In both, the tagged entities are real-looking words sitting inside text that
doesn't actually say anything — keeping them would train the model to extract
entities from noise rather than from context. All other records were kept and
corrected in place.

## Statistics

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

## Representative before/after examples

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
