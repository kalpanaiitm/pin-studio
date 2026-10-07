"""Offline generator (no API key). Builds keywords and pins straight from the page structure.

The copy is plainer than the AI version, but it is free, instant and uses only the page's own words.
"""
import re

from pinstudio.validate import slugify

GENERIC = re.compile(r"\b(a|an|the|guide|beginner'?s|complete|ultimate|explained|\(\d{4}\)|\d{4})\b", re.I)


def _short(text, n=38):
    text = re.sub(r"\s+", " ", text).strip().rstrip(".")
    if len(text) <= n:
        return text
    cut = text[:n].rsplit(" ", 1)[0]
    return cut.rstrip(",;:")


def _nice(phrase, source_title=""):
    """Use the phrase's casing from the page title when it appears there (keeps "Vinted", "HMRC")."""
    m = re.search(re.escape(phrase), source_title, re.I)
    out = m.group(0) if m else phrase
    out = out[:1].upper() + out[1:]
    return re.sub(r"\buk\b", "UK", out)


def keywords(page, boards):
    base = re.sub(r"[:|–-].*$", "", page.title)
    main = re.sub(r"\s+", " ", GENERIC.sub(" ", base)).strip().lower()
    main = re.sub(r"^how to ", "", main) or page.title.lower()
    related = []
    for s in page.sections:
        h = re.sub(r"[?!.]", "", s.heading.lower())
        if s.heading != "Introduction" and h not in related:
            related.append(h)
    words = [w for w in main.split() if len(w) > 3]
    board = next((b for b in boards if any(re.search(rf"\b{re.escape(w)}\b", b.lower()) for w in words)),
                 boards[0] if boards else "")
    return {"main_keyword": main, "related_keywords": related[:10], "board_suggestion": board,
            "notes": "Offline mode: keywords taken from the page title and headings."}


def _layout_for(section):
    h = section.heading.lower()
    n = len(section.bullets)
    if "mistake" in h or "avoid" in h:
        return "mistakes"
    if "checklist" in h:
        return "checklist"
    if "paid" in h and 3 <= n <= 4:
        return "flow"
    if any(w in h for w in ("happens", "steps", "works", "how to")):
        return "steps"
    return "checklist" if n >= 4 else "statement"


def pins(page, kw, boards, n=15):
    main = kw["main_keyword"]
    board = kw.get("board_suggestion") or (boards[0] if boards else "")
    cta = "Read the full guide" if page.kind == "blog" else "See what's inside"
    out = [{"layout": "hero", "kicker": "UK GUIDE" if page.kind == "blog" else "PRINTABLE", "headline": _short(page.title.split(":")[0], 55),
            "sub": _short(page.description or page.title, 130), "items": []}]
    if page.kind == "product" and page.image_url:
        out.append({"layout": "photo", "kicker": page.price or "PRINTABLE", "headline": _short(page.title, 55), "sub": "", "items": []})
    for s in page.sections:
        if s.heading == "Introduction" or not (s.bullets or s.text):
            continue
        layout = _layout_for(s)
        lo, hi = {"mistakes": (3, 6), "checklist": (4, 8), "steps": (3, 6), "flow": (3, 4)}.get(layout, (0, 0))
        items = [_short(b) for b in s.bullets][:hi]
        if layout != "statement" and len(items) < lo:
            layout, items = "statement", []
        sub = _short(s.text or (s.bullets[0] if s.bullets else ""), 130) if layout == "statement" else ""
        out.append({"layout": layout, "kicker": _short(s.heading.upper(), 22), "headline": _short(s.heading, 55), "sub": sub, "items": items})
    extra = [s for s in page.sections if s.heading != "Introduction"]
    frames = ["Quick guide: {h}", "{h}: what to know", "Save this: {h}"]
    i = 0
    while len(out) < n and extra:   # pad with differently-framed hero pins
        s = extra[i % len(extra)]
        frame = frames[(i // len(extra)) % len(frames)]
        out.append({"layout": "hero", "kicker": "SAVE FOR LATER", "headline": _short(frame.format(h=s.heading.rstrip("?")), 55),
                    "sub": _short(s.text or (s.bullets[0] if s.bullets else page.title), 130), "items": []})
        i += 1
    result = []
    for i, p in enumerate(out[:n], 1):
        topic = p["headline"].rstrip("?")
        nice = _nice(main, page.title)
        title = f"{nice}: {topic}" if main.lower() not in topic.lower() else topic
        desc = (f"{topic}: part of our practical {nice} {'guide' if page.kind == 'blog' else 'printable'} for UK readers, "
                f"from MoneySavvyUK. {cta}.")
        result.append({**p, "angle": topic, "title": title[:100], "description": desc[:300],
                       "alt": f"Pinterest pin about {main}: {topic}.", "filename": slugify(f"{main} {topic}"),
                       "board": board, "keywords": [main] + kw["related_keywords"][:2]})
    return result
