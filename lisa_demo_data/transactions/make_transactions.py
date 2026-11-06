#!/usr/bin/env python3
"""Lisa's card transactions as a bank-data connection would deliver them, and the little that leaves her phone.

Apps like Rocket Money read spending through bank-data aggregators such as Plaid; Rocket Money itself
has no public API. This file mimics that feed: on_phone.json holds every charge (merchant, amount,
time, Plaid-style category) and never leaves the phone. The on-device filter below shares only
restaurant, beer/wine/liquor-store and pharmacy charges, with the amount rounded to a range and the
time reduced to "evening or not"; shared.json is that output, and the only file the agent reads.

    .venv/bin/python lisa_demo_data/transactions/make_transactions.py
"""
import json
import random
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import generate_lisa_data as g  # noqa: E402  (reuses Lisa's life; importing generates nothing)

TZ = ZoneInfo("America/Los_Angeles")
SHARE = {  # Plaid-style detailed category -> what the agent may see
    "FOOD_AND_DRINK_RESTAURANT": "restaurant",
    "FOOD_AND_DRINK_BEER_WINE_AND_LIQUOR": "beer_wine_liquor",
    "MEDICAL_PHARMACIES_AND_SUPPLEMENTS": "pharmacy",
}
RANGES = [(25, "under $25"), (50, "$25–50"), (100, "$50–100"), (150, "$100–150"), (250, "$150–250"), (10**9, "$250+")]


def share_on_device(t: dict) -> dict | None:
    """The phone-side filter: None = this charge never leaves the phone."""
    kind = SHARE.get(t["personal_finance_category"]["detailed"])
    if not kind:
        return None
    when = datetime.fromisoformat(t["authorized_datetime"]) if t["authorized_datetime"] else None
    return {"id": t["transaction_id"], "date": t["date"], "merchant": t["merchant_name"], "category": kind,
            "amount_range": next(label for cap, label in RANGES if t["amount"] < cap),
            "evening": bool(when and when.hour >= 17), "channel": t["payment_channel"]}


def main():
    rng = random.Random(23)
    emails = json.loads((HERE.parent / "emails/emails.json").read_text())["messages"]
    totals = {}
    for m in emails:
        if m["subject"].startswith("Your receipt from "):
            if (tot := re.search(r"^Total\s+\$([\d,.]+)", m["body_text"], re.M)):
                totals[(m["date"][:10], m["from"]["name"].removesuffix(" via Tabbit"))] = float(tot.group(1).replace(",", ""))
    rows = []

    def add(day: str, hm: str | None, merchant: str, amount: float, primary: str, detailed: str, channel: str = "in store"):
        when = datetime.fromisoformat(f"{day}T{hm}").replace(tzinfo=TZ).isoformat(timespec="minutes") if hm else None
        rows.append({"transaction_id": f"tx_{len(rows) + 1:04d}", "account_id": "acct_visa_4417", "date": day, "authorized_datetime": when,
                     "name": merchant.upper(), "merchant_name": merchant, "amount": round(amount, 2), "iso_currency_code": "USD",
                     "payment_channel": channel, "pending": False,
                     "personal_finance_category": {"primary": primary, "detailed": detailed, "confidence_level": "HIGH"}})

    for day, key, *_ in g.DINNERS:                                  # every dinner out was paid by card
        name = g.RESTAURANTS[key][0]
        add(day, f"21:{rng.randint(5, 55):02d}", name, totals.get((day, name)) or rng.uniform(70, 160), "FOOD_AND_DRINK", "FOOD_AND_DRINK_RESTAURANT")
    for day in ("2026-07-25", "2026-08-29", "2026-09-26"):           # a bottle on the way home: no email trail at all
        add(day, f"18:{rng.randint(5, 40):02d}", "Grand Lake Wine & Spirits", rng.uniform(18, 34), "FOOD_AND_DRINK", "FOOD_AND_DRINK_BEER_WINE_AND_LIQUOR")
    for day in ("2026-07-08", "2026-08-07", "2026-09-09", "2026-10-08"):
        add(day, None, "Cellar Door Wine Club", 89.00, "FOOD_AND_DRINK", "FOOD_AND_DRINK_BEER_WINE_AND_LIQUOR", "online")
    for day, hm, amt in (("2026-08-22", "18:40", 17.14), ("2026-09-04", "17:48", 15.0), ("2026-10-03", "11:20", 15.0), ("2026-11-02", "12:10", 15.0)):
        add(day, hm, "Harbor Pharmacy", amt, "MEDICAL", "MEDICAL_PHARMACIES_AND_SUPPLEMENTS")
    # everything else: stays on the phone
    d = g.FIRST_EVENING
    while d <= g.LAST_EVENING:
        ds = d.isoformat()
        if d.weekday() < 5 and d not in g.TRAVEL_NIGHTS and rng.random() < 0.55:
            add(ds, f"08:{rng.randint(5, 50):02d}", "Blue Bottle Kiosk", rng.uniform(4.5, 7.5), "FOOD_AND_DRINK", "FOOD_AND_DRINK_COFFEE")
        if d.weekday() < 5 and rng.random() < 0.12:
            add(ds, f"12:{rng.randint(5, 45):02d}", rng.choice(["Juniper Café", "Noodle Bar 88", "Green Fork"]), rng.uniform(14, 24),
                "FOOD_AND_DRINK", "FOOD_AND_DRINK_RESTAURANT")
        if d.weekday() == 5 and rng.random() < 0.5:
            add(ds, f"10:{rng.randint(5, 55):02d}", "Lakeshore Gas", rng.uniform(42, 61), "TRANSPORTATION", "TRANSPORTATION_GAS")
        if d.day == 1:
            add(ds, None, "Courtside Tennis Club", 145.0, "PERSONAL_CARE", "PERSONAL_CARE_GYMS_AND_FITNESS_CENTERS", "other")
        if d.day == 12:
            add(ds, None, "EastBay Power", rng.uniform(88, 140), "RENT_AND_UTILITIES", "RENT_AND_UTILITIES_GAS_AND_ELECTRICITY", "other")
        if d.day == 17:
            add(ds, None, "Streamly", 22.99, "ENTERTAINMENT", "ENTERTAINMENT_TV_AND_MOVIES", "online")
        d += timedelta(days=1)
    for ds in ("2026-07-12", "2026-07-19", "2026-08-02", "2026-08-09", "2026-08-23", "2026-08-30", "2026-09-13", "2026-09-20",
               "2026-10-04", "2026-10-11", "2026-10-25", "2026-11-01"):
        add(ds, "11:05", "FreshCart", rng.uniform(85, 165), "FOOD_AND_DRINK", "FOOD_AND_DRINK_GROCERIES", "online")
    for ds, item, amt in (("2026-07-14", "Parcelly", 54.99), ("2026-08-05", "Parcelly", 23.47), ("2026-08-12", "Parcelly", 32.99),
                          ("2026-08-20", "Parcelly", 44.0), ("2026-09-01", "Parcelly", 39.95), ("2026-09-21", "Parcelly", 18.99), ("2026-10-06", "Parcelly", 29.99)):
        add(ds, "21:10", item, amt, "GENERAL_MERCHANDISE", "GENERAL_MERCHANDISE_ONLINE_MARKETPLACES", "online")
    add("2026-09-24", "14:03", "Bayline Air", 286.40, "TRAVEL", "TRAVEL_FLIGHTS", "online")
    add("2026-10-16", "10:52", "The Marlowe Seattle", 512.88, "TRAVEL", "TRAVEL_LODGING")
    add("2026-09-14", "19:30", "Bay Strikers U13", 120.0, "GENERAL_SERVICES", "GENERAL_SERVICES_EDUCATION", "online")

    rows.sort(key=lambda t: (t["date"], t["authorized_datetime"] or ""))
    shared = [s for t in rows if (s := share_on_device(t))]
    (HERE / "on_phone.json").write_text(json.dumps({
        "note": "Raw feed on the phone (Plaid-style shape, synthetic). Never uploaded.", "transactions": rows}, indent=1, ensure_ascii=False) + "\n")
    (HERE / "shared.json").write_text(json.dumps({
        "rule": "only restaurant, beer/wine/liquor and pharmacy charges leave the phone; amount as a range; time as evening or not",
        "shared": shared, "kept_on_phone": len(rows) - len(shared)}, indent=1, ensure_ascii=False) + "\n")
    print(f"{len(rows)} charges on the phone; {len(shared)} shared, {len(rows) - len(shared)} kept on the phone")


if __name__ == "__main__":
    main()
