"""
Pulls English WikiANN (train split) via the HF datasets-server REST API,
reconstructs plain source_text from tokens, and remaps its PER/ORG/LOC
tags onto our PERSON/ORGANIZATION/LOCATION labels with character offsets.

Output: data/wikiann_raw.json -- list of {source_text, privacy_mask}
records in the same shape as the Stage 1 starter set, before any policy
correction is applied.
"""
import json
import os
import time
import urllib.request

DATASET = "unimelb-nlp/wikiann"
CONFIG = "en"
SPLIT = "train"
PAGE_SIZE = 100
NUM_ROWS = 3000  # oversample; balancing/dedupe/QA will trim down later

TAG_NAMES = ["O", "B-PER", "I-PER", "B-ORG", "I-ORG", "B-LOC", "I-LOC"]
TAG_TO_LABEL = {"PER": "PERSON", "ORG": "ORGANIZATION", "LOC": "LOCATION"}

NO_SPACE_BEFORE = set(".,;:!?)]}%'’")
NO_SPACE_AFTER = set("([{$‘")

OUT_PATH = os.path.join(os.path.dirname(__file__), "data", "wikiann_raw.json")


def fetch_page(offset, length):
    url = (
        "https://datasets-server.huggingface.co/rows"
        f"?dataset={DATASET}&config={CONFIG}&split={SPLIT}"
        f"&offset={offset}&length={length}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def detokenize_with_offsets(tokens):
    """Joins tokens into text with light punctuation-aware spacing,
    returning (text, [(tok_start, tok_end), ...]) character offsets."""
    text = ""
    spans = []
    for i, tok in enumerate(tokens):
        if i > 0:
            prev = tokens[i - 1]
            need_space = True
            if tok and tok[0] in NO_SPACE_BEFORE:
                need_space = False
            if prev and prev[-1] in NO_SPACE_AFTER:
                need_space = False
            if need_space:
                text += " "
        start = len(text)
        text += tok
        end = len(text)
        spans.append((start, end))
    return text, spans


def row_to_record(row_idx, row):
    tokens = row["tokens"]
    tags = row["ner_tags"]
    text, offsets = detokenize_with_offsets(tokens)

    entities = []
    cur_label = None
    cur_start = None
    cur_end = None

    def flush():
        nonlocal cur_label, cur_start, cur_end
        if cur_label is not None:
            value = text[cur_start:cur_end]
            entities.append(
                {
                    "start": cur_start,
                    "end": cur_end,
                    "label": TAG_TO_LABEL[cur_label],
                    "value": value,
                }
            )
        cur_label, cur_start, cur_end = None, None, None

    for (tok_start, tok_end), tag_id in zip(offsets, tags):
        tag = TAG_NAMES[tag_id]
        if tag == "O":
            flush()
            continue
        bio, ent_type = tag.split("-")
        if bio == "B" or ent_type != cur_label:
            flush()
            cur_label, cur_start, cur_end = ent_type, tok_start, tok_end
        else:  # "I" continuing the same entity
            cur_end = tok_end
    flush()

    if not entities:
        return None

    return {
        "source": "wikiann",
        "wikiann_row_idx": row_idx,
        "source_text": text,
        "privacy_mask": entities,
    }


def main():
    records = []
    offset = 0
    while offset < NUM_ROWS:
        length = min(PAGE_SIZE, NUM_ROWS - offset)
        data = fetch_page(offset, length)
        for row in data["rows"]:
            rec = row_to_record(row["row_idx"], row["row"])
            if rec is not None:
                records.append(rec)
        offset += length
        time.sleep(0.1)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print(f"Fetched {offset} WikiANN rows, {len(records)} with at least one entity")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
