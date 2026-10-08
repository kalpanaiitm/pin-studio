"""Shared steps for one or many links: build pins, then schedule, render and export them together."""
from datetime import date

from pinstudio.export import export_batch, image_hash
from pinstudio.fetch import fetch_page
from pinstudio.generate import make_pins, recheck, suggest_keywords
from pinstudio.render import load_image, render_pin
from pinstudio.schedule import plan


def build_for_url(url, settings, llm, history_titles=(), n=None):
    """Read a page, pick keywords and make its pins (no manual review)."""
    page = fetch_page(url)
    kw = suggest_keywords(page, settings, llm)
    pins = make_pins(page, kw, settings, llm, n)
    recheck(pins, page, kw, settings, list(history_titles))
    for p in pins:
        p["_kind"] = page.kind
        p["_image_url"] = page.image_url if page.kind == "product" else ""
    return page, kw, pins


def capacity(settings):
    cfg = settings["schedule"]
    return cfg["pins_per_day"] * cfg["horizon_days"]


def schedule_and_export(pins, settings, paths_, history, upload_month, batch_name, today=None):
    """Schedule all pins together (posts interleaved), render full-size images and write the zip + CSV."""
    done, left = plan([dict(p) for p in pins], settings, history=history, today=today or date.today())
    photos = {}
    images = []
    for p in done:
        url = p.get("_image_url") or ""
        if p["layout"] == "photo" and url and url not in photos:
            photos[url] = load_image(url)
        cta = settings["brand"]["product_cta"] if p.get("_kind") == "product" else settings["brand"]["cta"]
        images.append(render_pin(p, settings["brand"], image=photos.get(url) if p["layout"] == "photo" else None, cta=cta))
    # Guardrail: never schedule a picture that was scheduled before (or twice in this batch), even under another name.
    seen = {h.get("image_hash") for h in history if h.get("image_hash")}
    kept, kept_imgs, blocked = [], [], []
    for p, img in zip(done, images):
        h = image_hash(img)
        if h in seen:
            blocked.append(p["title"])
            continue
        seen.add(h)
        kept.append(p)
        kept_imgs.append(img)
    folder, zip_path, csvs = export_batch(kept, kept_imgs, settings, paths_["output"], paths_["history"], upload_month, batch_name)
    return {"zip": str(zip_path), "folder": str(folder), "done": kept, "left": len(left), "csvs": [str(c) for c in csvs],
            "blocked_duplicates": blocked}
