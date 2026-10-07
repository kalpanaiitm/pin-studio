"""Prompts. Pinterest SEO rules live here so they are easy to read and change."""

LAYOUTS = {
    "hero": "big headline + one-line subtitle. Use for the main 'how to' / guide pin and question-style pins.",
    "checklist": "headline + 4-8 short items with ticks. Use for checklists and 'do this' lists.",
    "mistakes": "headline + 3-6 short items with crosses. Use for mistakes / things to avoid.",
    "steps": "headline + 3-6 numbered steps. Use for processes in order.",
    "statement": "one bold statement (max 6 words) + a 1-2 sentence explanation. Use for a key rule, myth or insight.",
    "flow": "headline + 3-4 boxes joined by arrows. Use for how something moves from A to B.",
    "photo": "the page's main image + headline band. ONLY for product pages that have an image.",
}

SEO_RULES = """PINTEREST SEO RULES
- Pinterest is a visual search engine. Use the words people actually type into Pinterest search, in UK English.
- Title: max {title_max} characters. Put the main keyword (or a close variant) in the first {kw_first} characters. Clear, specific, no clickbait.
- Description: {d_min}-{d_max} characters, 2-3 natural sentences. Include the main keyword once and 1-2 related keywords naturally,
  say who it is for and what they get, end with a soft call to action (e.g. "Read the full guide"). No keyword stuffing.
- {hashtag_rule}
- Text on the image (headline, items) must repeat the search phrase people use and be readable on a phone: short words, no jargon.
- Alt text: one plain sentence describing what the pin shows, including the keyword naturally. Max {alt_max} characters.
- File name: lowercase-hyphenated, starts with the main keyword, max 70 characters, no dates, ends without extension.
- Each pin needs a DIFFERENT angle, title and description. Pinterest treats near-duplicates as spam."""

FACT_RULES = """ACCURACY RULES (this is a personal-finance brand; trust matters more than clicks)
- Use ONLY facts that appear in the SOURCE. Never add numbers, prices, percentages, fees, dates, earnings or promises that are not in the SOURCE.
- No income claims ("make £500 a month"), no guarantees, no "secret" or "hack" wording.
- Tax, benefits and legal topics: describe what the source says; never give personal advice.
- If the source is a product, describe only what the source says it contains."""

KEYWORDS_SYSTEM = """You are a Pinterest SEO specialist for a UK personal-finance blog.
Suggest keywords people in the UK would type into Pinterest search to find this page.
Return JSON: {"main_keyword": str, "related_keywords": [8-12 str], "board_suggestion": str, "notes": str}
- main_keyword: 2-5 words, the single most searchable phrase that matches the page.
- related_keywords: variations, long-tail phrases and problem phrases (e.g. "sell clothes online uk", "declutter for cash").
  Lowercase. Only phrases genuinely relevant to the SOURCE.
- board_suggestion: pick the best board from BOARDS (copy it exactly).
- notes: one sentence on why, in plain English."""

PINS_SYSTEM = """You are a Pinterest content designer for the UK personal-finance brand {brand}.
Create {n} distinct pins that send readers to the SOURCE page.

{seo}

{facts}

LAYOUTS (choose one per pin; use a good mix, at least 4 different layouts; at least 2 'hero'):
{layouts}

FIELD LIMITS (the design breaks if exceeded)
- kicker: 2-4 words, max 22 characters, UPPERCASE (e.g. "SAVE THIS", "UK GUIDE 2026" only if 2026 is in the source).
- headline: max 55 characters.
- sub: hero/statement only, max 130 characters.
- items: checklist 4-8, mistakes 3-6, steps 3-6, flow 3-4 items; each item max 38 characters.
- board: copy exactly one name from BOARDS.
- keywords: 3 keywords for this pin (main keyword first).

Return JSON: {{"pins": [{{"angle": str, "layout": str, "kicker": str, "headline": str, "sub": str, "items": [str],
"title": str, "description": str, "alt": str, "filename": str, "board": str, "keywords": [str]}}]}}"""


def pins_system(settings: dict, n: int, kind: str, has_image: bool) -> str:
    seo = settings["seo"]
    hashtag_rule = ("You may end the description with 1-2 relevant hashtags." if seo.get("allow_hashtags")
                    else "Do NOT use hashtags; keywords in natural sentences work better on Pinterest now.")
    layouts = {k: v for k, v in LAYOUTS.items() if k != "photo" or (kind == "product" and has_image)}
    if kind == "product" and has_image:
        layouts["photo"] += " Use it for 3-5 of the pins."
    return PINS_SYSTEM.format(
        brand=settings["brand"]["name"], n=n,
        seo=SEO_RULES.format(title_max=seo["title_max"], kw_first=seo["keyword_within_first"], d_min=seo["description_min"],
                             d_max=seo["description_max"], alt_max=seo["alt_max"], hashtag_rule=hashtag_rule),
        facts=FACT_RULES, layouts="\n".join(f"- {k}: {v}" for k, v in layouts.items()))


def pins_user(page, keywords: dict, boards: list) -> str:
    return (f"MAIN KEYWORD: {keywords['main_keyword']}\nRELATED KEYWORDS: {', '.join(keywords['related_keywords'])}\n"
            f"BOARDS: {boards}\n\nSOURCE:\n{page.outline()}")


def keywords_user(page, boards: list) -> str:
    return f"BOARDS: {boards}\n\nSOURCE:\n{page.outline(6000)}"


def regenerate_user(page, keywords: dict, boards: list, existing_titles: list, layout: str, feedback: str) -> str:
    return (pins_user(page, keywords, boards) + f"\n\nCreate exactly 1 NEW pin with layout '{layout}'."
            f" It must not repeat these titles or angles: {existing_titles}."
            + (f" The user asked: {feedback}" if feedback else ""))
