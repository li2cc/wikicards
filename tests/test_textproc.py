from wikicard import textproc as t


def test_ordinals():
    assert [t.ordinal(n) for n in (1, 2, 3, 4, 11, 12, 13, 21, 22, 24, 45)] == [
        "1st", "2nd", "3rd", "4th", "11th", "12th", "13th", "21st", "22nd", "24th", "45th"]
    assert t.ordinal_phrase([22, 24]) == "22nd and 24th"
    assert t.ordinal_phrase([7]) == "7th"


def test_format_years():
    assert t.format_years([(1789, 1797)]) == "1789–1797"
    assert t.format_years([(1841, 1841)]) == "1841"
    assert t.format_years([(2017, 2021), (2025, None)]) == "2017–2021, 2025–present"


def test_parse_term():
    assert t.parse_term("April 30, 1789 – March 4, 1797") == (1789, 1797)
    assert t.parse_term("January 20, 2025 – Incumbent") == (2025, None)
    assert t.parse_term("March 4, 1841 – April 4, 1841") == (1841, 1841)
    assert t.parse_term("nothing") is None


def test_split_sentences_handles_abbreviations():
    s = t.split_sentences("He was the first U.S. president. Franklin D. Roosevelt won. Done.")
    assert s == ["He was the first U.S. president.", "Franklin D. Roosevelt won.", "Done."]


def test_mask_name():
    assert t.mask_name("Lincoln's cousin Abraham met Mr. Lincoln.", "Abraham Lincoln") == \
        "_____'s cousin _____ met Mr. _____."


def test_hint_shape():
    paras = ["Abraham Lincoln was the 16th president. He led the Union through the American "
             "Civil War and abolished slavery in the United States."]
    hint = t.build_hint([16], "Abraham Lincoln", paras)
    assert hint.startswith("The 16th president of the United States. ")
    assert "Lincoln" not in hint


def test_highlights_scoring_and_filters():
    paras = [
        "First paragraph is the description. It has two sentences here, too.",
        "He was born in a small town to a family of farmers and went to school nearby. "
        "He signed the Civil Rights Act and declared a national emergency during the crisis. "
        "The Great Depression shaped his early career as a young lawyer in the capital. "
        "The Great Depression also defined the later years of his administration as president."
    ]
    hl = t.build_highlights("Test Person", paras)
    assert hl[0].startswith("He signed the Civil Rights Act")
    assert not any("born" in h for h in hl)
    assert sum("Great Depression" in h for h in hl) == 1


def test_shorten():
    long = "word " * 30 + "end, and more words follow here " + "x " * 100
    out = t.shorten(long)
    assert len(out) <= 281 and out.endswith("…")
