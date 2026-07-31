"""Fine-tune distilbert-base-uncased for token classification on the Stage 2
dataset and report train + test metrics (no validation split).
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

HERE = os.path.dirname(__file__)
DATA_DIR = os.path.join(HERE, "data")
MODEL_DIR = os.path.join(HERE, "model")
MODEL_NAME = "distilbert-base-uncased"
MAX_LENGTH = 128


def load_jsonl(path):
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))
    return records


def spans_to_bio(offsets, spans):
    """offsets: list of (start, end) char offsets per token, (0,0) for specials.
    spans: list of {start, end, label} character spans, non-overlapping.
    Returns a list of label ids, one per token.
    """
    tags = ["O"] * len(offsets)
    for span in spans:
        s, e, label = span["start"], span["end"], span["label"]
        first = True
        for i, (tok_s, tok_e) in enumerate(offsets):
            if tok_s == tok_e:
                continue  # special token
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
    enc["labels"] = labels
    enc.pop("offset_mapping")
    return Dataset.from_dict(enc)


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


def predict_labels(trainer, dataset):
    output = trainer.predict(dataset)
    predictions = np.argmax(output.predictions, axis=2)
    labels = output.label_ids
    true_predictions = [
        [ID2LABEL[p] for p, l in zip(pred, lab) if l != -100]
        for pred, lab in zip(predictions, labels)
    ]
    true_labels = [
        [ID2LABEL[l] for p, l in zip(pred, lab) if l != -100]
        for pred, lab in zip(predictions, labels)
    ]
    return true_labels, true_predictions


def main():
    train_records = load_jsonl(os.path.join(DATA_DIR, "train.jsonl"))
    test_records = load_jsonl(os.path.join(DATA_DIR, "test.jsonl"))

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForTokenClassification.from_pretrained(
        MODEL_NAME, num_labels=len(LABEL_LIST), id2label=ID2LABEL, label2id=LABEL2ID
    )

    train_ds = build_dataset(train_records, tokenizer)
    test_ds = build_dataset(test_records, tokenizer)

    collator = DataCollatorForTokenClassification(tokenizer)

    args = TrainingArguments(
        output_dir=os.path.join(HERE, "checkpoints"),
        num_train_epochs=5,
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

    train_true, train_pred = predict_labels(trainer, train_ds)
    test_true, test_pred = predict_labels(trainer, test_ds)

    train_report = seqeval_metrics.classification_report(train_true, train_pred, zero_division=0)
    test_report = seqeval_metrics.classification_report(test_true, test_pred, zero_division=0)

    with open(os.path.join(DATA_DIR, "train_metrics.txt"), "w", encoding="utf-8") as f:
        f.write(train_report)
    with open(os.path.join(DATA_DIR, "test_metrics.txt"), "w", encoding="utf-8") as f:
        f.write(test_report)

    print("=== TRAIN metrics ===")
    print(train_report)
    print("=== TEST metrics ===")
    print(test_report)


if __name__ == "__main__":
    main()
