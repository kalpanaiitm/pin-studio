"""Spread pins over days: N per day within posting hours, max K per link per day, posts interleaved,
continuing after anything already scheduled in the history log."""
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo


def daily_slots(day: date, per_day: int, start: str, end: str, tz: ZoneInfo):
    h1, m1 = map(int, start.split(":"))
    h2, m2 = map(int, end.split(":"))
    a = datetime.combine(day, time(h1, m1), tz)
    b = datetime.combine(day, time(h2, m2), tz)
    if per_day == 1:
        return [a]
    step = (b - a) / (per_day - 1)
    slots = []
    for i in range(per_day):
        t = a + step * i
        t = t.replace(minute=(t.minute // 5) * 5, second=0, microsecond=0)   # tidy times like 09:25
        slots.append(t)
    return slots


def spread_order(n: int):
    """Order slot indices so the first few picks are spread across the day (e.g. 08:00, 12:20, 16:40)."""
    from math import gcd
    stride = max(1, round(n / 3))
    while gcd(stride, n) != 1:
        stride += 1
    return [(i * stride) % n for i in range(n)]


def interleave(pins):
    """Round-robin across links so one post's pins don't all land together."""
    by_link = defaultdict(list)
    for p in pins:
        by_link[p["link"]].append(p)
    queues, out = list(by_link.values()), []
    while any(queues):
        for q in queues:
            if q:
                out.append(q.pop(0))
    return out


def plan(pins, settings, history=(), today: date = None, start: date = None):
    """Assign 'publish_local' and 'publish_utc' to each pin. Returns (scheduled, unscheduled)."""
    cfg = settings["schedule"]
    tz = ZoneInfo(cfg["timezone"])
    today = today or datetime.now(tz).date()
    horizon = today + timedelta(days=cfg["horizon_days"])
    start = max(start or today + timedelta(days=1), today + timedelta(days=1))
    used = defaultdict(set)
    per_link = defaultdict(int)
    for h in history:
        if h.get("publish_local"):
            t = datetime.fromisoformat(h["publish_local"])
            used[t.date()].add(t.strftime("%H:%M"))
            per_link[(t.date(), h["link"])] += 1
    queue = interleave(pins)
    scheduled, day = [], start
    while queue and day <= horizon:
        slots = daily_slots(day, cfg["pins_per_day"], cfg["day_start"], cfg["day_end"], tz)
        free = [slots[i] for i in spread_order(len(slots)) if slots[i].strftime("%H:%M") not in used[day]]
        for slot in free:
            pick = next((p for p in queue if per_link[(day, p["link"])] < cfg["max_per_link_per_day"]), None)
            if pick is None:
                break
            queue.remove(pick)
            per_link[(day, pick["link"])] += 1
            used[day].add(slot.strftime("%H:%M"))
            pick["publish_local"] = slot.isoformat()
            pick["publish_utc"] = slot.astimezone(timezone.utc).strftime(settings["pinterest_csv"]["date_format"])
            scheduled.append(pick)
        day += timedelta(days=1)
    scheduled.sort(key=lambda p: p["publish_local"])
    return scheduled, queue
