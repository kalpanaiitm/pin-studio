from pinstudio.validate import normalise
from pinstudio.config import load_settings


def test_missing_title_and_fields_do_not_crash():
    s = load_settings(use_prefs=False)
    p = normalise({"headline": "Kids Eat Free in the UK", "layout": "weird", "items": [3, None, "a"]}, s, set())
    assert p["title"] == "Kids Eat Free in the UK"
    assert p["layout"] == "hero" and p["items"] == ["3", "a"]
    assert p["description"] == "" and p["alt"] and p["filename"]


def test_completely_empty_pin():
    s = load_settings(use_prefs=False)
    p = normalise({}, s, set())
    assert p["filename"] == "pin" and p["title"] == ""
