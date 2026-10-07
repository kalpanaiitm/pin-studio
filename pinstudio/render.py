"""Render 1000x1500 Pinterest pins with Pillow in the brand's colours. No AI image costs.

Fonts: the Inter family, bundled in assets/fonts (SIL Open Font Licence). Falls back to system fonts.
"""
import io
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps

W, H = 1000, 1500
ROOT = Path(__file__).resolve().parents[1]
FONT_DIRS = [ROOT / "assets" / "fonts", Path("/usr/share/fonts/opentype/inter"), Path("C:/Windows/Fonts")]
FONT_FILES = {"display": ["InterDisplay-ExtraBold.otf", "Inter-ExtraBold.otf", "segoeuib.ttf", "arialbd.ttf"],
              "bold": ["Inter-Bold.otf", "segoeuib.ttf", "arialbd.ttf"],
              "semi": ["Inter-SemiBold.otf", "seguisb.ttf", "arialbd.ttf"],
              "medium": ["Inter-Medium.otf", "segoeui.ttf", "arial.ttf"],
              "regular": ["Inter-Regular.otf", "segoeui.ttf", "arial.ttf"]}
BRAND = {}
_FONT_CACHE = {}


def set_brand(brand: dict):
    BRAND.clear()
    BRAND.update(brand["colours"])
    BRAND["site"] = brand["site"]
    BRAND["cta"] = brand.get("cta", "Read the full guide")
    BRAND["product_cta"] = brand.get("product_cta", "Get the printable")


def font(weight, size):
    key = (weight, size)
    if key not in _FONT_CACHE:
        for name in FONT_FILES[weight]:
            for folder in FONT_DIRS:
                if (folder / name).exists():
                    _FONT_CACHE[key] = ImageFont.truetype(str(folder / name), size)
                    break
            if key in _FONT_CACHE:
                break
        else:
            _FONT_CACHE[key] = ImageFont.load_default(size)
    return _FONT_CACHE[key]


def wrap(draw, text, fnt, width):
    words, lines, line = text.split(), [], ""
    for word in words:
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=fnt) <= width:
            line = trial
        else:
            lines.append(line)
            line = word
    lines.append(line)
    return lines


def fit(draw, text, weight, width, max_size, min_size, max_lines):
    """Largest font size at which text wraps into max_lines within width."""
    for size in range(max_size, min_size - 1, -2):
        fnt = font(weight, size)
        lines = wrap(draw, text, fnt, width)
        if len(lines) <= max_lines:
            return fnt, lines
    fnt = font(weight, min_size)
    return fnt, wrap(draw, text, fnt, width)


def text_block(draw, x, y, lines, fnt, fill, spacing=1.12, align="left", box_w=None):
    lh = int(fnt.size * spacing)
    for i, line in enumerate(lines):
        lx = x
        if align == "center":
            lx = x + (box_w - draw.textlength(line, font=fnt)) / 2
        draw.text((lx, y + i * lh), line, font=fnt, fill=fill)
    return y + lh * len(lines)


def pill(draw, x, y, text, bg, fg, size=30, center_w=None):
    fnt = font("bold", size)
    tw = draw.textlength(text, font=fnt)
    pad_x, h = 26, size + 26
    if center_w:
        x = x + (center_w - (tw + 2 * pad_x)) / 2
    draw.rounded_rectangle([x, y, x + tw + 2 * pad_x, y + h], radius=h // 2, fill=bg)
    draw.text((x + pad_x, y + 12), text, font=fnt, fill=fg)
    return y + h


def footer(draw, bg, fg, accent, cta=None):
    cta = cta or BRAND["cta"]
    draw.rectangle([0, H - 150, W, H], fill=bg)
    draw.text((70, H - 108), BRAND["site"], font=font("bold", 40), fill=fg)
    fnt = font("semi", 32)
    label = f"{cta}  >"
    tw = draw.textlength(label, font=fnt)
    draw.rounded_rectangle([W - 70 - tw - 48, H - 118, W - 70, H - 46], radius=36, fill=accent)
    draw.text((W - 70 - tw - 24, H - 102), label, font=fnt, fill=BRAND["white"])


def tick(draw, x, y, s, colour):
    draw.rounded_rectangle([x, y, x + s, y + s], radius=12, fill=colour)
    draw.line([(x + s * 0.24, y + s * 0.52), (x + s * 0.43, y + s * 0.70), (x + s * 0.77, y + s * 0.31)],
              fill=BRAND["white"], width=max(5, s // 9), joint="curve")


def cross(draw, x, y, s, colour):
    draw.ellipse([x, y, x + s, y + s], fill=colour)
    m, w = s * 0.31, max(5, s // 9)
    draw.line([(x + m, y + m), (x + s - m, y + s - m)], fill=BRAND["white"], width=w)
    draw.line([(x + s - m, y + m), (x + m, y + s - m)], fill=BRAND["white"], width=w)


def number(draw, x, y, s, n, colour):
    draw.ellipse([x, y, x + s, y + s], fill=colour)
    fnt = font("bold", int(s * 0.5))
    t = str(n)
    draw.text((x + (s - draw.textlength(t, font=fnt)) / 2, y + s * 0.2), t, font=fnt, fill=BRAND["white"])


def header(img, draw, pin, bg, fg, kicker_bg, height=None):
    fnt, lines = fit(draw, pin["headline"], "display", W - 140, 100, 64, 3)
    lh = int(fnt.size * 1.08)
    h = height or 120 + 66 + 34 + lh * len(lines) + 70
    draw.rectangle([0, 0, W, h], fill=bg)
    y = pill(draw, 70, 90, pin["kicker"], kicker_bg, BRAND["white"])
    text_block(draw, 70, y + 34, lines, fnt, fg, spacing=1.08)
    return h


def list_layout(pin, marker):
    img = Image.new("RGB", (W, H), BRAND["cream"])
    d = ImageDraw.Draw(img)
    top = header(img, d, pin, BRAND["teal"], BRAND["white"], BRAND["coral"])
    items = pin["items"]
    avail = H - 150 - top - 80
    step = min(160, avail / len(items))
    size = int(min(50, step * 0.45))
    s = int(size * 1.35)
    y = top + 60
    for i, item in enumerate(items, 1):
        fnt, lines = fit(d, item, "semi", W - 140 - s - 34, size, 28, 2)
        block_h = int(fnt.size * 1.15) * len(lines)
        cy = y + (step - max(block_h, s)) / 2
        mx = 70
        if marker == "tick":
            tick(d, mx, cy, s, BRAND["green"])
        elif marker == "cross":
            cross(d, mx, cy, s, BRAND["red"])
        else:
            number(d, mx, cy, s, i, BRAND["coral"])
        text_block(d, mx + s + 34, cy + max(0, (s - block_h) / 2), lines, fnt, BRAND["ink"], spacing=1.15)
        if i < len(items):
            d.line([(70, y + step), (W - 70, y + step)], fill=BRAND["line"], width=2)
        y += step
    footer(d, BRAND["deep"], BRAND["white"], BRAND["coral"])
    return img


def hero(pin):
    img = Image.new("RGB", (W, H), BRAND["teal"])
    d = ImageDraw.Draw(img)
    d.ellipse([560, -220, 1260, 480], fill=BRAND["circle"])
    d.ellipse([-260, 980, 380, 1620], fill=BRAND["circle"])
    fnt, lines = fit(d, pin["headline"], "display", W - 140, 124, 80, 4)
    sfnt, slines = fit(d, pin["sub"], "medium", W - 140, 50, 34, 4)
    pill_h, head_h = 32 + 26, int(fnt.size * 1.05) * len(lines)
    sub_h = int(sfnt.size * 1.3) * len(slines)
    total = pill_h + 50 + head_h + 100 + sub_h
    y0 = (H - 150 - total) / 2 - 20                      # centre the content block above the footer
    y = pill(d, 70, y0, pin["kicker"], BRAND["gold"], BRAND["deep"], size=32)
    y = text_block(d, 70, y + 50, lines, fnt, BRAND["white"], spacing=1.05)
    d.rectangle([70, y + 40, 230, y + 52], fill=BRAND["coral"])
    text_block(d, 70, y + 100, slines, sfnt, BRAND["cream"], spacing=1.3)
    footer(d, BRAND["cream"], BRAND["deep"], BRAND["coral"])
    return img


def statement(pin):
    img = Image.new("RGB", (W, H), BRAND["gold"])
    d = ImageDraw.Draw(img)
    pill(d, 0, 230, pin["kicker"], BRAND["deep"], BRAND["white"], size=32, center_w=W)
    fnt, lines = fit(d, pin["headline"], "display", W - 160, 140, 84, 3)
    y = text_block(d, 80, 380, lines, fnt, BRAND["deep"], spacing=1.04, align="center", box_w=W - 160)
    d.rectangle([W / 2 - 80, y + 46, W / 2 + 80, y + 58], fill=BRAND["coral"])
    card_y = y + 120
    sfnt, slines = fit(d, pin["sub"], "medium", W - 260, 44, 32, 6)
    card_h = int(sfnt.size * 1.35) * len(slines) + 110
    d.rounded_rectangle([80, card_y, W - 80, card_y + card_h], radius=36, fill=BRAND["cream"])
    text_block(d, 130, card_y + 55, slines, sfnt, BRAND["ink"], spacing=1.35)
    footer(d, BRAND["deep"], BRAND["white"], BRAND["coral"])
    return img


def flow(pin):
    img = Image.new("RGB", (W, H), BRAND["cream"])
    d = ImageDraw.Draw(img)
    top = header(img, d, pin, BRAND["teal"], BRAND["white"], BRAND["coral"])
    items = pin["items"]
    gap = 70
    box_h = (H - 150 - top - 100 - gap * (len(items) - 1)) / len(items)
    box_h = min(box_h, 170)
    total = box_h * len(items) + gap * (len(items) - 1)
    y = top + (H - 150 - top - total) / 2
    colours = [BRAND["white"], BRAND["white"], BRAND["white"], BRAND["gold"]]
    for i, item in enumerate(items):
        d.rounded_rectangle([110, y, W - 110, y + box_h], radius=30, fill=colours[min(i, 3)], outline=BRAND["teal"], width=4)
        fnt, lines = fit(d, item, "bold", W - 300, 46, 30, 2)
        bh = int(fnt.size * 1.15) * len(lines)
        text_block(d, 150, y + (box_h - bh) / 2, lines, fnt, BRAND["deep"], spacing=1.15, align="center", box_w=W - 300)
        if i < len(items) - 1:
            ax, ay = W / 2, y + box_h + 10
            d.line([(ax, ay), (ax, ay + gap - 26)], fill=BRAND["coral"], width=8)
            d.polygon([(ax - 22, ay + gap - 34), (ax + 22, ay + gap - 34), (ax, ay + gap - 8)], fill=BRAND["coral"])
        y += box_h + gap
    footer(d, BRAND["deep"], BRAND["white"], BRAND["coral"])
    return img


def load_image(url: str):
    if not url:
        return None
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0 (PinStudio)"})
        r.raise_for_status()
        return Image.open(io.BytesIO(r.content)).convert("RGB")
    except Exception:
        return None


def photo(pin, image=None):
    """Product photo on top, headline band below. Falls back to the hero layout without an image."""
    if image is None:
        return hero({**pin, "sub": pin.get("sub") or pin.get("headline", "")})
    img = Image.new("RGB", (W, H), BRAND["cream"])
    d = ImageDraw.Draw(img)
    pic = ImageOps.fit(image, (W, 900), method=Image.LANCZOS)
    img.paste(pic, (0, 0))
    d.rectangle([0, 900, W, H - 150], fill=BRAND["teal"])
    if pin.get("kicker"):
        pill(d, 70, 850, pin["kicker"], BRAND["gold"], BRAND["deep"], size=32)
    fnt, lines = fit(d, pin["headline"], "display", W - 140, 96, 60, 3)
    block = int(fnt.size * 1.06) * len(lines)
    text_block(d, 70, 900 + (450 - block) / 2 + 10, lines, fnt, BRAND["white"], spacing=1.06)
    footer(d, BRAND["deep"], BRAND["white"], BRAND["coral"], cta=BRAND["product_cta"])
    return img


LAYOUTS = {"hero": hero, "statement": statement, "flow": flow,
           "checklist": lambda p: list_layout(p, "tick"), "mistakes": lambda p: list_layout(p, "cross"),
           "steps": lambda p: list_layout(p, "number")}


def render_pin(pin: dict, brand: dict, image=None, cta: str = None):
    set_brand(brand)
    if cta:
        BRAND["cta"] = cta
    if pin["layout"] == "photo":
        return photo(pin, image)
    layout = LAYOUTS.get(pin["layout"], hero)
    if pin["layout"] in ("hero", "statement") and not pin.get("sub"):
        pin = {**pin, "sub": pin.get("title", "")}
    return layout(pin)
