"""
Dedupes the corrected Stage 2 candidates against Stage 1's 98 records and
against each other (Stage 2 decision 3: exact-match + substring), then
greedily selects new records to bring every label's TOTAL span count
(Stage 1 + Stage 2 combined) into the 200-600 floor/ceiling range (decision
2), prioritizing records containing the scarcest labels first so PRODUCT
and WORKOFART -- the two labels with the smallest candidate pools -- aren't
crowded out by abundant labels like PERSON/ORGANIZATION. Records are added
up to the ~650-new-record target (decision 6) without letting any label
exceed the ceiling. Finally splits Stage 1 + selected Stage 2 records into
a stratified 80/20 train/test split by each record's dominant (most
frequent) label (decision 4).

Output:
  data/stage2_selected.json      -- the ~650 new Stage 2 records
  data/combined_train.jsonl      -- Stage 1 + Stage 2, train split
  data/combined_test.jsonl       -- Stage 1 + Stage 2, test split
  data/stage2_stats.txt
"""
import json
import os
import random

random.seed(42)

HERE = os.path.dirname(__file__)
DATA_DIR = os.path.join(HERE, "data")
CORRECTED_PATH = os.path.join(DATA_DIR, "corrected_candidates.json")
STAGE1_PATH = os.path.join(HERE, "..", "stage1_rulecraft_cleanup", "data", "train.jsonl")

FLOOR = 200
CEILING = 600
NEW_RECORD_TARGET = 650

SELECTED_PATH = os.path.join(DATA_DIR, "stage2_selected.json")
TRAIN_PATH = os.path.join(DATA_DIR, "combined_train.jsonl")
TEST_PATH = os.path.join(DATA_DIR, "combined_test.jsonl")
STATS_PATH = os.path.join(DATA_DIR, "stage2_stats.txt")


def load_stage1():
    records = []
    with open(STAGE1_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def label_counts(records):
    counts = {}
    for r in records:
        for e in r["privacy_mask"]:
            counts[e["label"]] = counts.get(e["label"], 0) + 1
    return counts


def dedupe(records, existing_texts):
    """Exact-match + substring dedupe (decision 3). existing_texts is
    mutated in place as records are accepted."""
    kept = []
    dropped_exact = 0
    dropped_substring = 0
    # Sort longest-first so a long text is checked/added before shorter
    # texts that might be its substring.
    records = sorted(records, key=lambda r: -len(r["source_text"]))
    for r in records:
        t = r["source_text"]
        if t in existing_texts:
            dropped_exact += 1
            continue
        if any((t in other) or (other in t) for other in existing_texts):
            dropped_substring += 1
            continue
        existing_texts.add(t)
        kept.append(r)
    return kept, dropped_exact, dropped_substring


def main():
    stage1 = load_stage1()
    stage1_counts = label_counts(stage1)
    existing_texts = {r["source_text"] for r in stage1}

    candidates = json.load(open(CORRECTED_PATH, encoding="utf-8"))
    candidates, dropped_exact, dropped_substring = dedupe(candidates, existing_texts)

    pool_counts = label_counts(candidates)
    print("Pool label counts after dedupe:", pool_counts)
    print(f"Dedupe dropped: {dropped_exact} exact, {dropped_substring} substring")

    # Scarcity score: records containing labels with small candidate pools
    # (PRODUCT, WORKOFART) get selected first, so they aren't crowded out.
    def scarcity_score(record):
        labels_in_record = {e["label"] for e in record["privacy_mask"]}
        return sum(1.0 / pool_counts.get(lbl, 1) for lbl in labels_in_record)

    running_counts = dict(stage1_counts)
    selected = []

    def try_add(r):
        record_labels = [e["label"] for e in r["privacy_mask"]]
        would_exceed = any(
            running_counts.get(lbl, 0) + record_labels.count(lbl) > CEILING
            for lbl in set(record_labels)
        )
        if would_exceed:
            return False
        for lbl in record_labels:
            running_counts[lbl] = running_counts.get(lbl, 0) + 1
        selected.append(r)
        return True

    # WikiANN was explicitly chosen (decision 1) as the PERSON/ORGANIZATION/
    # LOCATION source. A pure scarcity-ranked greedy over the full pool
    # starves it out entirely: Wikipedia/Wikinews records that also carry a
    # scarce label (JOB, TIMEDATE, ...) alongside PERSON/ORG/LOCATION always
    # outrank WikiANN's PERSON/ORG/LOCATION-only records, so WikiANN would
    # contribute 0 of the ~650 selected records. Reserve a WikiANN quota
    # first so decision 1's source mix is actually honored, then fill the
    # rest by scarcity across whatever remains (including leftover WikiANN).
    WIKIANN_QUOTA = 200
    wikiann_pool = [r for r in candidates if r["source"] == "wikiann"]
    other_pool = [r for r in candidates if r["source"] != "wikiann"]
    wikiann_pool.sort(key=scarcity_score, reverse=True)
    remaining_wikiann = []
    for r in wikiann_pool:
        if len(selected) >= WIKIANN_QUOTA:
            remaining_wikiann.append(r)
            continue
        if not try_add(r):
            remaining_wikiann.append(r)

    rest_pool = remaining_wikiann + other_pool
    rest_pool.sort(key=scarcity_score, reverse=True)
    for r in rest_pool:
        if len(selected) >= NEW_RECORD_TARGET:
            break
        try_add(r)

    with open(SELECTED_PATH, "w", encoding="utf-8") as f:
        json.dump(selected, f, ensure_ascii=False, indent=2)

    combined = stage1 + selected
    final_counts = label_counts(combined)

    def dominant_label(record):
        counts = {}
        for e in record["privacy_mask"]:
            counts[e["label"]] = counts.get(e["label"], 0) + 1
        if not counts:
            return "NO_ENTITY"  # 2 pre-existing Stage 1 records with 0 spans
        return max(counts, key=counts.get)

    buckets = {}
    for r in combined:
        buckets.setdefault(dominant_label(r), []).append(r)

    train, test = [], []
    for label, recs in buckets.items():
        recs = list(recs)
        random.shuffle(recs)
        split_idx = round(len(recs) * 0.8)
        train.extend(recs[:split_idx])
        test.extend(recs[split_idx:])
    random.shuffle(train)
    random.shuffle(test)

    with open(TRAIN_PATH, "w", encoding="utf-8") as f:
        for r in train:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(TEST_PATH, "w", encoding="utf-8") as f:
        for r in test:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    lines = []
    lines.append(f"Stage 1 records: {len(stage1)}")
    lines.append(f"Candidate pool after dedupe: {len(candidates)} (dropped {dropped_exact} exact, {dropped_substring} substring)")
    lines.append(f"Stage 2 records selected: {len(selected)}")
    lines.append(f"Combined total records: {len(combined)}")
    lines.append(f"Train: {len(train)}  Test: {len(test)}  ({len(train)/len(combined):.1%} / {len(test)/len(combined):.1%})")
    lines.append("")
    lines.append(f"{'Label':<15}{'Stage1':>10}{'Final':>10}{'Floor':>8}{'Ceiling':>9}{'OK?':>6}")
    for label in sorted(final_counts):
        s1 = stage1_counts.get(label, 0)
        fin = final_counts.get(label, 0)
        ok = "yes" if FLOOR <= fin <= CEILING else "NO"
        lines.append(f"{label:<15}{s1:>10}{fin:>10}{FLOOR:>8}{CEILING:>9}{ok:>6}")
    report = "\n".join(lines)
    print(report)
    with open(STATS_PATH, "w", encoding="utf-8") as f:
        f.write(report + "\n")


if __name__ == "__main__":
    main()
