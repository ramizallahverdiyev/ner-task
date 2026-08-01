# Stage 4 — Diagnose, Relabel, Retrain

Diagnoses the 10 concrete problem patterns found in Stage 3's out-of-dataset
wild QA, fixes data/policy/hyperparameters accordingly, retrains
`distilbert-base-uncased` on the expanded dataset, and re-evaluates against
the original 10 patterns.

Dataset: https://huggingface.co/datasets/ramiz0/ner-stage4-diagnose-relabel-retrain
Model: https://huggingface.co/ramiz0/ner-stage4-diagnose-relabel-retrain-model

## Pipeline

Run in order:

```
python fetch_wiki_sources.py       # targeted Wikipedia/Wikinews sourcing -> data/wiki_raw_sentences.json
python label_candidates.py         # spaCy + gazetteer/pattern candidates -> data/candidates.json
python apply_policy.py             # mechanical policy correction -> data/corrected_candidates.json
python synthetic_reinforcement.py  # templated pattern 2/3 examples -> data/synthetic_records.json
python merge_and_split.py          # combine with Stage 2, dedupe, balance-select, split -> data/train.jsonl, data/test.jsonl
python train.py                    # fine-tunes distilbert-base-uncased (8 epochs) -> model/, data/train_metrics.txt, data/test_metrics.txt
python measure_resources.py        # params/disk size/CPU RAM/throughput -> data/resource_report.json
python wild_qa.py                  # re-runs Stage 3's 30 wild samples with the merge postprocess -> data/wild_qa_predictions.json, .txt
python push_to_hub.py              # publishes dataset + model (requires HF_TOKEN)
```

## Files

- `gazetteers.py` — extended JOB/PRODUCT/WORKOFART gazetteers and patterns
  (broader role vocabulary, alphanumeric equipment designators, brand names
  shaped like personal names).
- `fetch_wiki_sources.py` — targeted Wikipedia/Wikinews categories closing
  the 10 diagnosed gaps.
- `label_candidates.py` — hybrid spaCy + gazetteer/pattern candidate
  labeling, same mechanism as Stage 2, extended with two new matchers.
- `apply_policy.py` — Stage 1/2's mechanical policy corrections, plus one
  filter enforcing the existing ORGANIZATION definition (no new rule).
- `synthetic_reinforcement.py` — templated reinforcement examples for
  multi-word span consistency and same-entity labeling consistency.
- `merge_and_split.py` — combines with Stage 2's dataset, dedupes, applies
  the same 200/600 floor/ceiling balance criterion, splits new records.
- `postprocess.py` — merges adjacent same-label predicted spans with no
  intervening punctuation (pattern 2 fix), used at eval and inference time.
- `labels.py` — shared 17-label BIO schema.
- `train.py` — retrains with 8 epochs (up from Stage 3's 5), reports
  metrics computed on merge-postprocessed predictions.
- `measure_resources.py` — param count, disk size, CPU RSS, throughput.
- `wild_qa.py` — re-runs Stage 3's 30 wild samples for direct comparison.
- `dataset_card.md` / `model_card.md` — cards pushed as HF repo READMEs.
- `push_to_hub.py` — publishes dataset + model.
- `report.md` — full write-up: diagnosis of the 10 patterns, fixes applied,
  metrics comparison vs. Stage 3, and re-evaluation of the original 10
  patterns (improved/regressed/unresolved).
- `data/`, `model/`, `checkpoints/` — generated outputs (gitignored;
  regenerate by running the pipeline).
