"""
Templated generation of reinforcement examples for patterns 2 and 3 (see
stage4_decisions.md), mechanical instantiation of an already-decided fix
(not new content judgment): plug varied names/dates/amounts into fixed
sentence templates, label spans by template position, and validate offsets
exactly like every other Stage 4 record.

Pattern 2 (adjacent same-type spans not merging): multi-word JOB titles,
"the <Country>" LOCATION phrasing, relative TIMEDATE phrases, "$<amount>"
AMOUNT phrasing -- reinforcing that these are single spans.

Pattern 3 (same string labeled inconsistently): "U.S." / "the United
States" equivalence (both LOCATION), "CNN" consistently ORGANIZATION.

Output: data/synthetic_records.json
"""
import json
import os

HERE = os.path.dirname(__file__)
DATA_DIR = os.path.join(HERE, "data")
OUT_PATH = os.path.join(DATA_DIR, "synthetic_records.json")

PEOPLE = ["Maria Fernandez", "James Whitfield", "Aisha Kone", "David Park", "Elena Rossi"]
JOB_TITLES = [
    "Prime Minister", "Vice President", "Chief Executive Officer",
    "Secretary of State", "Deputy Governor", "Attorney General",
]
COUNTRIES = ["Netherlands", "Philippines", "Bahamas", "United Kingdom", "Gambia"]
TIME_PHRASES = ["this week", "last month", "next year", "this quarter"]
AMOUNTS = ["10 million", "2.5 billion", "750,000", "3.2 trillion"]
NEWS_ORGS = ["CNN", "Reuters", "the BBC", "the Associated Press"]

records = []


def add(text, spans):
    for s in spans:
        assert text[s["start"]:s["end"]] == s["value"], (text, s)
    records.append({"source": "synthetic", "source_text": text, "privacy_mask": spans})


for person, title in zip(PEOPLE, JOB_TITLES):
    text = f"{person} was sworn in as {title} on Monday."
    t_start = text.index(title)
    p_start = text.index(person)
    add(text, [
        {"start": p_start, "end": p_start + len(person), "label": "PERSON", "value": person},
        {"start": t_start, "end": t_start + len(title), "label": "JOB", "value": title},
    ])

for country in COUNTRIES:
    phrase = f"the {country}"
    text = f"The treaty was signed by representatives from {phrase} last year."
    start = text.index(phrase)
    add(text, [{"start": start, "end": start + len(phrase), "label": "LOCATION", "value": phrase}])

for tphrase in TIME_PHRASES:
    text = f"The company announced its new policy {tphrase}."
    start = text.index(tphrase)
    add(text, [{"start": start, "end": start + len(tphrase), "label": "TIMEDATE", "value": tphrase}])

for amount in AMOUNTS:
    value = f"${amount}"
    text = f"The fund raised {value} in its first round."
    start = text.index(value)
    add(text, [{"start": start, "end": start + len(value), "label": "AMOUNT", "value": value}])

# Pattern 3: U.S. / United States equivalence, both LOCATION
US_TEMPLATES = [
    "The U.S. imposed new tariffs on imported steel.",
    "Officials said the U.S. would continue talks next week.",
    "The United States imposed new tariffs on imported steel.",
    "Officials said the United States would continue talks next week.",
]
for text in US_TEMPLATES:
    if "the United States" in text:
        phrase = "the United States"
    elif "United States" in text:
        phrase = "United States"
    else:
        phrase = "U.S."
    start = text.index(phrase)
    add(text, [{"start": start, "end": start + len(phrase), "label": "LOCATION", "value": phrase}])

# Pattern 3: CNN / news orgs consistently ORGANIZATION
for org in NEWS_ORGS:
    text = f"{org} reported on the story throughout the evening."
    value = org[4:] if org.startswith("the ") else org
    start = text.index(value)
    add(text, [{"start": start, "end": start + len(value), "label": "ORGANIZATION", "value": value}])

os.makedirs(DATA_DIR, exist_ok=True)
with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(records, f, ensure_ascii=False, indent=2)

print(f"Generated {len(records)} synthetic reinforcement records -> {OUT_PATH}")
