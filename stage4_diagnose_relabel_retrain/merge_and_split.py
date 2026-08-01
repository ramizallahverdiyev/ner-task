"""
Combines Stage 2's existing combined_train.jsonl + combined_test.jsonl
(748 records) with Stage 4's new corrected candidates and synthetic
reinforcement records, dedupes (Stage 2 decision 3: exact-match +
substring) against everything already in the dataset, then greedily
selects new records using Stage 2 decision 2's same floor/ceiling balance
criterion (200/600 per label) -- most labels are already at or near the
600 ceiling, which naturally caps how much gets added and concentrates
new volume on the still-scarce labels (PRODUCT, WORKOFART, JOB, AMOUNT),
consistent with pattern 10 being the highest-priority fix. New records are
split 80/20 stratified by dominant label and appended to the existing
Stage 2 splits (the existing 748 records' train/test membership is left
untouched).

Output:
  data/stage4_selected.json
  data/train.jsonl
  data/test.jsonl
  data/stage4_stats.txt
"""
import json
import os
import random

random.seed(42)

HERE = os.path.dirname(__file__)
DATA_DIR = os.path.join(HERE, "data")
CORRECTED_PATH = os.path.join(DATA_DIR, "corrected_candidates.json")
SYNTHETIC_PATH = os.path.join(DATA_DIR, "synthetic_records.json")
STAGE2_TRAIN_PATH = os.path.join(HERE, "..", "stage2_dataset_expansion", "data", "combined_train.jsonl")
STAGE2_TEST_PATH = os.path.join(HERE, "..", "stage2_dataset_expansion", "data", "combined_test.jsonl")

FLOOR = 200
CEILING = 600

SELECTED_PATH = os.path.join(DATA_DIR, "stage4_selected.json")
TRAIN_PATH = os.path.join(DATA_DIR, "train.jsonl")
TEST_PATH = os.path.join(DATA_DIR, "test.jsonl")
STATS_PATH = os.path.join(DATA_DIR, "stage4_stats.txt")


def load_jsonl(path):
    records = []
    with open(path, encoding="utf-8") as f:
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
    kept = []
    dropped_exact = 0
    dropped_substring = 0
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


def dominant_label(record):
    counts = {}
    for e in record["privacy_mask"]:
        counts[e["label"]] = counts.get(e["label"], 0) + 1
    if not counts:
        return "NO_ENTITY"
    return max(counts, key=counts.get)


def main():
    stage2_train = load_jsonl(STAGE2_TRAIN_PATH)
    stage2_test = load_jsonl(STAGE2_TEST_PATH)
    stage2_combined = stage2_train + stage2_test
    stage2_counts = label_counts(stage2_combined)
    existing_texts = {r["source_text"] for r in stage2_combined}

    candidates = json.load(open(CORRECTED_PATH, encoding="utf-8"))
    synthetic = json.load(open(SYNTHETIC_PATH, encoding="utf-8"))
    pool = candidates + synthetic
    pool, dropped_exact, dropped_substring = dedupe(pool, existing_texts)

    pool_counts = label_counts(pool)
    print("Pool label counts after dedupe:", pool_counts)
    print(f"Dedupe dropped: {dropped_exact} exact, {dropped_substring} substring")

    def scarcity_score(record):
        labels_in_record = {e["label"] for e in record["privacy_mask"]}
        return sum(1.0 / pool_counts.get(lbl, 1) for lbl in labels_in_record)

    running_counts = dict(stage2_counts)
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

    # Synthetic records always kept (small, deliberately targeted at
    # patterns 2/3) -- add first so they aren't crowded out by ceiling.
    synthetic_texts = {r["source_text"] for r in synthetic}
    pool.sort(key=lambda r: (r["source_text"] not in synthetic_texts, -scarcity_score(r)))
    for r in pool:
        try_add(r)

    with open(SELECTED_PATH, "w", encoding="utf-8") as f:
        json.dump(selected, f, ensure_ascii=False, indent=2)

    buckets = {}
    for r in selected:
        buckets.setdefault(dominant_label(r), []).append(r)

    new_train, new_test = [], []
    for label, recs in buckets.items():
        recs = list(recs)
        random.shuffle(recs)
        split_idx = round(len(recs) * 0.8)
        new_train.extend(recs[:split_idx])
        new_test.extend(recs[split_idx:])

    train = stage2_train + new_train
    test = stage2_test + new_test
    random.shuffle(train)
    random.shuffle(test)

    with open(TRAIN_PATH, "w", encoding="utf-8") as f:
        for r in train:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(TEST_PATH, "w", encoding="utf-8") as f:
        for r in test:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    combined = train + test
    final_counts = label_counts(combined)

    lines = []
    lines.append(f"Stage 1+2 records: {len(stage2_combined)}")
    lines.append(f"Candidate+synthetic pool after dedupe: {len(pool)} (dropped {dropped_exact} exact, {dropped_substring} substring)")
    lines.append(f"Stage 4 records selected: {len(selected)}")
    lines.append(f"Combined total records: {len(combined)}")
    lines.append(f"Train: {len(train)}  Test: {len(test)}  ({len(train)/len(combined):.1%} / {len(test)/len(combined):.1%})")
    lines.append("")
    lines.append(f"{'Label':<15}{'Stage1+2':>10}{'Final':>10}{'Floor':>8}{'Ceiling':>9}{'OK?':>6}")
    for label in sorted(final_counts):
        s2 = stage2_counts.get(label, 0)
        fin = final_counts.get(label, 0)
        ok = "yes" if FLOOR <= fin <= CEILING else "NO"
        lines.append(f"{label:<15}{s2:>10}{fin:>10}{FLOOR:>8}{CEILING:>9}{ok:>6}")
    report = "\n".join(lines)
    print(report)
    with open(STATS_PATH, "w", encoding="utf-8") as f:
        f.write(report + "\n")


if __name__ == "__main__":
    main()
