"""Pull the Stage 2 dataset (train + test) from Hugging Face."""
import os

from huggingface_hub import hf_hub_download

REPO_ID = "ramiz0/ner-stage2-dataset-expansion"
HERE = os.path.dirname(__file__)
DATA_DIR = os.path.join(HERE, "data")
os.makedirs(DATA_DIR, exist_ok=True)

for split in ("train", "test"):
    path = hf_hub_download(repo_id=REPO_ID, repo_type="dataset", filename=f"data/{split}.jsonl")
    out_path = os.path.join(DATA_DIR, f"{split}.jsonl")
    with open(path, encoding="utf-8") as src, open(out_path, "w", encoding="utf-8") as dst:
        dst.write(src.read())
    n = sum(1 for _ in open(out_path, encoding="utf-8"))
    print(f"{split}: {n} records -> {out_path}")
