"""Pull out-of-dataset 'wild' QA sentences from a source distinct from Stage
2's (WikiANN/Wikipedia/Wikinews): the CNN/DailyMail news dataset.

Selection mechanism (Claude's choice, per explicit user direction to pull
from a different public source and flag the selection mechanism used):
evenly-spaced article sampling across the test split for topic diversity,
then within each sampled article keep sentences of 6-40 words that contain
at least one capitalized token (a cheap proxy for likely named entities),
capped at 2 sentences per article, until a target count is reached.
"""
import json
import os

import spacy
from datasets import load_dataset

HERE = os.path.dirname(__file__)
DATA_DIR = os.path.join(HERE, "data")
TARGET_COUNT = 30
MIN_WORDS = 6
MAX_WORDS = 40
MAX_PER_ARTICLE = 2


def has_capitalized_token(sent):
    words = sent.split()
    return any(w[0].isupper() for w in words if w and w[0].isalpha())


def main():
    nlp = spacy.load("en_core_web_sm", disable=["ner", "lemmatizer", "tagger", "parser"])
    nlp.add_pipe("sentencizer")

    ds = load_dataset("abisee/cnn_dailymail", "3.0.0", split="test")
    n = len(ds)
    stride = max(1, n // 400)  # spread candidate articles across the whole test split

    selected = []
    for i in range(0, n, stride):
        if len(selected) >= TARGET_COUNT:
            break
        article = ds[i]["article"]
        doc = nlp(article)
        picked_here = 0
        for sent in doc.sents:
            text = sent.text.strip()
            n_words = len(text.split())
            if not (MIN_WORDS <= n_words <= MAX_WORDS):
                continue
            if not has_capitalized_token(text):
                continue
            selected.append({"source_article_index": i, "source_text": text})
            picked_here += 1
            if picked_here >= MAX_PER_ARTICLE or len(selected) >= TARGET_COUNT:
                break

    out_path = os.path.join(DATA_DIR, "wild_samples.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(selected, f, indent=2)

    print(f"Selected {len(selected)} wild sentences -> {out_path}")


if __name__ == "__main__":
    main()
