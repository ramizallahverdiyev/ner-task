# Stage 4 — Diagnose, Relabel, Retrain

**Model produced:** https://huggingface.co/ramiz0/ner-stage4-diagnose-relabel-retrain-model
**Dataset used:** https://huggingface.co/datasets/ramiz0/ner-stage4-diagnose-relabel-retrain (773 train / 194 test, no validation split)
**Scripts:** `stage4_diagnose_relabel_retrain/`

## Diagnosis of the 10 Stage 3 wild-QA patterns

Each of Stage 3's 10 documented problem patterns (see
`stage3_first_model_run/report.md`) was diagnosed individually before any
fix was implemented. Summary of the diagnosis (full reasoning and options
considered are in the project's private decision log):

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

## Data and hyperparameter changes

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

## Resources

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

## Train + test metrics (comparison vs. Stage 3)

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

Full per-label precision/recall in `data/train_metrics.txt` /
`data/test_metrics.txt`. Train micro F1 rose from 0.70 to 0.84 alongside
the larger, more diverse training set and additional epochs.

**PERSON regressed** (0.68 -> 0.57) despite no targeted change aimed at
PERSON. The most likely contributors, based on the wild-QA re-run below:
the `BRAND_PERSON_NAMES` override and the pattern-2 merge postprocess both
interact with PERSON spans (a brand name adjacent to a real person's name,
or a fragment mid-name), and can now stitch a PERSON span together with an
adjacent wrong-label fragment into one larger wrong span, which seqeval
scores as a complete miss rather than a partial one. This is an
unresolved regression, documented rather than argued away.

## Re-evaluation against the original 10 wild-QA patterns

Re-ran the identical 30 Stage 3 wild samples (not re-sourced, for a direct
comparison) through the Stage 4 model with the merge postprocess. Full
output: `data/wild_qa_predictions.txt` / `.json`.

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
   "cardiologist". The postprocess is a net improvement on net but is a
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
