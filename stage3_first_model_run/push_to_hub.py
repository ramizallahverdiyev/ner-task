"""Push the Stage 3 fine-tuned model (+ model card) to Hugging Face.

Requires HF_TOKEN in the environment with write access.
"""
import os

from huggingface_hub import HfApi

REPO_ID = "ramiz0/ner-stage3-first-model-run"
HERE = os.path.dirname(__file__)
MODEL_DIR = os.path.join(HERE, "model")

api = HfApi(token=os.environ["HF_TOKEN"])
api.create_repo(repo_id=REPO_ID, repo_type="model", private=False, exist_ok=True)

api.upload_folder(
    folder_path=MODEL_DIR,
    repo_id=REPO_ID,
    repo_type="model",
)
api.upload_file(
    path_or_fileobj=os.path.join(HERE, "model_card.md"),
    path_in_repo="README.md",
    repo_id=REPO_ID,
    repo_type="model",
)

print(f"Pushed to https://huggingface.co/{REPO_ID}")
