"""
Builds first-pass label candidates for Stage 4's newly-fetched raw
sentences (data/wiki_raw_sentences.json), using the same hybrid mechanism
as Stage 2 (spaCy for PERSON/ORGANIZATION/LOCATION/TIMEDATE/AMOUNT-adjacent
categories, gazetteer/pattern matching for JOB/WORKOFART/PRODUCT), extended
with two Stage 4-specific matchers:
  - PRODUCT_ALPHANUMERIC_PATTERN (pattern 9: vehicle/aircraft designators)
  - BRAND_PERSON_NAMES (pattern 8: brand names shaped like personal names,
    force-labeled ORGANIZATION, overriding any spaCy PERSON guess)

Output: data/candidates.json -- unified list of {source, source_text,
privacy_mask} records, all pre-correction (before apply_policy.py).
"""
import json
import os
import re

import spacy

from gazetteers import (
    BRAND_PERSON_NAMES,
    JOB_TERMS,
    PRODUCT_ALPHANUMERIC_PATTERN,
    PRODUCT_TRIGGER_NOUNS,
    PRODUCT_TRIGGER_VERBS,
    WORKOFART_TRIGGER_NOUNS,
    WORKOFART_TRIGGER_VERBS,
)

HERE = os.path.dirname(__file__)
DATA_DIR = os.path.join(HERE, "data")
WIKI_SENT_PATH = os.path.join(DATA_DIR, "wiki_raw_sentences.json")
OUT_PATH = os.path.join(DATA_DIR, "candidates.json")

MARKUP_PATTERN = re.compile(r"'''|\[\[|\]\]|\{\{|\}\}")

SPACY_TO_LABEL = {
    "PERSON": "PERSON",
    "ORG": "ORGANIZATION",
    "GPE": "LOCATION",
    "LOC": "LOCATION",
    "DATE": "TIMEDATE",
    "TIME": "TIMEDATE",
    "MONEY": "AMOUNT",
    "QUANTITY": "AMOUNT",
    "CARDINAL": "AMOUNT",
    "PERCENT": "AMOUNT",
    "WORK_OF_ART": "WORKOFART",
}

JOB_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(t) for t in JOB_TERMS) + r")\b",
    re.IGNORECASE,
)

BRAND_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(b) for b in BRAND_PERSON_NAMES) + r")\b"
)


def build_trigger_patterns(noun_triggers, verb_triggers):
    all_triggers = "|".join(re.escape(t) for t in noun_triggers + verb_triggers)
    noun_only = "|".join(re.escape(t) for t in noun_triggers)
    title_case = re.compile(
        r"\b(?:" + all_triggers + r")\b\s+(?:the\s+|a\s+|an\s+)?"
        r"((?:[A-Z][\w'-]*\s*){1,8})"
    )
    quoted = re.compile(
        r"\b(?:" + noun_only + r")\b\s+(?:the\s+|a\s+|an\s+)?"
        r"(\"[^\"]{2,80}\")"
    )
    return title_case, quoted


WORKOFART_PATTERN, WORKOFART_QUOTED_PATTERN = build_trigger_patterns(
    WORKOFART_TRIGGER_NOUNS, WORKOFART_TRIGGER_VERBS
)
PRODUCT_PATTERN, PRODUCT_QUOTED_PATTERN = build_trigger_patterns(
    PRODUCT_TRIGGER_NOUNS, PRODUCT_TRIGGER_VERBS
)


def spans_overlap(a_start, a_end, b_start, b_end):
    return a_start < b_end and b_start < a_end


def dedupe_overlaps(entities):
    entities = sorted(entities, key=lambda e: (e["start"], -(e["end"] - e["start"])))
    kept = []
    for e in entities:
        if any(spans_overlap(e["start"], e["end"], k["start"], k["end"]) for k in kept):
            continue
        kept.append(e)
    return kept


def label_with_spacy(nlp, text):
    doc = nlp(text)
    out = []
    for ent in doc.ents:
        label = SPACY_TO_LABEL.get(ent.label_)
        if label is None:
            continue
        out.append(
            {
                "start": ent.start_char,
                "end": ent.end_char,
                "label": label,
                "value": text[ent.start_char : ent.end_char],
                "candidate_source": "spacy",
            }
        )
    return out


def label_jobs(text, existing):
    out = []
    for m in JOB_PATTERN.finditer(text):
        start, end = m.start(), m.end()
        if any(spans_overlap(start, end, e["start"], e["end"]) for e in existing):
            continue
        out.append(
            {
                "start": start,
                "end": end,
                "label": "JOB",
                "value": text[start:end],
                "candidate_source": "gazetteer",
            }
        )
    return out


def label_brands(text, existing):
    """Pattern 8: brand names shaped like personal names -- force-labeled
    ORGANIZATION, overriding any overlapping spaCy PERSON guess."""
    out = []
    removed_from_existing = []
    for m in BRAND_PATTERN.finditer(text):
        start, end = m.start(), m.end()
        for e in existing:
            if spans_overlap(start, end, e["start"], e["end"]):
                removed_from_existing.append(e)
        out.append(
            {
                "start": start,
                "end": end,
                "label": "ORGANIZATION",
                "value": text[start:end],
                "candidate_source": "gazetteer",
            }
        )
    for e in removed_from_existing:
        if e in existing:
            existing.remove(e)
    return out


def label_product_alphanumeric(text, existing):
    out = []
    for m in PRODUCT_ALPHANUMERIC_PATTERN.finditer(text):
        start, end = m.start(), m.end()
        if any(spans_overlap(start, end, e["start"], e["end"]) for e in existing + out):
            continue
        out.append(
            {
                "start": start,
                "end": end,
                "label": "PRODUCT",
                "value": text[start:end],
                "candidate_source": "gazetteer",
            }
        )
    return out


def _add_trigger_match(out, existing, text, start, end, label, strip_quotes=False):
    value = text[start:end].strip()
    if not value or len(value) < 2:
        return
    while value and value[-1] in " .,;:":
        value = value[:-1]
    end = start + len(value)
    if strip_quotes and value.startswith('"') and value.endswith('"'):
        start += 1
        end -= 1
        value = value[1:-1]
    if not value:
        return
    if any(spans_overlap(start, end, e["start"], e["end"]) for e in existing + out):
        return
    out.append(
        {
            "start": start,
            "end": end,
            "label": label,
            "value": text[start:end],
            "candidate_source": "gazetteer",
        }
    )


def label_by_trigger_pattern(text, existing, title_case_pattern, quoted_pattern, label):
    out = []
    for m in quoted_pattern.finditer(text):
        _add_trigger_match(out, existing, text, m.start(1), m.end(1), label, strip_quotes=True)
    for m in title_case_pattern.finditer(text):
        _add_trigger_match(out, existing, text, m.start(1), m.end(1), label)
    return out


def main():
    nlp = spacy.load("en_core_web_sm", disable=["lemmatizer"])
    records = []

    wiki_sents = json.load(open(WIKI_SENT_PATH, encoding="utf-8"))
    dropped_markup = 0
    for r in wiki_sents:
        text = r["source_text"]
        if MARKUP_PATTERN.search(text):
            dropped_markup += 1
            continue
        entities = label_with_spacy(nlp, text)
        entities += label_brands(text, entities)
        entities += label_jobs(text, entities)
        entities += label_by_trigger_pattern(
            text, entities, WORKOFART_PATTERN, WORKOFART_QUOTED_PATTERN, "WORKOFART"
        )
        entities += label_by_trigger_pattern(
            text, entities, PRODUCT_PATTERN, PRODUCT_QUOTED_PATTERN, "PRODUCT"
        )
        entities += label_product_alphanumeric(text, entities)
        entities = dedupe_overlaps(entities)
        if not entities:
            continue
        records.append(
            {
                "source": r["source"],
                "source_text": text,
                "privacy_mask": entities,
            }
        )

    print(f"Wiki sources: {len(wiki_sents)} sentences in, {dropped_markup} dropped (markup), {len(records)} labeled and kept")

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    label_counts = {}
    for r in records:
        for e in r["privacy_mask"]:
            label_counts[e["label"]] = label_counts.get(e["label"], 0) + 1
    print("Candidate span counts by label:", label_counts)
    print(f"Total candidate records: {len(records)}")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
