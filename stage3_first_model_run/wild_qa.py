"""Run the trained Stage 3 model on the wild QA samples and print predictions
as XML-tagged text for manual review. This script only surfaces raw model
output -- identifying the 10 concrete problem patterns from these results is
a manual analysis step, not automated here.
"""
import json
import os

import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer

HERE = os.path.dirname(__file__)
MODEL_DIR = os.path.join(HERE, "model")
DATA_DIR = os.path.join(HERE, "data")


def tag_text(text, tokenizer, model):
    enc = tokenizer(text, return_tensors="pt", return_offsets_mapping=True, truncation=True, max_length=128)
    offsets = enc.pop("offset_mapping")[0].tolist()
    with torch.no_grad():
        logits = model(**enc).logits[0]
    pred_ids = logits.argmax(-1).tolist()
    id2label = model.config.id2label

    spans = []
    current = None
    for (tok_s, tok_e), pid in zip(offsets, pred_ids):
        if tok_s == tok_e:
            continue
        label = id2label[pid]
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

    spans.sort(key=lambda s: s["start"])
    out = []
    cursor = 0
    for s in spans:
        out.append(text[cursor:s["start"]])
        out.append(f"<{s['label']}>{text[s['start']:s['end']]}</{s['label']}>")
        cursor = s["end"]
    out.append(text[cursor:])
    return "".join(out), spans


def main():
    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
    model = AutoModelForTokenClassification.from_pretrained(MODEL_DIR)
    model.eval()

    with open(os.path.join(DATA_DIR, "wild_samples.json"), encoding="utf-8") as f:
        samples = json.load(f)

    results = []
    lines = []
    for i, sample in enumerate(samples):
        tagged, spans = tag_text(sample["source_text"], tokenizer, model)
        results.append({"source_text": sample["source_text"], "tagged": tagged, "predicted_spans": spans})
        lines.append(f"[{i}] {tagged}")

    out_json = os.path.join(DATA_DIR, "wild_qa_predictions.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    out_txt = os.path.join(DATA_DIR, "wild_qa_predictions.txt")
    with open(out_txt, "w", encoding="utf-8") as f:
        f.write("\n\n".join(lines))

    print("\n\n".join(lines))
    print(f"\nWrote {out_json} and {out_txt}")


if __name__ == "__main__":
    main()
