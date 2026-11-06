from fondasi.normalize import is_quote_in_source, normalize_for_match


def test_whitespace_and_case_still_match():
    source = "The  Onboarding Program\nlasts three weeks and begins every Monday."
    quote = "the onboarding program lasts three weeks"
    assert is_quote_in_source(quote, source)


def test_short_quote_under_six_words_returns_false():
    source = "The property is managed by the local team."
    assert is_quote_in_source("the property", source) is False


def test_curly_quotes_match_straight_quotes():
    source = "All notes are stored in the \u201cshared workspace\u201d for every team."
    quote = 'all notes are stored in the "shared workspace" for every team'
    assert is_quote_in_source(quote, source)


def test_zero_width_characters_are_ignored():
    source = "Mentors meet their agents twice every\u200b week."
    assert is_quote_in_source("mentors meet their agents twice every week", source)


def test_normalize_collapses_whitespace():
    assert normalize_for_match("  Hello \n\n World \t") == "hello world"
