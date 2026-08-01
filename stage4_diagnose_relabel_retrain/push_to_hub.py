"""Push the Stage 4 dataset (train + test) and fine-tuned model, with their
cards, to Hugging Face.

Requires HF_TOKEN in the environment with write access.
"""
import os

from huggingface_hub import HfApi

DATASET_REPO_ID = "ramiz0/ner-stage4-diagnose-relabel-retrain"
MODEL_REPO_ID = "ramiz0/ner-stage4-diagnose-relabel-retrain-model"
HERE = os.path.dirname(__file__)
MODEL_DIR = os.path.join(HERE, "model")

api = HfApi(token=os.environ["HF_TOKEN"])

api.create_repo(repo_id=DATASET_REPO_ID, repo_type="dataset", private=False, exist_ok=True)
api.upload_file(
    path_or_fileobj=os.path.join(HERE, "dataset_card.md"),
    path_in_repo="README.md",
    repo_id=DATASET_REPO_ID,
    repo_type="dataset",
)
api.upload_file(
    path_or_fileobj=os.path.join(HERE, "data", "train.jsonl"),
    path_in_repo="data/train.jsonl",
    repo_id=DATASET_REPO_ID,
    repo_type="dataset",
)
api.upload_file(
    path_or_fileobj=os.path.join(HERE, "data", "test.jsonl"),
    path_in_repo="data/test.jsonl",
    repo_id=DATASET_REPO_ID,
    repo_type="dataset",
)
print(f"Pushed dataset to https://huggingface.co/datasets/{DATASET_REPO_ID}")

api.create_repo(repo_id=MODEL_REPO_ID, repo_type="model", private=False, exist_ok=True)
api.upload_folder(
    folder_path=MODEL_DIR,
    repo_id=MODEL_REPO_ID,
    repo_type="model",
)
api.upload_file(
    path_or_fileobj=os.path.join(HERE, "model_card.md"),
    path_in_repo="README.md",
    repo_id=MODEL_REPO_ID,
    repo_type="model",
)
print(f"Pushed model to https://huggingface.co/{MODEL_REPO_ID}")
