# NER Task

A 4-stage applied NER project: reviewing and correcting an annotated dataset,
expanding it, training a token-classification model, then diagnosing and
improving it based on model behavior.

## Overview

- `stage1_rulecraft_cleanup/` — annotation policy definition and dataset
  cleanup. Dataset: https://huggingface.co/datasets/ramiz0/ner-stage1-rulecraft-cleanup.
  Report: `stage1_rulecraft_cleanup/report.md`.
- `stage2_dataset_expansion/` — dataset expansion to 748 records, balanced,
  deduplicated, split. Dataset: https://huggingface.co/datasets/ramiz0/ner-stage2-dataset-expansion.
  Report: `stage2_dataset_expansion/report.md`.
- Stages 3-4: in progress.

## Setup

Each stage folder is self-contained with its own scripts, run in the order
listed in that folder's README.

## Usage

See each stage folder's README for pipeline commands.
