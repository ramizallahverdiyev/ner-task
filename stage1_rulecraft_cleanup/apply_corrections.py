"""Apply the Stage 1 annotation policy to the starter dataset.

Reads data/starter100.json (from fetch_starter.py), applies baseline-rule
corrections and the 14 added policy rules documented in dataset_card.md,
removes 2 records (spam/gibberish text), and writes:
  - data/starter100_corrected.json
  - data/train.jsonl
  - data/stage1_stats.txt
"""
import copy
import json
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
IN_PATH = os.path.join(DATA_DIR, "starter100.json")
OUT_JSON_PATH = os.path.join(DATA_DIR, "starter100_corrected.json")
OUT_JSONL_PATH = os.path.join(DATA_DIR, "train.jsonl")
STATS_PATH = os.path.join(DATA_DIR, "stage1_stats.txt")

with open(IN_PATH, encoding="utf-8") as f:
    rows = json.load(f)

by_idx = {r["unique_index"]: r for r in rows}


def ents(idx):
    return by_idx[idx]["privacy_mask"]


def text(idx):
    return by_idx[idx]["source_text"]


def remove(idx, start, end, label=None):
    e = ents(idx)
    before = len(e)
    e[:] = [
        x
        for x in e
        if not (x["start"] == start and x["end"] == end and (label is None or x["label"] == label))
    ]
    assert len(e) == before - 1, f"remove failed idx={idx} start={start} end={end} label={label}"


def relabel(idx, start, end, new_label):
    found = False
    for x in ents(idx):
        if x["start"] == start and x["end"] == end:
            x["label"] = new_label
            found = True
    assert found, f"relabel failed idx={idx} start={start} end={end}"


def respan(idx, old_start, old_end, new_start, new_end, new_label=None):
    t = text(idx)
    found = False
    for x in ents(idx):
        if x["start"] == old_start and x["end"] == old_end:
            x["start"] = new_start
            x["end"] = new_end
            x["value"] = t[new_start:new_end]
            if new_label:
                x["label"] = new_label
            found = True
    assert found, f"respan failed idx={idx} old=({old_start},{old_end})"


def merge(idx, spans, label):
    """Merge several (start,end) spans into one span covering min..max."""
    t = text(idx)
    starts = [s for s, e in spans]
    ends = [e for s, e in spans]
    new_start, new_end = min(starts), max(ends)
    e = ents(idx)
    before = len(e)
    e[:] = [x for x in e if (x["start"], x["end"]) not in spans]
    assert len(e) == before - len(spans), f"merge remove failed idx={idx} spans={spans}"
    e.append({"start": new_start, "end": new_end, "label": label, "value": t[new_start:new_end]})


def add(idx, label, needle, occurrence=0):
    t = text(idx)
    start = -1
    for _ in range(occurrence + 1):
        start = t.find(needle, start + 1)
        assert start != -1, f"add: needle not found idx={idx} needle={needle!r}"
    end = start + len(needle)
    ents(idx).append({"start": start, "end": end, "label": label, "value": t[start:end]})


before_snapshot = copy.deepcopy(by_idx)
changed = set()


def mark(idx):
    changed.add(idx)


# ============================================================
# Rule 1 -- vague TIMEDATE removal (no resolvable time value)
# ============================================================
r1 = [
    (0, 63, 69), (7, 42, 47), (7, 153, 164), (9, 399, 411), (9, 533, 536),
    (9, 1085, 1088), (10, 413, 417), (10, 1264, 1269), (10, 1274, 1280),
    (58, 662, 671), (58, 932, 940), (58, 1169, 1175), (67, 667, 670),
    (67, 978, 983), (68, 407, 413), (68, 907, 916), (68, 1317, 1324),
    (68, 1385, 1398), (69, 171, 174), (69, 202, 212), (69, 671, 676),
    (70, 667, 673), (71, 284, 288), (72, 225, 228), (76, 1269, 1272),
    (79, 1049, 1053), (84, 106, 112), (84, 261, 267), (87, 905, 927),
    (95, 102, 108),
]
for idx, s, e in r1:
    remove(idx, s, e, "TIMEDATE")
    mark(idx)

# event/activity words mistagged as TIMEDATE (not time expressions at all)
for idx, s, e in [(57, 273, 289), (78, 1423, 1428), (74, 213, 235), (86, 192, 206)]:
    remove(idx, s, e, "TIMEDATE")
    mark(idx)

# ============================================================
# Rule 3 -- JOB context-functional scope: remove demographic/statistical
# subjects, abstract policy-language, and department/team/sector nouns
# ============================================================
r3_remove = [
    (84, 965, 976, "JOB"), (84, 1167, 1178, "JOB"),
    (58, 720, 728, "JOB"),
    (66, 74, 98, "JOB"), (66, 250, 264, "JOB"),
    (77, 221, 250, "JOB"),
    (64, 123, 143, "JOB"),
    (89, 154, 166, "JOB"),
    (98, 85, 100, "JOB"),
    (81, 781, 794, "JOB"), (81, 1035, 1048, "JOB"),
    (68, 293, 308, "JOB"),
    (80, 838, 846, "JOB"), (80, 1475, 1483, "JOB"), (80, 1601, 1609, "JOB"),
]
for idx, s, e, lbl in r3_remove:
    remove(idx, s, e, lbl)
    mark(idx)

# ============================================================
# Rule 4 -- AMOUNT magnitude test: remove non-quantities (flat errors)
# ============================================================
for idx, s, e in [(43, 5, 12), (43, 13, 54), (44, 47, 53), (77, 0, 7), (95, 37, 43)]:
    remove(idx, s, e, "AMOUNT")
    mark(idx)

# ============================================================
# Rule 7 -- countries/kingdoms are LOCATION
# ============================================================
relabel(40, 19, 32, "LOCATION")
mark(40)

# ============================================================
# Rule 8 -- age expressions are AMOUNT (new spans)
# ============================================================
add(45, "AMOUNT", "19-year-old")
mark(45)
add(95, "AMOUNT", "98 years old")
mark(95)
add(76, "AMOUNT", "34-year-old")
mark(76)

# ============================================================
# Rule 9 -- league/competition names are ORGANIZATION (new span)
# ============================================================
add(44, "ORGANIZATION", "La Liga")
mark(44)

# ============================================================
# Rule 10 -- fix stray/invalid COMPANY label
# ============================================================
relabel(16, 2, 33, "PRODUCT")          # "Guided Advanced Tactical Rocket" -> same referent as GATR
mark(16)
relabel(39, 97, 112, "TIMEDATE")       # "Remembrance Day" -> named recurring observance
mark(39)
relabel(47, 37, 60, "ORGANIZATION")    # "Schamberger - O'Connell"
mark(47)
merge(48, [(5, 8), (9, 14), (15, 22)], "PERSON")  # "Dan" + "Riley" + "Sanford" -> one PERSON span
mark(48)
merge(69, [(13, 19), (20, 28)], "PERSON")  # "Ronald" + "McDonald" -> one PERSON span
mark(69)
relabel(79, 17, 21, "TIMEDATE")        # "2012" -> wine vintage year
mark(79)
merge(86, [(0, 3), (4, 11)], "PERSON")  # "Kim" + "Jong-Un" -> one PERSON span

# ============================================================
# Rule 11 -- named businesses/venues: LOCATION -> ORGANIZATION
# ============================================================
for idx, s, e in [
    (4, 208, 214),      # Sahara (casino)
    (4, 883, 891),      # chipotle (restaurant chain)
    (4, 920, 933),      # cosmopolitans (The Cosmopolitan hotel/casino)
    (65, 45, 63),       # Joyride Taco House
    (70, 24, 40),       # Black Bear Diner
    (79, 243, 250),     # Andre's (1st)
    (79, 1002, 1007),   # Yusho
    (79, 1025, 1036),   # Monte Carlo
    (79, 1037, 1044),   # Andre's (2nd)
    (82, 73, 86),       # Harmony House
    (83, 71, 94),       # Security Operations Hub
    (56, 99, 115),      # West Wing Studio
    (66, 152, 167),     # Research Center
    (64, 20, 55),       # United Emergency Response Coalition
]:
    relabel(idx, s, e, "ORGANIZATION")
    mark(idx)

# fix McDonald's LOCATION/ORGANIZATION inconsistency within #69
relabel(69, 412, 422, "ORGANIZATION")
relabel(69, 1171, 1181, "ORGANIZATION")
relabel(69, 1315, 1325, "ORGANIZATION")
remove(69, 859, 867, "LOCATION")  # bare "country."
mark(69)

# fix #42 "Inc" alone LOCATION -> remove, add proper "Prohaska Inc" ORGANIZATION
remove(42, 24, 27, "LOCATION")
add(42, "ORGANIZATION", "Prohaska Inc")
mark(42)

# fix #50 "Wal-Mart and" -> trim to "Wal-Mart", ORGANIZATION
respan(50, 25, 37, 25, 33, "ORGANIZATION")
mark(50)

# fix #33 "Andreanneboro expects" -> trim to "Andreanneboro"
respan(33, 49, 70, 49, 63)
mark(33)

# fix #25 "blizzard" + "entertainment" -> merge into one ORGANIZATION span
merge(25, [(0, 8), (9, 22)], "ORGANIZATION")
mark(25)

# fix #58 bare "Company" ORGANIZATION -> remove
remove(58, 514, 521, "ORGANIZATION")
mark(58)

# ============================================================
# Rule 12 -- award titles: confirmed already unlabeled, no action needed
# ============================================================

# ============================================================
# Rule 13 -- institutional documents/reports are WORKOFART
# ============================================================
relabel(99, 4, 36, "WORKOFART")   # Project Performance Audit Report
relabel(99, 38, 42, "WORKOFART")  # PPAR
mark(99)

# ============================================================
# Rule 14 -- legal citations require actual title text: remove bare locators
# ============================================================
remove(84, 1041, 1044, "WORKOFART")  # CFR
mark(84)
remove(61, 957, 961, "WORKOFART")    # "U.S." in "462 U.S. 352, 358"
mark(61)

# ============================================================
# Rule 15 -- usernames / transcript placeholders: already PERSON, no change
# ============================================================

# ============================================================
# Bare-category-descriptor removals found while applying the full pass
# ============================================================
remove(73, 827, 834, "PRODUCT")  # bare "product"
mark(73)
remove(79, 1281, 1285, "LOCATION")  # bare "city"
mark(79)
respan(88, 156, 162, 156, 161)  # "movie." -> trim trailing period first
remove(88, 156, 161, "WORKOFART")  # then remove bare "movie"
mark(88)

# boundary fix: "Apache Impala is" -> "Apache Impala", PRODUCT not WORKOFART
respan(21, 0, 16, 0, 13, "PRODUCT")
mark(21)

# "Cardinal Regiment" refers to a group, not one individual -> ORGANIZATION
relabel(9, 1307, 1324, "ORGANIZATION")
mark(9)

# split merged span "Central Command Center , Providence Road" into two entities
remove(64, 203, 243, "LOCATION")
add(64, "ORGANIZATION", "Central Command Center")
add(64, "LOCATION", "Providence Road")
mark(64)

# ============================================================
# Multi-word PERSON name fragment merges (baseline rule: "a multi-word name
# should be one span when it forms one real named entity")
# ============================================================
merges = [
    (1, [(0, 5), (6, 14)]),                              # Manny Pacquiao
    (1, [(21, 26), (27, 37)]),                            # Floyd Mayweather
    (5, [(488, 492), (493, 499)]),                        # Adam Levine (2nd occurrence)
    (44, [(21, 26), (27, 36)]),                           # Willy Caballero
    (45, [(47, 53), (54, 59)]),                           # M'Baye Niang
    (57, [(173, 178), (179, 184), (185, 193)]),           # David James Thompson
    (64, [(80, 87), (88, 96)]),                           # Michael Thompson
    (66, [(278, 284), (285, 293)]),                       # Amanda Martinez
    (71, [(127, 134), (135, 143)]),                       # Kouassi Bafounga
    (72, [(26, 31), (32, 38)]),                           # David Wilson
    (73, [(1102, 1110), (1112, 1118), (1120, 1126)]),     # Norville "Shaggy" Rogers
    (76, [(172, 178), (179, 186)]),                       # Jeremy Abelson
    (76, [(1165, 1173), (1174, 1181)]),                   # Kimberly Schmitz
    (76, [(1281, 1286), (1287, 1291)]),                   # Bobby Kern
    (77, [(196, 202), (203, 211)]),                       # Robert Williams
    (82, [(4, 11), (12, 17), (18, 26)]),                  # Michael James Thompson
    (83, [(5, 11), (12, 17)]),                            # Robert Walsh
    (88, [(594, 598), (599, 603)]),                       # Cait Sith (1st)
    (88, [(810, 814), (815, 819)]),                       # Cait Sith (2nd)
    (98, [(0, 7), (8, 14)]),                              # Hermina Wisoky
    (26, [(0, 5), (6, 17)]),                              # Suvir Mirchandani
    (60, [(126, 132), (133, 140)]),                       # Robson Dourado
]
for idx, spans in merges:
    merge(idx, spans, "PERSON")
    mark(idx)

# ============================================================
# Record removal: #59, #92 are spam/gibberish text where tagged entities sit
# inside meaningless generated word-salad, not real language.
# ============================================================
removed_records = [59, 92]
for idx in removed_records:
    del by_idx[idx]

# ============================================================
# write outputs
# ============================================================
corrected = [by_idx[i] for i in sorted(by_idx)]
for r in corrected:
    r["privacy_mask"].sort(key=lambda x: x["start"])

os.makedirs(DATA_DIR, exist_ok=True)

with open(OUT_JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(corrected, f, indent=2, ensure_ascii=False)

with open(OUT_JSONL_PATH, "w", encoding="utf-8") as f:
    for r in corrected:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")


def label_counts(snapshot):
    c = {}
    for idx, r in snapshot.items():
        for e in r["privacy_mask"]:
            c[e["label"]] = c.get(e["label"], 0) + 1
    return c


before_counts = label_counts(before_snapshot)
after_counts = label_counts(by_idx)
total_before_spans = sum(before_counts.values())
total_after_spans = sum(after_counts.values())

with open(STATS_PATH, "w", encoding="utf-8") as out:
    out.write("=== Label counts before -> after ===\n")
    all_labels = sorted(set(before_counts) | set(after_counts))
    for lbl in all_labels:
        out.write(f"  {lbl}: {before_counts.get(lbl, 0)} -> {after_counts.get(lbl, 0)}\n")
    out.write(f"TOTAL SPANS: {total_before_spans} -> {total_after_spans}\n")
    out.write(f"Records removed: {len(removed_records)} ({removed_records})\n")
    changed_kept = changed - set(removed_records)
    out.write(f"Records changed (excl. removed): {len(changed_kept)} / 100\n")
    out.write(f"Records unchanged: {100 - len(changed_kept) - len(removed_records)}\n")
    out.write(f"Final record count: {len(corrected)}\n")

print("done")
