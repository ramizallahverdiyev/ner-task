# Stage 3 — First Model Run

**Model produced:** https://huggingface.co/ramiz0/ner-stage3-first-model-run
**Dataset used:** https://huggingface.co/datasets/ramiz0/ner-stage2-dataset-expansion (598 train / 150 test, no validation split)
**Scripts:** `stage3_first_model_run/`

## Model and training setup

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

## Resources

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

## Train + test metrics

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

## Wild QA (out-of-dataset samples)

**Sample sourcing:** 30 sentences pulled from the CNN/DailyMail news
dataset (`abisee/cnn_dailymail`), a source distinct from all of Stage 1/2's
sourcing (starter set, WikiANN, Wikipedia, Wikinews). The selection
mechanism — evenly-spaced article sampling across the test split, then
within each article keeping sentences of 6-40 words containing at least one
capitalized token, capped at 2 per article — was Claude's choice, per
explicit instruction to pull from a different public source and flag the
selection mechanism as such rather than attribute it to the user's own
judgment. Full predictions: `data/wild_qa_predictions.txt` /
`data/wild_qa_predictions.json`.

**The 10 problem patterns below were also selected by Claude, per explicit
user instruction** ("select yourself, flag as my call") rather than
originated from the user's own analysis — flagged here per the project's
stated norm that judgment calls should be attributed accurately.

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
