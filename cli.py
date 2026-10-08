"""Command-line version (no review screen):
    python cli.py <url> [<url> ...] [--month 2026/10] [--pins 15] [--per-day 15]
Makes pins for every link, schedules them together and writes one zip + Pinterest CSV."""
import argparse
from datetime import date

from pinstudio.batch import build_for_url, capacity, schedule_and_export
from pinstudio.config import load_settings, paths
from pinstudio.export import read_history
from pinstudio.llm import LLM

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("urls", nargs="+")
    ap.add_argument("--month", help="WordPress upload month, e.g. 2026/10 (default: this month)")
    ap.add_argument("--pins", type=int, help="pins per post")
    ap.add_argument("--per-day", type=int, help="pins per day (default from settings / app)")
    a = ap.parse_args()
    S, P = load_settings(), paths()
    if a.per_day:
        S["schedule"]["pins_per_day"] = a.per_day
    llm = LLM(S)
    history = read_history(P["history"])
    titles = [h["title"] for h in history]
    pins = []
    for url in a.urls:
        try:
            page, kw, made = build_for_url(url, S, llm, titles + [p["title"] for p in pins], a.pins)
        except Exception as e:
            print(f"SKIPPED {url}: {e}")
            continue
        bad = [p for p in made if any(x["level"] == "error" for x in p["issues"])]
        print(f"{page.title[:60]}: {len(made)} pins, keyword '{kw['main_keyword']}'" + (f", {len(bad)} left out (flagged)" if bad else ""))
        for p in bad:
            print("   ! " + p["title"] + ": " + "; ".join(x["msg"] for x in p["issues"] if x["level"] == "error"))
        pins += [p for p in made if p not in bad]
    print(f"\n{len(pins)} pins ready; schedule holds up to {capacity(S)} at {S['schedule']['pins_per_day']} a day.")
    if pins:
        exp = schedule_and_export(pins, S, P, history, a.month or date.today().strftime("%Y/%m"), f"cli-{len(a.urls)}-posts")
        print(f"{len(exp['done'])} scheduled, {exp['left']} left over.\nFiles: {exp['zip']}")
    print(f"AI cost: ${llm.cost_usd:.4f}")
