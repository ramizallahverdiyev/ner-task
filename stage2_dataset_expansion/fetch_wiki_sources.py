"""
Pulls raw sentences from targeted Wikipedia categories (chosen to be
JOB- and WORKOFART-dense, per Stage 2 decision 8) and from Wikinews
(TIMEDATE/AMOUNT-rich news-style sentences), with no entity labels yet --
labeling happens in label_candidates.py.

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

# Categories chosen for JOB density (people described by their role/career)
# and WORKOFART density (titled creative works), per decision 8.
WIKIPEDIA_CATEGORIES = [
    "American film directors",
    "American novelists",
    "Association football managers",
    "Foreign ministers",
    "State governors of the United States",
    "American physicians",
    "Jazz musicians",
    "Television journalists",
    "Chief executives",
    "Prime ministers",
    "American novels",
    "British films",
    "Rock albums",
    "Broadway plays",
    "Painters",
    # Added for WORKOFART/PRODUCT density (Stage 2 balancing gap). The
    # gaming/tech categories originally here (Video games, Video game
    # franchises, Video game consoles, Smartphones, Consumer electronics
    # brands, Software) were dropped after the QA spot-check found spaCy's
    # small model performs very unreliably on gaming/tech proper nouns
    # (Xbox One tagged PERSON, PlayStation Store tagged PERSON/PRODUCT
    # inconsistently, etc.) -- replaced with categories in plain
    # biographical/business/brand prose, which tested clean in the sample.
    "Science fiction novels",
    "Fantasy novels",
    "Paintings",
    "Sculptures",
    "Symphonies",
    "Soft drinks",
    "Cosmetics brands",
    "Watch brands",
    "Perfumes",
]
PAGES_PER_CATEGORY = 12

WIKINEWS_CATEGORIES = [
    "Politics and conflicts",
    "Business and economy",
    "Sports",
]
PAGES_PER_WIKINEWS_CATEGORY = 15

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
        s = " ".join(s.split())  # collapse whitespace
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
