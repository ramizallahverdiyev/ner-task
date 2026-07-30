"""Pull the Stage 1 starter dataset and save a local JSON snapshot.

Source: polygraf-ai/applied-nlp-ner-candidate-starter-100 (Hugging Face).
"""
import json
import os
import urllib.request

REPO_ID = "polygraf-ai/applied-nlp-ner-candidate-starter-100"
OUT_PATH = os.path.join(os.path.dirname(__file__), "data", "starter100.json")


def fetch_via_datasets_lib():
    from datasets import load_dataset

    ds = load_dataset(REPO_ID, split="train")
    return [dict(row) for row in ds]


def fetch_via_rest_api():
    url = (
        "https://datasets-server.huggingface.co/rows"
        f"?dataset={REPO_ID}&config=default&split=train&offset=0&length=100"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    return [row["row"] for row in data["rows"]]


def main():
    try:
        rows = fetch_via_datasets_lib()
    except Exception:
        rows = fetch_via_rest_api()

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(rows)} records to {OUT_PATH}")


if __name__ == "__main__":
    main()
