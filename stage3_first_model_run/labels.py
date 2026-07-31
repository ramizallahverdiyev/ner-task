"""Shared BIO label schema for the 8 entity types (17 labels total)."""

ENTITY_TYPES = [
    "PERSON",
    "ORGANIZATION",
    "LOCATION",
    "TIMEDATE",
    "PRODUCT",
    "WORKOFART",
    "JOB",
    "AMOUNT",
]

LABEL_LIST = ["O"] + [f"{prefix}-{t}" for t in ENTITY_TYPES for prefix in ("B", "I")]
LABEL2ID = {label: i for i, label in enumerate(LABEL_LIST)}
ID2LABEL = {i: label for i, label in enumerate(LABEL_LIST)}
