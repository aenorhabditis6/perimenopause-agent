#!/usr/bin/env python3
"""What an on-device location app would upload for Lisa: visits to restaurants and bars only.

The app (assumed, not built) tracks visits and classifies each place on the phone, the way Google
Maps already labels places. Only a visit to a place of type restaurant or bar leaves the phone, as
place name + type + arrival and departure time; no coordinates. Everything else it sees (home, work,
friends' homes, the clinic, the pharmacy, the tennis club) stays on the phone; on_device_summary.json
counts those so the demo can show what was held back.

    .venv/bin/python lisa_demo_data/places/make_visits.py
"""
import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import generate_lisa_data as g  # noqa: E402  (reuses Lisa's dinner list; importing generates nothing)

TZ = ZoneInfo("America/Los_Angeles")
PLACE_TYPE = {"rosemary": "bar", "gilded": "bar"}           # a wine bar and a gastropub; the rest are restaurants
EXTRA = [  # evening visits from calendar events held at restaurants
    ("2026-09-17", "Lakeside Grill", "restaurant", "18:05", "21:10"),
    ("2026-10-15", "Elliott Bay Kitchen", "restaurant", "18:10", "20:05"),
]
LUNCHES = ["Juniper Café", "Noodle Bar 88", "Green Fork", "Taqueria Sol"]   # daytime visits; the analysis ignores them


def at(day: str, hm: str) -> datetime:
    return datetime.fromisoformat(f"{day}T{hm}").replace(tzinfo=TZ)


def main():
    rng = random.Random(11)
    key = json.loads((HERE.parent / "truth/email_expected_events.json").read_text())["expected"]
    times = {(e["event_date"], e["merchant"], e["category"]): e.get("event_time") for e in key if e.get("category", "").startswith("restaurant_")}
    visits = []
    for day, rkey, *_ in g.DINNERS:
        name = g.RESTAURANTS[rkey][0]
        seat = times.get((day, name, "restaurant_reservation")) or "19:00"
        paid = times.get((day, name, "restaurant_receipt"))
        arrive = at(day, seat) - timedelta(minutes=rng.randint(2, 9))
        leave = at(day, paid) + timedelta(minutes=rng.randint(6, 14)) if paid else arrive + timedelta(minutes=rng.randint(125, 170))
        visits.append((day, name, PLACE_TYPE.get(rkey, "restaurant"), arrive, leave))
    for day, name, kind, a, b in EXTRA:
        visits.append((day, name, kind, at(day, a), at(day, b)))
    workdays = [d for d in g.evenings() if d.weekday() < 5 and d not in g.TRAVEL_NIGHTS]
    for d in sorted(rng.sample(workdays, 9)):
        a = at(d.isoformat(), f"12:{rng.randint(5, 25):02d}")
        visits.append((d.isoformat(), rng.choice(LUNCHES), "restaurant", a, a + timedelta(minutes=rng.randint(35, 55))))
    visits.sort(key=lambda v: v[3])
    rows = [{"id": f"v{k:03d}", "place": name, "place_type": kind, "arrived_at": a.isoformat(timespec="minutes"),
             "left_at": b.isoformat(timespec="minutes")} for k, (day, name, kind, a, b) in enumerate(visits, 1)]
    (HERE / "visits.json").write_text(json.dumps({
        "source": "on-device location app (assumed; synthetic data)",
        "rule": "only visits to places classified restaurant or bar leave the phone: place name, type, arrival, departure; no coordinates",
        "visits": rows}, indent=1, ensure_ascii=False) + "\n")
    held = {"home": 121, "work": 63, "kids' schools": 48, "tennis club": 19, "friends' homes": 7, "pharmacy": 4,
            "medical office": 1, "airport": 2, "hotel": 2, "shops and errands": 38}
    (HERE / "on_device_summary.json").write_text(json.dumps({
        "note": "Visits the location app saw but never uploaded (counts only; illustrative)",
        "kept_on_phone": held, "total_kept": sum(held.values())}, indent=1) + "\n")
    print(f"{len(rows)} restaurant/bar visits uploaded; {sum(held.values())} other visits kept on the phone")


if __name__ == "__main__":
    main()
