"""Quality checks for every pin: Pinterest limits, SEO placement, design limits and a fact guard."""
import re
from difflib import SequenceMatcher

LIMITS = {"checklist": (4, 8), "mistakes": (3, 6), "steps": (3, 6), "flow": (3, 4)}
NUMBER = re.compile(r"[£$€]\s?\d[\d,]*(?:\.\d+)?|\d+(?:[.,]\d+)?\s?%|\b\d[\d,]*(?:\.\d+)?\b")
STOP = set("a an and the to of for in on with your you how what is are do does can uk".split())


def slugify(text: str, max_len: int = 70) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return slug[:max_len].rstrip("-") or "pin"


def keyword_words(keyword: str):
    return [w for w in re.findall(r"[a-z0-9]+", keyword.lower()) if w not in STOP] or re.findall(r"[a-z0-9]+", keyword.lower())


def keyword_early(title: str, keyword: str, within: int) -> bool:
    head = title[:within].lower()
    if keyword.lower() in head:
        return True
    words = keyword_words(keyword)
    hits = sum(1 for w in words if re.search(rf"\b{re.escape(w)}", head))
    return hits >= max(1, round(len(words) * 0.6))


def _norm_title(t: str) -> str:
    return " ".join(re.findall(r"[a-z0-9£%]+", t.lower()))


def similar_title(title: str, others, threshold: float = 0.85):
    """Return the first existing title that is nearly the same (ignoring case and punctuation)."""
    a = _norm_title(title)
    for other in others:
        b = _norm_title(other)
        if a and b and a != b and SequenceMatcher(None, a, b).ratio() >= threshold:
            return other
    return None


def numbers_in(text: str):
    return {re.sub(r"[\s,]", "", m.group(0)) for m in NUMBER.finditer(text or "")}


def check_pin(pin: dict, source_text: str, main_keyword: str, settings: dict, boards: list, seen_titles: set,
              list_sizes=()) -> list:
    seo, issues = settings["seo"], []

    def add(level, msg):
        issues.append({"level": level, "msg": msg})

    layout = pin.get("layout")
    if layout in LIMITS:
        lo, hi = LIMITS[layout]
        n = len(pin.get("items") or [])
        if not lo <= n <= hi:
            add("error", f"{layout} needs {lo}-{hi} items (has {n})")
        long = [i for i in pin.get("items") or [] if len(i) > 38]
        if long:
            add("warn", f"{len(long)} item(s) over 38 characters may wrap")
    if len(pin.get("headline", "")) > 55:
        add("warn", "headline over 55 characters; the design will shrink it")
    if len(pin.get("kicker", "")) > 22:
        add("warn", "kicker over 22 characters")
    title = pin.get("title", "")
    if not title:
        add("error", "missing title")
    elif len(title) > seo["title_max"]:
        add("error", f"title is {len(title)} characters (max {seo['title_max']})")
    if title and not keyword_early(title, main_keyword, seo["keyword_within_first"]):
        add("warn", f"main keyword not in the first {seo['keyword_within_first']} characters of the title")
    if title.lower() in seen_titles:
        add("error", "duplicate title (already used in this batch or a previous one)")
    else:
        close = similar_title(title, seen_titles, settings["seo"].get("near_duplicate", 0.85))
        if close:
            add("error", f"almost the same as an existing title: '{close}'. Change the angle or wording.")
    desc = pin.get("description", "")
    if not seo["description_min"] <= len(desc) <= seo["description_max"]:
        add("warn", f"description is {len(desc)} characters (aim for {seo['description_min']}-{seo['description_max']})")
    if not any(w in desc.lower() for w in keyword_words(main_keyword)):
        add("warn", "description doesn't mention the main keyword")
    if not seo.get("allow_hashtags") and "#" in desc:
        add("warn", "hashtags present (turned off in settings)")
    if len(pin.get("alt", "")) > seo["alt_max"] or not pin.get("alt"):
        add("warn", "alt text missing or too long")
    if boards and pin.get("board") not in boards:
        add("error", f"board '{pin.get('board')}' is not in your board list")
    # Fact guard: every number on the pin or in its copy must appear in the source page.
    # Counts are fine when they describe a list: "6 mistakes" with 6 items on the pin, or a 6-item list in the post.
    source_numbers = numbers_in(source_text) | {str(len(pin.get("items") or []))} | {str(n) for n in list_sizes}
    pin_text = " ".join([pin.get("headline", ""), pin.get("sub", ""), pin.get("kicker", ""), title, desc, *(pin.get("items") or [])])
    invented = sorted(n for n in numbers_in(pin_text) if n not in source_numbers)
    if invented:
        add("error", f"number(s) not found in your post: {', '.join(invented)}. Check before publishing.")
    return issues


def normalise(pin: dict, settings: dict, used_files: set) -> dict:
    """Tidy fields without changing meaning."""
    p = {k: (v.strip() if isinstance(v, str) else v) for k, v in pin.items()}
    p["kicker"] = (p.get("kicker") or "").upper()
    p["items"] = [i.strip() for i in (p.get("items") or []) if i and i.strip()]
    p["sub"] = p.get("sub") or ""
    p["keywords"] = [k.strip().lower() for k in (p.get("keywords") or []) if k.strip()][:5]
    if not settings["seo"].get("allow_hashtags"):
        p["description"] = re.sub(r"\s*#\w+", "", p.get("description", "")).strip()
    base = slugify(p.get("filename") or p.get("title", ""))
    name, n = base, 2
    while name in used_files:
        name, n = f"{base}-{n}", n + 1
    used_files.add(name)
    p["filename"] = name
    return p
