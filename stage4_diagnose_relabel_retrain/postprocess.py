"""
Pattern 2 fix (see stage4_decisions.md): merges adjacent same-label
predicted spans that have no intervening punctuation, e.g. "Prime" + "
Minister" (JOB, JOB) -> "Prime Minister" (JOB). Operates on decoded
entity spans (start/end/label over the original text), used by both
train.py's evaluation step and the wild-QA re-run.
"""
import re

NON_MERGE_GAP_RE = re.compile(r"[.,;:!?()\"']")


def merge_adjacent_same_label(text, spans):
    """spans: list of {"start", "end", "label"} sorted by start.
    Merges spans[i] into spans[i-1] when same label and the text between
    them contains no punctuation (only whitespace, or nothing)."""
    if not spans:
        return spans
    spans = sorted(spans, key=lambda s: s["start"])
    merged = [dict(spans[0])]
    for s in spans[1:]:
        prev = merged[-1]
        gap = text[prev["end"]:s["start"]]
        if s["label"] == prev["label"] and NON_MERGE_GAP_RE.search(gap) is None:
            prev["end"] = s["end"]
        else:
            merged.append(dict(s))
    return merged
