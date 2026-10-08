from pinstudio.validate import check_pin, keyword_early, normalise

BASE = {"layout": "hero", "kicker": "GUIDE", "headline": "How to Sell on Vinted UK", "sub": "", "items": [],
        "title": "How to Sell on Vinted UK: Beginner's Guide",
        "description": "A beginner's guide to selling on Vinted UK: photos, pricing, postage and getting paid. Read the full guide.",
        "alt": "Pin about selling on Vinted UK.", "board": "Vinted & Reselling Tips UK"}


def msgs(pin, page, settings, seen=None):
    return [i["msg"] for i in check_pin(pin, page.full_text, "sell on vinted uk", settings, settings["boards"], seen or set())]


def test_good_pin_has_no_issues(page, settings):
    assert msgs(BASE, page, settings) == []


def test_fact_guard_catches_invented_numbers(page, settings):
    pin = {**BASE, "headline": "Make £500 a month on Vinted", "description": BASE["description"] + " Sellers earn 30% more."}
    out = " ".join(msgs(pin, page, settings))
    assert "£500" in out and "30%" in out


def test_numbers_in_the_source_are_allowed(page, settings):
    assert not any("number" in m for m in msgs({**BASE, "title": "Sell on Vinted UK: Beginner's Guide (2026)"}, page, settings))


def test_seo_and_limits(page, settings):
    pin = {**BASE, "title": "A really nice and very long introduction before we get to Vinted selling",
           "layout": "checklist", "items": ["one", "two"], "board": "Random Board", "description": "Too short #vinted"}
    out = " ".join(msgs(pin, page, settings, {"how to sell on vinted uk: beginner's guide"}))
    for expected in ("first 40", "needs 4-8 items", "not in your board list", "description is", "hashtags"):
        assert expected in out


def test_duplicate_titles_flagged(page, settings):
    assert any("duplicate" in m for m in msgs(BASE, page, settings, {BASE["title"].lower()}))


def test_keyword_early_accepts_variants():
    assert keyword_early("How to Sell on Vinted UK fast", "sell on vinted uk", 40)
    assert keyword_early("Vinted selling tips for UK beginners", "sell on vinted uk", 40)


def test_normalise_strips_hashtags_and_dedupes_files(settings):
    used = set()
    a = normalise({**BASE, "description": "Nice #vinted #uk", "filename": "Sell on Vinted UK!"}, settings, used)
    b = normalise({**BASE, "filename": "sell-on-vinted-uk"}, settings, used)
    assert a["description"] == "Nice" and a["filename"] == "sell-on-vinted-uk" and b["filename"] == "sell-on-vinted-uk-2"


def test_list_counts_are_not_flagged_but_other_numbers_are(page, settings):
    pin = {**BASE, "layout": "mistakes", "headline": "6 Vinted Mistakes Beginners Make", "items": ["a", "b", "c", "d", "e", "f"]}
    assert not any("number" in m for m in msgs(pin, page, settings))
    pin["headline"] = "11 Vinted Mistakes Beginners Make"
    assert any("11" in m for m in msgs(pin, page, settings))


def test_near_duplicate_titles_blocked(page, settings):
    out = msgs({**BASE, "title": "How to Sell on Vinted in the UK: Beginners Guide"}, page, settings,
               {"how to sell on vinted uk: beginner's guide"})
    assert any("almost the same" in m for m in out)
    assert not any("almost the same" in m for m in msgs({**BASE, "title": "6 Vinted Mistakes Beginners Make"}, page, settings,
                                                         {"how to sell on vinted uk: beginner's guide"}))
