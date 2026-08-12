from app.chat_safety.matcher import (
    AGE_UNDER_18_CATEGORY,
    CONTACT_INFO_CATEGORY,
    DEFAULT_PATTERNS,
    MEETUP_CATEGORY,
    compile_patterns,
    match_message,
    parse_age_under_18,
)

_PATTERNS = compile_patterns(DEFAULT_PATTERNS)


def test_matches_danish_meetup_phrase():
    hit = match_message("skal vi mødes i morgen?", _PATTERNS)
    assert hit is not None
    assert hit.category == MEETUP_CATEGORY


def test_matches_english_meetup_phrase():
    hit = match_message("let's meet up sometime", _PATTERNS)
    assert hit is not None
    assert hit.category == MEETUP_CATEGORY


def test_matches_age_question_da_and_en():
    da_hit = match_message("hvor gammel er du?", _PATTERNS)
    en_hit = match_message("how old are you?", _PATTERNS)
    assert da_hit is not None
    assert en_hit is not None
    assert da_hit.category == AGE_UNDER_18_CATEGORY
    assert en_hit.category == AGE_UNDER_18_CATEGORY


def test_matches_social_handle_and_phone_number():
    handle_hit = match_message("add me on instagram", _PATTERNS)
    phone_hit = match_message("call me at 12345678", _PATTERNS)
    assert handle_hit is not None
    assert phone_hit is not None
    assert handle_hit.category == CONTACT_INFO_CATEGORY
    assert phone_hit.category == CONTACT_INFO_CATEGORY


def test_no_match_on_unrelated_message():
    assert match_message("what kind of beer do you like?", _PATTERNS) is None


def test_parse_age_under_18_accepts_plain_number():
    assert parse_age_under_18("15") == 15
    assert parse_age_under_18("im 16 years old") == 16


def test_parse_age_under_18_rejects_18_and_over():
    assert parse_age_under_18("18") is None
    assert parse_age_under_18("25") is None


def test_parse_age_under_18_none_when_no_number():
    assert parse_age_under_18("i'd rather not say") is None
