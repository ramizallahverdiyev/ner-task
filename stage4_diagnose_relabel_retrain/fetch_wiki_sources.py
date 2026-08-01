"""
Stage 4 targeted-sourcing script, extending Stage 2's fetch_wiki_sources.py
with categories chosen to close the gaps found in Stage 3's 10 wild-QA
problem patterns (see stage4_decisions.md):

  - Rare/non-Western proper nouns (pattern 1): biographical categories for
    people/places outside the Western-name-heavy mix Stage 2 already used.
  - Neighborhood/place names (pattern 7).
  - Brand articles (pattern 8, paired with the BRAND_PERSON_NAMES gazetteer
    in label_candidates.py).
  - Aircraft/vehicle model designators (pattern 9).
  - Extra WORKOFART/PRODUCT volume (pattern 10 -- the highest-priority fix).

Output: data/wiki_raw_sentences.json -- list of {source, page_title,
source_text} records, deduplicated by exact sentence text at fetch time.
"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

import spacy

UA = "ner-dataset-research-script/1.0"
OUT_PATH = os.path.join(os.path.dirname(__file__), "data", "wiki_raw_sentences.json")

WIKIPEDIA_CATEGORIES = [
    # Pattern 1: rare/non-Western proper nouns
    "Israeli politicians",
    "Somali politicians",
    "Djiboutian politicians",
    "Nigerian politicians",
    "Lebanese politicians",
    "Italian fashion designers",
    "Palestinian militant groups",
    # Pattern 7: neighborhoods/named places
    "Neighborhoods of Lagos",
    "Neighborhoods of Manhattan",
    "Districts of London",
    # Pattern 8: brand articles (paired with BRAND_PERSON_NAMES gazetteer)
    "Clothing brands",
    "Fashion accessory brands",
    # Pattern 9: aircraft/vehicle model designators
    "Military aircraft of the United States",
    "Reconnaissance aircraft",
    "Fighter aircraft",
    # Pattern 10: extra WORKOFART/PRODUCT volume
    "American television series",
    "British novels",
    "Pop albums",
    "Video games",
    "Automobiles",
]
PAGES_PER_CATEGORY = 12

WIKINEWS_CATEGORIES = [
    "Politics and conflicts",
    "Crime and law",
]
PAGES_PER_WIKINEWS_CATEGORY = 12

MIN_SENT_LEN = 40
MAX_SENT_LEN = 300


def api_get(host, params, retries=6):
    url = f"https://{host}/w/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                wait = 5 * (attempt + 1)
                print(f"  429 rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            raise


def category_members(host, category, limit):
    data = api_get(
        host,
        {
            "action": "query",
            "format": "json",
            "list": "categorymembers",
            "cmtitle": f"Category:{category}",
            "cmlimit": limit,
            "cmtype": "page",
            "cmnamespace": 0,
        },
    )
    return [m["title"] for m in data.get("query", {}).get("categorymembers", [])]


def page_extract(host, title):
    data = api_get(
        host,
        {
            "action": "query",
            "format": "json",
            "prop": "extracts",
            "explaintext": 1,
            "titles": title,
        },
    )
    pages = data.get("query", {}).get("pages", {})
    for p in pages.values():
        return p.get("extract", "")
    return ""


def split_sentences(nlp, text):
    doc = nlp(text)
    out = []
    for sent in doc.sents:
        s = sent.text.strip().replace("\n", " ")
        s = " ".join(s.split())
        if MIN_SENT_LEN <= len(s) <= MAX_SENT_LEN:
            out.append(s)
    return out


def main():
    nlp = spacy.load("en_core_web_sm", disable=["ner", "lemmatizer"])
    seen_text = set()
    records = []

    for cat in WIKIPEDIA_CATEGORIES:
        try:
            titles = category_members("en.wikipedia.org", cat, PAGES_PER_CATEGORY)
        except Exception as e:
            print(f"  category fetch failed for {cat}: {e}")
            continue
        for title in titles:
            try:
                extract = page_extract("en.wikipedia.org", title)
            except Exception as e:
                print(f"  page fetch failed for {title}: {e}")
                continue
            for sent in split_sentences(nlp, extract):
                if sent in seen_text:
                    continue
                seen_text.add(sent)
                records.append(
                    {"source": "wikipedia", "page_title": title, "source_text": sent}
                )
            time.sleep(0.5)
        print(f"wikipedia category '{cat}': {len(titles)} pages, running total {len(records)} sentences")
        time.sleep(1.0)

    for cat in WIKINEWS_CATEGORIES:
        try:
            titles = category_members("en.wikinews.org", cat, PAGES_PER_WIKINEWS_CATEGORY)
        except Exception as e:
            print(f"  wikinews category fetch failed for {cat}: {e}")
            continue
        for title in titles:
            try:
                extract = page_extract("en.wikinews.org", title)
            except Exception as e:
                print(f"  wikinews page fetch failed for {title}: {e}")
                continue
            for sent in split_sentences(nlp, extract):
                if sent in seen_text:
                    continue
                seen_text.add(sent)
                records.append(
                    {"source": "wikinews", "page_title": title, "source_text": sent}
                )
            time.sleep(0.5)
        print(f"wikinews category '{cat}': {len(titles)} pages, running total {len(records)} sentences")
        time.sleep(1.0)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print(f"Total raw sentences: {len(records)}")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
