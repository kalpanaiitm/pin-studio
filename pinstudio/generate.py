"""The pipeline: page -> keywords -> pins (AI or offline) -> tidy + checks."""
from pinstudio import mock, prompts
from pinstudio.llm import LLM
from pinstudio.validate import check_pin, normalise


def suggest_keywords(page, settings, llm: LLM) -> dict:
    boards = settings["boards"]
    if llm.mode == "mock":
        return mock.keywords(page, boards)
    data = llm.json(prompts.KEYWORDS_SYSTEM, prompts.keywords_user(page, boards))
    data["related_keywords"] = [k.strip().lower() for k in data.get("related_keywords", []) if k.strip()][:12]
    data["main_keyword"] = data.get("main_keyword", page.title).strip().lower()
    if data.get("board_suggestion") not in boards and boards:
        data["board_suggestion"] = boards[0]
    return data


def make_pins(page, kw: dict, settings, llm: LLM, n: int = None) -> list:
    n = n or settings["pins_per_post"]
    if llm.mode == "mock":
        raw = mock.pins(page, kw, settings["boards"], n)
    else:
        system = prompts.pins_system(settings, n, page.kind, bool(page.image_url))
        raw = llm.json(system, prompts.pins_user(page, kw, settings["boards"])).get("pins", [])[:n]
    return finish(raw, page, kw, settings)


def regenerate_one(page, kw, settings, llm, pins, index, layout, feedback="") -> list:
    if llm.mode == "mock":
        alt = mock.pins(page, kw, settings["boards"], len(pins) + 5)
        titles = {p["title"].lower() for p in pins}
        new = next((p for p in alt if p["title"].lower() not in titles), alt[-1])
    else:
        system = prompts.pins_system(settings, 1, page.kind, bool(page.image_url))
        user = prompts.regenerate_user(page, kw, settings["boards"], [p["title"] for p in pins], layout, feedback)
        new = llm.json(system, user).get("pins", [{}])[0]
    others = [p for i, p in enumerate(pins) if i != index]
    fixed = finish([new], page, kw, settings, taken=others)[0]
    return pins[:index] + [fixed] + pins[index + 1:]


def finish(raw, page, kw, settings, taken=(), history_titles=()):
    used_files = {p["filename"] for p in taken}
    seen = {t.lower() for t in history_titles} | {p["title"].lower() for p in taken}
    out = []
    for pin in raw:
        p = normalise(pin, settings, used_files)
        p["link"] = page.url
        p["issues"] = check_pin(p, page.full_text, kw["main_keyword"], settings, settings["boards"], seen, _sizes(page))
        seen.add(p.get("title", "").lower())
        out.append(p)
    return out


def recheck(pins, page, kw, settings, history_titles=()):
    """Re-run the checks after the user edits pins in the app."""
    seen = {t.lower() for t in history_titles}
    for p in pins:
        p["issues"] = check_pin(p, page.full_text, kw["main_keyword"], settings, settings["boards"], seen, _sizes(page))
        seen.add(p.get("title", "").lower())
    return pins


def _sizes(page):
    return {len(s.bullets) for s in page.sections if s.bullets}
