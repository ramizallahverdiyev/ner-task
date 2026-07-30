# Stage 1 — Rulecraft and Cleanup

Corrects the 100-record starter dataset under an annotation policy (baseline
rules + 14 added rules for gaps the baseline left open) and publishes the
result to Hugging Face.

Dataset: https://huggingface.co/datasets/ramiz0/ner-stage1-rulecraft-cleanup

## Pipeline

Run in order:

```
python fetch_starter.py       # pulls polygraf-ai/applied-nlp-ner-candidate-starter-100 -> data/starter100.json
python apply_corrections.py   # applies the policy -> data/starter100_corrected.json, data/train.jsonl, data/stage1_stats.txt
python push_to_hub.py         # pushes data/train.jsonl + dataset_card.md to the HF repo above (requires HF_TOKEN)
```

## Files

- `fetch_starter.py` — pulls the raw starter dataset.
- `apply_corrections.py` — applies every correction: the 14 policy rules (see
  `dataset_card.md` for the full text and justification of each), the invalid
  `COMPANY`-label fix, span boundary fixes, multi-word name merges, and the
  removal of 2 spam/gibberish records.
- `dataset_card.md` — the dataset card pushed as `README.md` on the HF repo:
  Labels, Baseline rules, full policy, and corrections summary.
- `push_to_hub.py` — publishes the result.
- `data/` — generated outputs (gitignored; regenerate by running the pipeline).
