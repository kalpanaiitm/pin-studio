from pinstudio.generate import make_pins, regenerate_one, suggest_keywords
from pinstudio.llm import LLM


def test_openai_path_end_to_end(page, settings, fake_openai):
    settings["llm"]["mode"] = "openai"
    llm = LLM(settings)
    kw = suggest_keywords(page, settings, llm)
    pins = make_pins(page, kw, settings, llm, n=10)
    assert kw["main_keyword"] == "sell on vinted uk" and len(pins) == 10
    assert fake_openai[0]["headers"]["Authorization"] == "Bearer test-key-not-real"
    assert fake_openai[1]["body"]["response_format"] == {"type": "json_object"}
    assert "Do NOT use hashtags" in fake_openai[1]["body"]["messages"][0]["content"]
    assert llm.calls == 2 and 0 < llm.cost_usd < 0.01
    assert all(p["filename"].startswith("sell-on-vinted-uk") for p in pins)
    assert not [i for p in pins for i in p["issues"] if i["level"] == "error"]


def test_missing_key_gives_clear_message(page, settings, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    settings["llm"]["mode"] = "openai"
    try:
        suggest_keywords(page, settings, LLM(settings))
        assert False
    except Exception as e:
        assert "OPENAI_API_KEY" in str(e)


def test_offline_mode_makes_15_unique_pins(page, settings):
    llm = LLM(settings)
    kw = suggest_keywords(page, settings, llm)
    pins = make_pins(page, kw, settings, llm)
    assert len(pins) == 15 and len({p["title"] for p in pins}) == 15
    assert len({p["filename"] for p in pins}) == 15
    assert kw["board_suggestion"] == "Vinted & Reselling Tips UK"


def test_regenerate_replaces_only_one(page, settings):
    llm = LLM(settings)
    kw = suggest_keywords(page, settings, llm)
    pins = make_pins(page, kw, settings, llm, n=10)
    new = regenerate_one(page, kw, settings, llm, pins, 3, "hero")
    assert len(new) == 10 and new[3]["title"] != pins[3]["title"] and new[4] == pins[4]
