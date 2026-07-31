"""
JOB and WORKOFART candidate-flagging word lists, per Stage 2 decision 9.
These are first-pass candidate signals only -- every flagged span still
goes through the full policy-correction pass in apply_policy.py before
being trusted as a final label.
"""

JOB_TERMS = [
    # Business/exec
    "CEO", "chairman", "chairwoman", "chairperson", "founder", "co-founder",
    "executive director", "managing director", "vice president", "treasurer",
    "spokesperson", "general manager", "board member",
    # Government/politics
    "senator", "governor", "mayor", "ambassador", "minister",
    "secretary of state", "congressman", "congresswoman", "representative",
    "prime minister", "president", "councilman", "councilwoman",
    # Military/law enforcement
    "general", "colonel", "lieutenant", "sergeant", "captain", "admiral",
    "sheriff", "detective", "police officer", "chief of police",
    # Academia/professional
    "professor", "dean", "principal", "superintendent", "researcher",
    "scientist", "engineer", "architect", "lawyer", "judge", "attorney",
    "accountant", "analyst", "consultant",
    # Medical
    "doctor", "physician", "surgeon", "nurse", "dentist", "pharmacist",
    "therapist", "paramedic",
    # Media/arts
    "journalist", "editor", "author", "novelist", "director", "producer",
    "actor", "actress", "musician", "composer", "artist", "photographer",
    "anchor", "correspondent",
    # Sports
    "coach", "head coach", "manager", "player", "athlete", "captain",
    # Trades/other
    "teacher", "chef", "pilot", "farmer", "bricklayer", "electrician",
    "plumber", "technician",
]

# Sorted longest-first so multi-word terms match before their single-word
# substrings (e.g. "head coach" before "coach").
JOB_TERMS = sorted(set(JOB_TERMS), key=len, reverse=True)

WORKOFART_TRIGGER_NOUNS = [
    "novel", "book", "film", "movie", "album", "song", "painting", "play",
    "poem", "article", "report", "opera", "sculpture", "documentary",
    "series", "show",
]

WORKOFART_TRIGGER_VERBS = [
    "wrote", "directed", "starred in", "released", "published", "composed",
    "painted", "titled", "called", "authored", "produced",
]

# PRODUCT: spaCy's small-model PRODUCT tag turned out to have ~0% precision
# in QA spot-checks (mislabeling PERSON/LOCATION/WORKOFART as PRODUCT), so
# PRODUCT uses the same trigger-word + capture-pattern mechanism as
# WORKOFART instead (Stage 2 decision 10).
PRODUCT_TRIGGER_NOUNS = [
    "brand", "model", "device", "smartphone", "car", "vehicle", "watch",
    "perfume", "fragrance", "cologne", "laptop", "camera", "console",
    "drink", "beverage", "chemical", "formula", "line", "edition",
]

PRODUCT_TRIGGER_VERBS = [
    "launched", "released", "manufactured", "produced", "sold", "marketed",
    "introduced", "unveiled", "discontinued",
]
