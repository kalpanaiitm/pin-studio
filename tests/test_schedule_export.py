import csv
from datetime import date, datetime

from pinstudio.export import export_batch, read_history
from pinstudio.render import render_pin
from pinstudio.schedule import plan


def make(link, n):
    return [{"link": link, "title": f"{link} {i}"} for i in range(n)]


def test_ten_a_day_max_three_per_link(settings):
    pins = make("a", 15) + make("b", 15)
    done, left = plan(pins, settings, today=date(2026, 10, 7))
    by_day = {}
    for p in done:
        t = datetime.fromisoformat(p["publish_local"])
        by_day.setdefault(t.date(), []).append(p)
        assert 8 <= t.hour <= 21
    assert all(len(v) <= 10 for v in by_day.values())
    for day, items in by_day.items():
        for link in ("a", "b"):
            assert sum(1 for p in items if p["link"] == link) <= 3
    assert min(by_day) == date(2026, 10, 8) and not left


def test_respects_14_day_horizon(settings):
    done, left = plan(make("a", 60), settings, today=date(2026, 10, 7))
    assert len(done) == 42 and len(left) == 18      # 3 per link per day x 14 days


def test_continues_after_history(settings):
    first, _ = plan(make("a", 3), settings, today=date(2026, 10, 7))
    second, _ = plan(make("b", 10), settings, history=first, today=date(2026, 10, 7))
    taken = {p["publish_local"] for p in first}
    assert not taken & {p["publish_local"] for p in second}


def test_utc_conversion_in_british_summer_time(settings):
    done, _ = plan(make("a", 1), settings, today=date(2026, 7, 1))
    assert done[0]["publish_local"].endswith("08:00:00+01:00") and done[0]["publish_utc"] == "2026-07-02T07:00:00"


def test_export_writes_csv_images_and_history(tmp_path, settings):
    pins = [{"layout": "hero", "kicker": "GUIDE", "headline": "How to Sell on Vinted UK", "sub": "Step by step",
             "items": [], "title": "How to Sell on Vinted UK", "description": "d", "alt": "a", "board": "Vinted & Reselling Tips UK",
             "filename": "sell-on-vinted-uk", "keywords": ["sell on vinted uk", "vinted tips"], "link": "https://x/"}]
    plan(pins, settings, today=date(2026, 10, 7))
    images = [render_pin(p, settings["brand"]) for p in pins]
    folder, zip_path, csvs = export_batch(pins, images, settings, tmp_path, tmp_path / "h.csv", "2026/10", "vinted")
    rows = list(csv.DictReader(csvs[0].open(encoding="utf-8")))
    assert list(rows[0]) == settings["pinterest_csv"]["columns"]
    assert rows[0]["Media URL"] == "https://moneysavvyuk.com/wp-content/uploads/2026/10/sell-on-vinted-uk.png"
    assert rows[0]["Publish date"] == "2026-10-08T07:00:00" and rows[0]["Keywords"] == "sell on vinted uk, vinted tips"
    assert (folder / "sell-on-vinted-uk.png").exists() and zip_path.exists()
    assert read_history(tmp_path / "h.csv")[0]["title"] == "How to Sell on Vinted UK"


def test_every_layout_renders(settings, product):
    from pinstudio.render import load_image  # noqa: F401
    for layout, items in [("hero", []), ("statement", []), ("checklist", ["a b c"] * 6), ("mistakes", ["x y"] * 4),
                          ("steps", ["s t"] * 5), ("flow", ["f g"] * 4), ("photo", [])]:
        img = render_pin({"layout": layout, "kicker": "TEST", "headline": "A headline that is fairly long here",
                          "sub": "A subtitle", "items": items, "title": "t"}, settings["brand"])
        assert img.size == (1000, 1500)


def test_one_posts_pins_are_spread_through_the_day(settings):
    done, _ = plan(make("a", 3), settings, today=date(2026, 10, 7))
    hours = sorted(datetime.fromisoformat(p["publish_local"]).hour for p in done)
    assert hours[0] == 8 and hours[-1] >= 15        # not all crammed into the morning


def test_twenty_a_day_needs_seven_posts(settings):
    settings["schedule"]["pins_per_day"] = 20
    pins = [p for i in range(7) for p in make(f"post{i}", 15)]
    done, left = plan(pins, settings, today=date(2026, 10, 7))
    first_day = [p for p in done if p["publish_local"].startswith("2026-10-08")]
    assert len(first_day) == 20 and all(sum(1 for p in first_day if p["link"] == f"post{i}") <= 3 for i in range(7))


def test_bulk_pipeline_two_posts(settings, page, product, monkeypatch, tmp_path):
    from pinstudio import batch
    from pinstudio.llm import LLM
    pages = {page.url: page, product.url: product}
    monkeypatch.setattr(batch, "fetch_page", lambda url: pages[url])
    monkeypatch.setattr(batch, "load_image", lambda url: None)
    llm = LLM(settings)
    pins = []
    for url in pages:
        _, _, made = batch.build_for_url(url, settings, llm, [p["title"] for p in pins], 8)
        pins += made
    paths_ = {"output": tmp_path, "history": tmp_path / "h.csv"}
    exp = batch.schedule_and_export(pins, settings, paths_, [], "2026/10", "bulk", today=date(2026, 10, 7))
    assert len(exp["done"]) == 16 and exp["left"] == 0
    day1 = [p for p in exp["done"] if p["publish_local"].startswith("2026-10-08")]
    assert {p["link"] for p in day1} == set(pages)          # both posts appear on day one
