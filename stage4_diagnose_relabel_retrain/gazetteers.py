"""
JOB/WORKOFART/PRODUCT candidate-flagging word lists and patterns for Stage 4,
extending Stage 2's gazetteers.py per the Stage 4 diagnosis of the 10 Stage 3
wild-QA problem patterns (see stage4_decisions.md, private planning notes).

Extensions over Stage 2:
  - JOB_TERMS: broader role-noun vocabulary beyond the original fixed list
    (pattern 4 -- "cardiologist" was never seen as JOB in training).
  - PRODUCT_ALPHANUMERIC_PATTERN: a dedicated regex for alphanumeric
    vehicle/aircraft/equipment model designators (pattern 9 -- "RC-135U"
    was mislabeled ORGANIZATION with a boundary split), independent of the
    noun-trigger-based PRODUCT pattern already in Stage 2.
  - BRAND_PERSON_NAMES: an explicit list of brand names shaped like personal
    names (pattern 8 -- "Hugo Boss" misclassified PERSON), force-labeled
    ORGANIZATION wherever they appear as a whole word/phrase match.
"""
import re

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
    # Medical (extended -- pattern 4: broader specialist vocabulary)
    "doctor", "physician", "surgeon", "nurse", "dentist", "pharmacist",
    "therapist", "paramedic", "cardiologist", "neurologist", "oncologist",
    "radiologist", "psychiatrist", "pediatrician", "dermatologist",
    "anesthesiologist", "gynecologist", "orthopedist", "pathologist",
    "endocrinologist",
    # Media/arts
    "journalist", "editor", "author", "novelist", "director", "producer",
    "actor", "actress", "musician", "composer", "artist", "photographer",
    "anchor", "correspondent",
    # Sports
    "coach", "head coach", "manager", "player", "athlete", "captain",
    # Trades/other (extended)
    "teacher", "chef", "pilot", "farmer", "bricklayer", "electrician",
    "plumber", "technician", "surveyor", "geologist", "biologist",
    "chemist", "economist", "diplomat",
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

PRODUCT_TRIGGER_NOUNS = [
    "brand", "model", "device", "smartphone", "car", "vehicle", "watch",
    "perfume", "fragrance", "cologne", "laptop", "camera", "console",
    "drink", "beverage", "chemical", "formula", "line", "edition",
    # Extended for pattern 9/10 (aircraft/equipment + PRODUCT volume)
    "aircraft", "jet", "engine", "rifle", "revolver", "tank", "warship",
]

PRODUCT_TRIGGER_VERBS = [
    "launched", "released", "manufactured", "produced", "sold", "marketed",
    "introduced", "unveiled", "discontinued",
]

# Pattern 9: alphanumeric vehicle/aircraft/equipment model designators, e.g.
# "RC-135U", "F-16", "Boeing 747", "AK-47". Matches a designator token
# (letters+digits, optionally hyphenated, optional trailing letter suffix)
# on its own, or a manufacturer name immediately followed by one.
PRODUCT_ALPHANUMERIC_PATTERN = re.compile(
    r"\b(?:[A-Z]{1,4}-\d{2,4}[A-Z]?|(?:Boeing|Airbus|Cessna|Lockheed|McDonnell Douglas)\s+\d{2,4}[A-Z]?)\b"
)

# Pattern 8: brand names shaped like personal names -- force-labeled
# ORGANIZATION wherever matched, since spaCy/PERSON-shape heuristics
# misclassify them as PERSON.
BRAND_PERSON_NAMES = [
    "Hugo Boss", "Ralph Lauren", "Tommy Hilfiger", "Calvin Klein",
    "Louis Vuitton", "Christian Dior", "Giorgio Armani", "Michael Kors",
    "Victoria's Secret", "Levi Strauss", "Marc Jacobs", "Tom Ford",
    "Vera Wang", "Kate Spade",
]
