"""Command-line version: python cli.py <url> [--month 2026/10] [--pins 15]
Makes pins, schedules them and writes the zip without the review screen."""
import argparse

from pinstudio.config import load_settings, paths
from pinstudio.export import export_batch, read_history
from pinstudio.fetch import fetch_page
from pinstudio.generate import make_pins, recheck, suggest_keywords
from pinstudio.llm import LLM
from pinstudio.render import load_image, render_pin
from pinstudio.schedule import plan

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--month", help="WordPress upload month, e.g. 2026/10 (default: this month)")
    ap.add_argument("--pins", type=int)
    a = ap.parse_args()
    S, P = load_settings(), paths()
    llm = LLM(S)
    page = fetch_page(a.url)
    kw = suggest_keywords(page, S, llm)
    print(f"Main keyword: {kw['main_keyword']}\nRelated: {', '.join(kw['related_keywords'])}")
    history = read_history(P["history"])
    pins = recheck(make_pins(page, kw, S, llm, a.pins), page, kw, S, [h["title"] for h in history])
    for i, p in enumerate(pins, 1):
        flags = "; ".join(x["msg"] for x in p["issues"])
        print(f"{i:2}. [{p['layout']}] {p['title']}" + (f"\n    ! {flags}" if flags else ""))
    done, left = plan(pins, S, history=history)
    photo = load_image(page.image_url) if page.kind == "product" else None
    cta = S["brand"]["cta"] if page.kind == "blog" else S["brand"]["product_cta"]
    images = [render_pin(p, S["brand"], image=photo if p["layout"] == "photo" else None, cta=cta) for p in done]
    from datetime import date
    folder, zip_path, _ = export_batch(done, images, S, P["output"], P["history"], a.month or date.today().strftime("%Y/%m"),
                                       "-".join(done[0]["filename"].split("-")[:4]) if done else "batch")
    print(f"\n{len(done)} pins scheduled, {len(left)} left over. Files: {zip_path}\nAI cost: ${llm.cost_usd:.4f}")
