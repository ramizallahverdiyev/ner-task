"""Push the Stage 1 corrected dataset and its dataset card to Hugging Face.

Requires HF_TOKEN in the environment with write access.
"""
import os

from huggingface_hub import HfApi

REPO_ID = "ramiz0/ner-stage1-rulecraft-cleanup"
HERE = os.path.dirname(__file__)

api = HfApi(token=os.environ["HF_TOKEN"])
api.create_repo(repo_id=REPO_ID, repo_type="dataset", private=False, exist_ok=True)

api.upload_file(
    path_or_fileobj=os.path.join(HERE, "dataset_card.md"),
    path_in_repo="README.md",
    repo_id=REPO_ID,
    repo_type="dataset",
)
api.upload_file(
    path_or_fileobj=os.path.join(HERE, "data", "train.jsonl"),
    path_in_repo="data/train.jsonl",
    repo_id=REPO_ID,
    repo_type="dataset",
)

print(f"Pushed to https://huggingface.co/datasets/{REPO_ID}")
