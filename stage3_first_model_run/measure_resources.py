"""Report model size/param count and CPU RAM/throughput for the trained
Stage 3 model, run standalone after train.py.
"""
import json
import os
import time

import psutil
import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer

HERE = os.path.dirname(__file__)
MODEL_DIR = os.path.join(HERE, "model")
DATA_DIR = os.path.join(HERE, "data")
N_WARMUP = 5
N_TIMED = 50


def dir_size_bytes(path):
    total = 0
    for root, _, files in os.walk(path):
        for name in files:
            total += os.path.getsize(os.path.join(root, name))
    return total


def main():
    torch.set_num_threads(psutil.cpu_count(logical=False) or psutil.cpu_count())

    process = psutil.Process(os.getpid())
    rss_before = process.memory_info().rss

    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
    model = AutoModelForTokenClassification.from_pretrained(MODEL_DIR)
    model.eval()

    rss_after_load = process.memory_info().rss

    num_params = sum(p.numel() for p in model.parameters())
    disk_bytes = dir_size_bytes(MODEL_DIR)

    with open(os.path.join(DATA_DIR, "test.jsonl"), encoding="utf-8") as f:
        texts = [json.loads(line)["source_text"] for line in f]
    sample_texts = (texts * ((N_WARMUP + N_TIMED) // len(texts) + 1))[: N_WARMUP + N_TIMED]

    with torch.no_grad():
        for text in sample_texts[:N_WARMUP]:
            enc = tokenizer(text, return_tensors="pt", truncation=True, max_length=128)
            model(**enc)

    rss_peak = process.memory_info().rss
    start = time.perf_counter()
    with torch.no_grad():
        for text in sample_texts[N_WARMUP:]:
            enc = tokenizer(text, return_tensors="pt", truncation=True, max_length=128)
            model(**enc)
            rss_peak = max(rss_peak, process.memory_info().rss)
    elapsed = time.perf_counter() - start

    throughput = N_TIMED / elapsed

    report = {
        "num_parameters": num_params,
        "model_disk_size_mb": round(disk_bytes / (1024 * 1024), 2),
        "rss_before_load_mb": round(rss_before / (1024 * 1024), 2),
        "rss_after_load_mb": round(rss_after_load / (1024 * 1024), 2),
        "rss_peak_inference_mb": round(rss_peak / (1024 * 1024), 2),
        "cpu_threads_used": torch.get_num_threads(),
        "inference_sentences_per_sec_cpu_batch1": round(throughput, 2),
        "n_timed_inferences": N_TIMED,
    }

    out_path = os.path.join(DATA_DIR, "resource_report.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
