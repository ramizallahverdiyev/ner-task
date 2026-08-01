"""Fine-tune distilbert-base-uncased for token classification on the Stage 4
dataset and report train + test metrics (no validation split).

Changes from Stage 3's train.py (see stage4_decisions.md):
  - 8 epochs instead of 5 (pattern 1: train F1 hadn't saturated at 5).
  - Final train/test metrics are computed after decoding predictions to
    entity spans and applying postprocess.merge_adjacent_same_label
    (pattern 2), then re-encoding back to BIO tags for seqeval scoring --
    this reports the metrics of the actually-shipped inference behavior,
    not the raw un-merged model output. Per-epoch eval during training
    (compute_metrics) stays on raw token predictions, matching Stage 3,
    since it's just a training-progress signal.
"""
import json
import os

import numpy as np
import seqeval.metrics as seqeval_metrics
from datasets import Dataset
from transformers import (
    AutoModelForTokenClassification,
    AutoTokenizer,
    DataCollatorForTokenClassification,
    Trainer,
    TrainingArguments,
)

from labels import ID2LABEL, LABEL2ID, LABEL_LIST
from postprocess import merge_adjacent_same_label

HERE = os.path.dirname(__file__)
DATA_DIR = os.path.join(HERE, "data")
MODEL_DIR = os.path.join(HERE, "model")
MODEL_NAME = "distilbert-base-uncased"
MAX_LENGTH = 128
NUM_EPOCHS = 8


def load_jsonl(path):
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))
    return records


def spans_to_bio(offsets, spans):
    tags = ["O"] * len(offsets)
    for span in spans:
        s, e, label = span["start"], span["end"], span["label"]
        first = True
        for i, (tok_s, tok_e) in enumerate(offsets):
            if tok_s == tok_e:
                continue
            if tok_s >= s and tok_e <= e:
                tags[i] = f"{'B' if first else 'I'}-{label}"
                first = False
    label_ids = []
    for i, (tok_s, tok_e) in enumerate(offsets):
        if tok_s == tok_e:
            label_ids.append(-100)
        else:
            label_ids.append(LABEL2ID[tags[i]])
    return label_ids


def build_dataset(records, tokenizer):
    texts = [r["source_text"] for r in records]
    all_spans = [r["privacy_mask"] for r in records]
    enc = tokenizer(
        texts,
        truncation=True,
        max_length=MAX_LENGTH,
        return_offsets_mapping=True,
        padding=False,
    )
    labels = [
        spans_to_bio(offsets, spans)
        for offsets, spans in zip(enc["offset_mapping"], all_spans)
    ]
    offset_mapping = enc["offset_mapping"]
    enc["labels"] = labels
    enc.pop("offset_mapping")
    ds = Dataset.from_dict(enc)
    return ds, texts, offset_mapping


def compute_metrics(eval_pred):
    predictions, labels = eval_pred
    predictions = np.argmax(predictions, axis=2)
    true_predictions = [
        [ID2LABEL[p] for p, l in zip(pred, lab) if l != -100]
        for pred, lab in zip(predictions, labels)
    ]
    true_labels = [
        [ID2LABEL[l] for p, l in zip(pred, lab) if l != -100]
        for pred, lab in zip(predictions, labels)
    ]
    report = seqeval_metrics.classification_report(
        true_labels, true_predictions, output_dict=True, zero_division=0
    )
    return {
        "precision": report["micro avg"]["precision"],
        "recall": report["micro avg"]["recall"],
        "f1": report["micro avg"]["f1-score"],
    }


def decode_spans(offsets, pred_ids):
    spans = []
    current = None
    for (tok_s, tok_e), pid in zip(offsets, pred_ids):
        if tok_s == tok_e:
            continue
        label = ID2LABEL[pid]
        if label == "O":
            if current:
                spans.append(current)
                current = None
            continue
        prefix, etype = label.split("-", 1)
        if prefix == "B" or current is None or current["label"] != etype:
            if current:
                spans.append(current)
            current = {"start": tok_s, "end": tok_e, "label": etype}
        else:
            current["end"] = tok_e
    if current:
        spans.append(current)
    return spans


def spans_to_tag_sequence(offsets, spans):
    tags = ["O"] * len(offsets)
    for span in spans:
        first = True
        for i, (tok_s, tok_e) in enumerate(offsets):
            if tok_s == tok_e:
                continue
            if tok_s >= span["start"] and tok_e <= span["end"]:
                tags[i] = f"{'B' if first else 'I'}-{span['label']}"
                first = False
    return [t for t, (s, e) in zip(tags, offsets) if s != e]


def predict_labels_merged(trainer, dataset, texts, offset_mapping):
    """Decodes predictions to spans, applies the pattern-2 adjacent-merge
    postprocess, then re-encodes to BIO tags for seqeval -- reports
    metrics for the actually-shipped (merged) inference behavior."""
    output = trainer.predict(dataset)
    pred_ids_batch = np.argmax(output.predictions, axis=2)
    label_ids_batch = output.label_ids

    true_labels = []
    true_predictions = []
    for pred_ids, label_ids, text, offsets in zip(pred_ids_batch, label_ids_batch, texts, offset_mapping):
        gold_tags = [ID2LABEL[l] for l, off in zip(label_ids, offsets) if l != -100]
        raw_spans = decode_spans(offsets, pred_ids)
        merged_spans = merge_adjacent_same_label(text, raw_spans)
        pred_tags = spans_to_tag_sequence(offsets, merged_spans)
        # decode_spans/spans_to_tag_sequence both skip special tokens
        # (tok_s == tok_e), same filter as the gold side, so lengths match.
        true_labels.append(gold_tags)
        true_predictions.append(pred_tags)
    return true_labels, true_predictions


def main():
    train_records = load_jsonl(os.path.join(DATA_DIR, "train.jsonl"))
    test_records = load_jsonl(os.path.join(DATA_DIR, "test.jsonl"))

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForTokenClassification.from_pretrained(
        MODEL_NAME, num_labels=len(LABEL_LIST), id2label=ID2LABEL, label2id=LABEL2ID
    )

    train_ds, train_texts, train_offsets = build_dataset(train_records, tokenizer)
    test_ds, test_texts, test_offsets = build_dataset(test_records, tokenizer)

    collator = DataCollatorForTokenClassification(tokenizer)

    args = TrainingArguments(
        output_dir=os.path.join(HERE, "checkpoints"),
        num_train_epochs=NUM_EPOCHS,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=16,
        learning_rate=5e-5,
        weight_decay=0.01,
        warmup_ratio=0.1,
        eval_strategy="epoch",
        save_strategy="no",
        logging_strategy="epoch",
        report_to=[],
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_ds,
        eval_dataset=test_ds,
        data_collator=collator,
        compute_metrics=compute_metrics,
    )

    trainer.train()

    os.makedirs(MODEL_DIR, exist_ok=True)
    trainer.save_model(MODEL_DIR)
    tokenizer.save_pretrained(MODEL_DIR)

    train_true, train_pred = predict_labels_merged(trainer, train_ds, train_texts, train_offsets)
    test_true, test_pred = predict_labels_merged(trainer, test_ds, test_texts, test_offsets)

    train_report = seqeval_metrics.classification_report(train_true, train_pred, zero_division=0)
    test_report = seqeval_metrics.classification_report(test_true, test_pred, zero_division=0)

    with open(os.path.join(DATA_DIR, "train_metrics.txt"), "w", encoding="utf-8") as f:
        f.write(train_report)
    with open(os.path.join(DATA_DIR, "test_metrics.txt"), "w", encoding="utf-8") as f:
        f.write(test_report)

    print("=== TRAIN metrics (with pattern-2 merge postprocess) ===")
    print(train_report)
    print("=== TEST metrics (with pattern-2 merge postprocess) ===")
    print(test_report)


if __name__ == "__main__":
    main()
