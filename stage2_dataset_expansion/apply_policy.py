"""
Applies the mechanically-expressible subset of the Stage 1 policy (baseline
+ 14 rules, see stage1_rulecraft_cleanup/dataset_card.md) to the first-pass
candidates from label_candidates.py. Rules that require reading a sentence
for semantic/contextual judgment (e.g. rule 3's role-in-action test, rule 2's
nickname-vs-generic-noun test) are not fully automatable here -- those are
covered by the manual stratified spot-check described in Stage 2 decision 7,
not by this script.

Automated corrections applied:
  - baseline: drop bare category/type words used alone (e.g. "product", "city")
  - rule 1 / rule 4: drop vague TIMEDATE / zero-magnitude AMOUNT words
  - rule 5: strip honorifics from PERSON spans (never label the honorific itself)
  - rule 8: relabel age expressions ("N-year-old") as AMOUNT
  - rule 9 / rule 10: relabel named venues/leagues mislabeled LOCATION as ORGANIZATION
  - rule 11: drop award/prize-title spans (no label fits an award name)
  - rule 3 (partial, mechanical slice only): drop JOB spans immediately
    preceded by a percentage-of-group pattern ("13.3% of ... bricklayers"),
    a clear demographic-count usage rather than a role-in-action

Output: data/corrected_candidates.json, plus data/policy_stats.txt
"""
import json
import os
import re

HERE = os.path.dirname(__file__)
DATA_DIR = os.path.join(HERE, "data")
IN_PATH = os.path.join(DATA_DIR, "candidates.json")
OUT_PATH = os.path.join(DATA_DIR, "corrected_candidates.json")
STATS_PATH = os.path.join(DATA_DIR, "policy_stats.txt")

BARE_CATEGORY_WORDS = {
    "person", "people", "company", "organization", "organisation", "team",
    "hospital", "city", "product", "book", "quantity", "place", "country",
    "government", "business", "firm", "group", "institution", "agency",
    "movie", "film", "song", "album", "show",
}

VAGUE_TIMEDATE_WORDS = {
    "now", "moment", "again", "ever", "never", "before", "always", "yet",
    "just", "already", "initially", "recent", "latest", "long", "soon",
    "currently", "today", "still", "once", "sometimes", "often",
}

ZERO_MAGNITUDE_AMOUNT_WORDS = {
    "many", "some", "a lot", "few", "several", "various", "numerous",
    "plenty", "lots",
}

HONORIFICS = [
    "Mr.", "Mrs.", "Ms.", "Miss", "Dr.", "Prof.", "Professor", "Sir",
    "Dame", "Lord", "Lady", "Cardinal", "Rev.", "Reverend", "Father",
    "Bishop", "Hon.", "Honorable", "Mx.",
]
HONORIFIC_PREFIX_RE = re.compile(
    r"^(?:" + "|".join(re.escape(h) for h in HONORIFICS) + r")\s+"
)

AGE_PATTERN = re.compile(r"^\d{1,3}[- ]year[- ]old$", re.IGNORECASE)

VENUE_KEYWORDS = [
    "Hotel", "Casino", "Restaurant", "Café", "Museum", "Theatre",
    "Theater", "Studio", "Clinic", "Stadium", "Arena", "Resort", "Club",
]
LEAGUE_KEYWORDS = ["League", "Cup", "Championship", "Open", "Series", "Tour"]

AWARD_SUFFIXES = ["Award", "Awards", "Prize", "Medal", "Trophy"]

DEMOGRAPHIC_PRECEDING_RE = re.compile(r"\d+(\.\d+)?%\s+(?:of\s+)?(?:the\s+)?[\w\s]{0,20}$")


def strip_bare_category(entities, text):
    out = []
    for e in entities:
        if e["value"].strip().lower() in BARE_CATEGORY_WORDS:
            continue
        out.append(e)
    return out


def strip_vague_timedate_amount(entities):
    out = []
    for e in entities:
        val_lower = e["value"].strip().lower()
        if e["label"] == "TIMEDATE" and val_lower in VAGUE_TIMEDATE_WORDS:
            continue
        if e["label"] == "AMOUNT" and val_lower in ZERO_MAGNITUDE_AMOUNT_WORDS:
            continue
        out.append(e)
    return out


def strip_honorifics(entities, text):
    out = []
    for e in entities:
        if e["label"] != "PERSON":
            out.append(e)
            continue
        m = HONORIFIC_PREFIX_RE.match(e["value"])
        if m:
            new_start = e["start"] + m.end()
            if new_start >= e["end"]:
                continue  # span was only the honorific itself
            e = dict(e, start=new_start, value=text[new_start : e["end"]])
        out.append(e)
    return out


def fix_age_expressions(entities):
    out = []
    for e in entities:
        if AGE_PATTERN.match(e["value"].strip()):
            e = dict(e, label="AMOUNT")
        out.append(e)
    return out


def fix_venue_league_location(entities):
    out = []
    for e in entities:
        if e["label"] == "LOCATION" and any(k in e["value"] for k in VENUE_KEYWORDS + LEAGUE_KEYWORDS):
            e = dict(e, label="ORGANIZATION")
        out.append(e)
    return out


def drop_award_titles(entities):
    out = []
    for e in entities:
        if e["label"] in ("WORKOFART", "PRODUCT") and any(
            e["value"].rstrip().endswith(suf) for suf in AWARD_SUFFIXES
        ):
            continue
        out.append(e)
    return out


def drop_demographic_jobs(entities, text):
    out = []
    for e in entities:
        if e["label"] == "JOB":
            preceding = text[: e["start"]]
            if DEMOGRAPHIC_PRECEDING_RE.search(preceding):
                continue
        out.append(e)
    return out


def validate(record):
    text = record["source_text"]
    ents = record["privacy_mask"]
    for e in ents:
        assert text[e["start"] : e["end"]] == e["value"], (record, e)
    sorted_ents = sorted(ents, key=lambda e: e["start"])
    for a, b in zip(sorted_ents, sorted_ents[1:]):
        assert a["end"] <= b["start"], (record, a, b)


def main():
    records = json.load(open(IN_PATH, encoding="utf-8"))
    before_counts = {}
    for r in records:
        for e in r["privacy_mask"]:
            before_counts[e["label"]] = before_counts.get(e["label"], 0) + 1

    out_records = []
    for r in records:
        text = r["source_text"]
        ents = r["privacy_mask"]
        ents = strip_bare_category(ents, text)
        ents = strip_vague_timedate_amount(ents)
        ents = strip_honorifics(ents, text)
        ents = fix_age_expressions(ents)
        ents = fix_venue_league_location(ents)
        ents = drop_award_titles(ents)
        ents = drop_demographic_jobs(ents, text)
        if not ents:
            continue
        ents = sorted(ents, key=lambda e: e["start"])
        new_record = {
            "source": r["source"],
            "source_text": text,
            "privacy_mask": ents,
        }
        validate(new_record)
        out_records.append(new_record)

    after_counts = {}
    for r in out_records:
        for e in r["privacy_mask"]:
            after_counts[e["label"]] = after_counts.get(e["label"], 0) + 1

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out_records, f, ensure_ascii=False, indent=2)

    lines = []
    lines.append(f"Records before correction: {len(records)}")
    lines.append(f"Records after correction (non-empty): {len(out_records)}")
    lines.append("")
    lines.append(f"{'Label':<15}{'Before':>10}{'After':>10}")
    for label in sorted(set(before_counts) | set(after_counts)):
        lines.append(f"{label:<15}{before_counts.get(label,0):>10}{after_counts.get(label,0):>10}")
    report = "\n".join(lines)
    print(report)
    with open(STATS_PATH, "w", encoding="utf-8") as f:
        f.write(report + "\n")


if __name__ == "__main__":
    main()
