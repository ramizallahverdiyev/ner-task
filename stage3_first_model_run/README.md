# Stage 3 — First Model Run

Fine-tunes `distilbert-base-uncased` for token classification on the Stage 2
dataset (598 train / 150 test), reports resource/throughput and train+test
metrics, and runs QA on 30 out-of-dataset "wild" sentences.

Model: https://huggingface.co/ramiz0/ner-stage3-first-model-run

## Pipeline

Run in order:

```
python fetch_dataset.py        # pulls ramiz0/ner-stage2-dataset-expansion -> data/train.jsonl, data/test.jsonl
python train.py                 # fine-tunes distilbert-base-uncased -> model/, data/train_metrics.txt, data/test_metrics.txt
python measure_resources.py     # params/disk size/CPU RAM/throughput -> data/resource_report.json
python fetch_wild_samples.py    # pulls 30 out-of-dataset sentences from CNN/DailyMail -> data/wild_samples.json
python wild_qa.py               # tags wild samples with the trained model -> data/wild_qa_predictions.json, .txt
python push_to_hub.py           # publishes model/ + model_card.md to the HF repo above (requires HF_TOKEN)
```

## Files

- `labels.py` — shared 17-label BIO schema for the 8 entity types.
- `fetch_dataset.py` — pulls the Stage 2 train/test jsonl.
- `train.py` — tokenizes with char-offset-aligned BIO tagging, fine-tunes,
  evaluates on train + test with seqeval, saves the model.
- `measure_resources.py` — param count, disk size, CPU RSS, single-sentence
  CPU inference throughput.
- `fetch_wild_samples.py` — pulls out-of-dataset QA sentences from a source
  distinct from Stage 1/2's (CNN/DailyMail).
- `wild_qa.py` — runs the trained model on the wild samples, outputs
  XML-tagged predictions for manual review.
- `model_card.md` — the model card pushed as `README.md` on the HF repo.
- `push_to_hub.py` — publishes the model.
- `report.md` — full write-up: setup, resources, metrics, and the 10
  documented problem patterns from wild QA.
- `data/`, `model/`, `checkpoints/` — generated outputs (gitignored;
  regenerate by running the pipeline).
