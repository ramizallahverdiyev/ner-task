# Stage 2 — Dataset Expansion

Expands Stage 1's 98 corrected records to 748 total (650 new), sourced from
WikiANN (remapped PERSON/ORGANIZATION/LOCATION) and Wikipedia/Wikinews
(freshly labeled under the full policy), balanced, deduplicated, split, and
published to Hugging Face.

Dataset: https://huggingface.co/datasets/ramiz0/ner-stage2-dataset-expansion

## Pipeline

Run in order:

```
python fetch_wikiann.py          # pulls unimelb-nlp/wikiann (English) -> data/wikiann_raw.json
python fetch_wiki_sources.py     # pulls targeted Wikipedia/Wikinews sentences -> data/wiki_raw_sentences.json
python label_candidates.py       # first-pass labeling (spaCy + gazetteers) -> data/candidates.json
python apply_policy.py           # automated policy correction -> data/corrected_candidates.json
python balance_dedupe_split.py   # balance/dedupe/split vs Stage 1 -> data/combined_train.jsonl, data/combined_test.jsonl
python push_to_hub.py            # publishes to the HF repo above (requires HF_TOKEN)
```

## Files

- `fetch_wikiann.py` — pulls WikiANN, remaps PER/ORG/LOC tags to our schema.
- `fetch_wiki_sources.py` — pulls sentences from targeted Wikipedia
  categories (chosen for JOB/WORKOFART density) and Wikinews.
- `gazetteers.py` — JOB term list and WORKOFART/PRODUCT trigger-word
  patterns used for first-pass candidate flagging.
- `label_candidates.py` — hybrid first-pass labeler: spaCy for
  PERSON/ORGANIZATION/LOCATION/TIMEDATE/AMOUNT-adjacent/WORKOFART,
  gazetteer/pattern matching for JOB and PRODUCT.
- `apply_policy.py` — automated policy-correction pass (the
  mechanically-expressible subset of the Stage 1 rules).
- `balance_dedupe_split.py` — dedupe against Stage 1, balance every label
  into the 200-600 floor/ceiling range, stratified 80/20 train/test split.
- `dataset_card.md` — the dataset card pushed as `README.md` on the HF repo.
- `push_to_hub.py` — publishes the result.
- `data/` — generated outputs (gitignored; regenerate by running the pipeline).
