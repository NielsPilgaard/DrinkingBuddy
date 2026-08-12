import re
from dataclasses import dataclass

# Fixed keyword/pattern matching only at MVP - no ML/NLP
# (tasks/13-chat-safety-filters.md). Danish + English coverage only.

MEETUP_CATEGORY = "meetup_proposal"
AGE_UNDER_18_CATEGORY = "age_disclosure_under_18"
CONTACT_INFO_CATEGORY = "contact_info_sharing"

CATEGORIES = (MEETUP_CATEGORY, AGE_UNDER_18_CATEGORY, CONTACT_INFO_CATEGORY)

# (slug, category, regex) - the default, code-shipped seed set. Runtime rules
# live in the chat_safety_patterns table (DB-editable, see
# tasks/13-chat-safety-filters.md "Config" scope); this list only seeds that
# table on first migration and acts as a fallback if the table is empty.
DEFAULT_PATTERNS: list[tuple[str, str, str]] = [
    (
        "meetup-da",
        MEETUP_CATEGORY,
        r"\b(skal vi m[øo]des|kan vi m[øo]des|m[øo]de dig|ses i (virkelig)?heden|"
        r"m[øo]des irl|hvor bor du)\b",
    ),
    (
        "meetup-en",
        MEETUP_CATEGORY,
        r"\b(let'?s meet up|can we meet|meet in person|meet irl|where do you live|"
        r"send (me )?your location)\b",
    ),
    (
        "age-question-da",
        AGE_UNDER_18_CATEGORY,
        r"\bhvor gammel er du\b",
    ),
    (
        "age-question-en",
        AGE_UNDER_18_CATEGORY,
        r"\bhow old are you\b",
    ),
    (
        "contact-handles",
        CONTACT_INFO_CATEGORY,
        r"\b(instagram|insta|snapchat|snap|facebook|fb|tiktok|whatsapp|telegram|discord)\b",
    ),
    (
        "contact-phone",
        CONTACT_INFO_CATEGORY,
        r"(\+?\d[\d\s-]{6,}\d)",
    ),
]

# Standalone age-answer pattern, applied only to the message that follows an
# age-question hit within the same call (see matcher_state.py) - a bare
# number isn't safe to flag as a category on its own.
_AGE_ANSWER_RE = re.compile(r"\b(1[0-7]|[1-9])\s*(år|years?|yo)?\b", re.IGNORECASE)


@dataclass(frozen=True)
class CompiledPattern:
    slug: str
    category: str
    regex: re.Pattern[str]


def compile_patterns(rows: list[tuple[str, str, str]]) -> list[CompiledPattern]:
    return [
        CompiledPattern(slug=slug, category=category, regex=re.compile(pattern, re.IGNORECASE))
        for slug, category, pattern in rows
    ]


def match_message(text: str, patterns: list[CompiledPattern]) -> CompiledPattern | None:
    """Returns the first pattern that matches `text`, or None."""
    for compiled in patterns:
        if compiled.regex.search(text):
            return compiled
    return None


def parse_age_under_18(text: str) -> int | None:
    """If `text` parses as an age answer under 18, returns that age. Used to
    resolve an age-question -> age-answer exchange into the
    age_disclosure_under_18 category (task 13 scope: "age-question pattern
    followed by an answer parsing to under 18")."""
    match = _AGE_ANSWER_RE.search(text)
    if match is None:
        return None
    age = int(match.group(1))
    if 0 < age < 18:
        return age
    return None
