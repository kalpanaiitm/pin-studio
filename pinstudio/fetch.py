"""Read a blog post or product page into a clean structure the rest of the app can use."""
import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (PinStudio; personal content tool)"}
NOISE = ("script", "style", "nav", "footer", "header", "form", "aside", "noscript", "iframe")


@dataclass
class Section:
    heading: str
    text: str = ""
    bullets: list = field(default_factory=list)


@dataclass
class Page:
    url: str
    kind: str                 # blog | product
    title: str
    description: str = ""
    image_url: str = ""
    price: str = ""
    sections: list = field(default_factory=list)

    @property
    def full_text(self) -> str:
        parts = [self.title, self.description, self.price]
        for s in self.sections:
            parts += [s.heading, s.text, *s.bullets]
        return "\n".join(p for p in parts if p)

    def outline(self, max_chars: int = 9000) -> str:
        """Compact text version for the AI prompt (keeps cost low)."""
        lines = [f"TITLE: {self.title}", f"TYPE: {self.kind}", f"URL: {self.url}"]
        if self.description:
            lines.append(f"SUMMARY: {self.description}")
        if self.price:
            lines.append(f"PRICE: {self.price}")
        for s in self.sections:
            lines.append(f"\n## {s.heading}")
            if s.text:
                lines.append(s.text)
            lines += [f"- {b}" for b in s.bullets]
        return "\n".join(lines)[:max_chars]


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _meta(soup, *names):
    for name in names:
        tag = soup.find("meta", attrs={"property": name}) or soup.find("meta", attrs={"name": name})
        if tag and tag.get("content"):
            return _clean(tag["content"])
    return ""


def parse_html(html: str, url: str) -> Page:
    soup = BeautifulSoup(html, "lxml")
    host = urlparse(url).netloc.lower()
    kind = "product" if "payhip.com" in host or soup.find("meta", attrs={"property": "og:type", "content": "product"}) else "blog"
    title = _meta(soup, "og:title") or _clean(soup.title.string if soup.title else "")
    h1 = soup.find("h1")
    if h1 and _clean(h1.get_text()):
        title = _clean(h1.get_text())
    title = re.sub(r"\s*[|–-]\s*(MoneySavvyUK|Payhip).*$", "", title, flags=re.I)
    page = Page(url=url, kind=kind, title=title, description=_meta(soup, "og:description", "description"),
                image_url=_meta(soup, "og:image"))
    price = soup.find(attrs={"class": re.compile(r"price", re.I)})
    if price:
        m = re.search(r"[£$€]\s?\d+(?:\.\d{2})?", price.get_text())
        page.price = m.group(0) if m else ""
    for tag in soup(NOISE):
        tag.decompose()
    body = soup.find("article") or soup.find(class_=re.compile(r"entry-content|post-content|product-description|description", re.I)) or soup.body or soup
    current = Section(heading="Introduction")
    for el in body.find_all(["h2", "h3", "p", "li"]):
        if el.name in ("h2", "h3"):
            if current.text or current.bullets:
                page.sections.append(current)
            current = Section(heading=_clean(el.get_text()))
        elif el.name == "p":
            t = _clean(el.get_text())
            if len(t) > 25 and not re.search(r"cookie|subscribe|newsletter|affiliate", t, re.I):
                current.text = f"{current.text} {t}".strip()
        elif el.name == "li" and el.find_parent(["nav", "footer"]) is None:
            t = _clean(el.get_text())
            if 3 < len(t) < 220:
                current.bullets.append(t)
    if current.text or current.bullets:
        page.sections.append(current)
    return page


def fetch_page(url: str, timeout: int = 20) -> Page:
    if not re.match(r"^https?://", url or ""):
        raise ValueError("Please paste a full link starting with https://")
    response = requests.get(url, headers=HEADERS, timeout=timeout)
    response.raise_for_status()
    page = parse_html(response.text, url)
    if not page.sections:
        raise ValueError("Couldn't find the article text on that page.")
    return page
