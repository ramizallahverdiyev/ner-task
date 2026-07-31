"""
Builds first-pass label candidates for every raw record, per Stage 2
decision 5 (hybrid: spaCy for PERSON/ORGANIZATION/LOCATION/TIMEDATE/
AMOUNT-adjacent categories, gazetteer/pattern matching for JOB and
WORKOFART), before any policy correction is applied.

Inputs:
  data/wikiann_raw.json         (already PERSON/ORGANIZATION/LOCATION labeled)
  data/wiki_raw_sentences.json  (unlabeled Wikipedia/Wikinews sentences)

Output:
  data/candidates.json -- unified list of {source, source_text,
  privacy_mask} records, all pre-correction. privacy_mask entries carry an
  extra "candidate_source" field (wikiann | spacy | gazetteer) so the
  correction/QA pass can trace where each span came from.
"""
import json
import os
import re

import spacy

from gazetteers import (
    JOB_TERMS,
    PRODUCT_TRIGGER_NOUNS,
    PRODUCT_TRIGGER_VERBS,
    WORKOFART_TRIGGER_NOUNS,
    WORKOFART_TRIGGER_VERBS,
)

HERE = os.path.dirname(__file__)
DATA_DIR = os.path.join(HERE, "data")
WIKIANN_PATH = os.path.join(DATA_DIR, "wikiann_raw.json")
WIKI_SENT_PATH = os.path.join(DATA_DIR, "wiki_raw_sentences.json")
OUT_PATH = os.path.join(DATA_DIR, "candidates.json")

# Wiki-markup leftovers (WikiANN is built from raw wikitext; some rows keep
# fragments like '''bold''' or [[links]]) -- records containing these are
# dropped rather than labeled, same data-hygiene standard as Stage 1.
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
    # PRODUCT deliberately not mapped from spaCy here -- QA found ~0%
    # precision (mislabeling PERSON/LOCATION/WORKOFART as PRODUCT); PRODUCT
    # uses the trigger-word pattern matcher below instead (decision 10).
}

JOB_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(t) for t in JOB_TERMS) + r")\b",
    re.IGNORECASE,
)

# A trigger word (creative-work or product related) followed by an
# optional article, then a run of Title-Case words -- the trigger word
# itself is not part of the flagged span. Quoted-string capture is
# restricted to the noun triggers only: generic verbs like "called"/
# "titled" quote all sorts of non-title phrases ("called 'chancellor'")
# and produced too many false positives when allowed to trigger a
# quoted-string capture.
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
    """Keeps longer spans when candidates overlap (simple greedy pick)."""
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

    wikiann = json.load(open(WIKIANN_PATH, encoding="utf-8"))
    dropped_markup = 0
    for r in wikiann:
        if MARKUP_PATTERN.search(r["source_text"]):
            dropped_markup += 1
            continue
        mask = [dict(e, candidate_source="wikiann") for e in r["privacy_mask"]]
        records.append(
            {"source": "wikiann", "source_text": r["source_text"], "privacy_mask": mask}
        )
    print(f"WikiANN: {len(wikiann)} loaded, {dropped_markup} dropped (wiki markup), {len(records)} kept")

    wiki_kept_start = len(records)
    wiki_sents = json.load(open(WIKI_SENT_PATH, encoding="utf-8"))
    for r in wiki_sents:
        text = r["source_text"]
        entities = label_with_spacy(nlp, text)
        entities += label_jobs(text, entities)
        entities += label_by_trigger_pattern(
            text, entities, WORKOFART_PATTERN, WORKOFART_QUOTED_PATTERN, "WORKOFART"
        )
        entities += label_by_trigger_pattern(
            text, entities, PRODUCT_PATTERN, PRODUCT_QUOTED_PATTERN, "PRODUCT"
        )
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
    print(f"Wikipedia/Wikinews: {len(wiki_sents)} sentences in, {len(records) - wiki_kept_start} labeled and kept")

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
