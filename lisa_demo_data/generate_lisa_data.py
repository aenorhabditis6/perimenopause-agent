#!/usr/bin/env python3
"""Synthetic demo data for "Lisa Hartley", a fictional 46-year-old.

Everything is made up: the person, every merchant and every address (all on
the reserved .example domain). One seed drives everything, so the same seed
always produces the same files.

    python3 generate_lisa_data.py

Writes profile/, emails/, calendar/, wearables/, app_state/ and truth/ next to
this script. truth/ is the answer key for the team; never feed it to the agent.
"""
from __future__ import annotations

import csv
import html
import json
import math
import os
import random
import uuid
from datetime import date, datetime, time, timedelta, timezone
from email.message import EmailMessage
from email.utils import format_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SEED = int(os.environ.get("LISA_SEED", 94))
TZ = ZoneInfo("America/Los_Angeles")
OUT = Path(os.environ.get("LISA_OUT", Path(__file__).resolve().parent))
FIRST_EVENING = date(2026, 7, 6)
LAST_EVENING = date(2026, 11, 4)        # the last sleep ends on the morning of Nov 5
TREATMENT_START = date(2026, 9, 4)      # first evening on the new prescription
SCHOOL_STARTS = date(2026, 8, 12)
LEARNING_WINDOW = (date(2026, 8, 10), date(2026, 9, 18))  # when the agent asks one-tap questions
NS = uuid.UUID("6f1c2a9e-3b0d-4c55-9a51-0d7c3e2b8a10")

LISA = ("Lisa Hartley", "lisa.hartley@mail.example")

rng = random.Random(SEED)


def uid(*parts) -> str:
    return str(uuid.uuid5(NS, "|".join(map(str, parts))))


def at(d: date, hh: int, mm: int = 0) -> datetime:
    return datetime.combine(d, time(hh, mm), tzinfo=TZ)


def iso(t: datetime) -> str:
    return t.isoformat(timespec="seconds")


def wall(d: date, minutes: int) -> datetime:
    """Local wall-clock time `minutes` after midnight of d (may run past midnight)."""
    return (datetime.combine(d, time(0)) + timedelta(minutes=minutes)).replace(tzinfo=TZ)


def plus(t: datetime, minutes: float) -> datetime:
    """Real elapsed time (correct across the Nov 1 DST change)."""
    return (t.astimezone(timezone.utc) + timedelta(minutes=minutes)).astimezone(TZ)


def mins_between(a: datetime, b: datetime) -> int:
    return round((b.astimezone(timezone.utc) - a.astimezone(timezone.utc)).total_seconds() / 60)


def D(s: str) -> date:
    return date.fromisoformat(s)


def evenings():
    d = FIRST_EVENING
    while d <= LAST_EVENING:
        yield d
        d += timedelta(days=1)


def nice_date(d: date) -> str:
    return f"{d:%A}, {d:%B} {d.day}, {d.year}"


def short_date(d: date) -> str:
    return f"{d:%a}, {d:%b} {d.day}"


def clock(t: datetime) -> str:
    h = t.hour % 12 or 12
    return f"{h}:{t.minute:02d} {'AM' if t.hour < 12 else 'PM'}"


def clip(x, lo, hi):
    return max(lo, min(hi, x))


# ---------------------------------------------------------------------------
# Lisa's life: the ground truth every file is generated from
# ---------------------------------------------------------------------------

RESTAURANTS = {
    "rosemary": ("Rosemary & Vine", "4120 Piedmont Ave, Oakland, CA", "rosemaryandvine.example"),
    "spice": ("Spice Route Thai", "2289 Telegraph Ave, Oakland, CA", "spiceroute.example"),
    "gilded": ("The Gilded Tap", "510 Grand Ave, Oakland, CA", "gildedtap.example"),
    "sora": ("Sora Sushi", "3317 Lakeshore Ave, Oakland, CA", "sorasushi.example"),
    "mesa": ("Mesa Verde Cantina", "1820 Fruitvale Ave, Oakland, CA", "mesaverde.example"),
    "lucca": ("Osteria Lucca", "5940 College Ave, Oakland, CA", "osterialucca.example"),
    "harborview": ("Harborview Oyster Bar", "1101 Alaskan Way, Seattle, WA", "harborview-oyster.example"),
}

# (item, unit price, is_alcohol)
MENUS = {
    "rosemary": {"drinks": [("Glass — Barbera d'Asti", 15.0)], "food": [("Burrata", 16.0), ("Wild mushroom risotto", 28.0), ("Branzino", 34.0), ("Tiramisu", 12.0)], "soft": [("Sparkling water (bottle)", 7.0)]},
    "spice": {"drinks": [("Singha beer", 8.0)], "food": [("Pad see ew", 17.0), ("Green curry", 19.0), ("Kids' pad thai", 12.0), ("Mango sticky rice", 11.0)], "soft": [("Thai iced tea", 6.0)]},
    "gilded": {"drinks": [("Glass — Sauvignon Blanc", 14.0)], "food": [("Fish & chips", 24.0), ("Truffle fries", 11.0), ("Little gem salad", 15.0)], "soft": [("House lemonade", 6.0)]},
    "sora": {"drinks": [("Junmai sake (carafe)", 18.0)], "food": [("Omakase set", 68.0), ("Miso soup", 5.0)], "soft": [("Green tea", 4.0)]},
    "mesa": {"drinks": [("Margarita (classic)", 14.0)], "food": [("Tacos al pastor", 18.0), ("Guacamole & chips", 13.0), ("Enchiladas verdes", 21.0)], "soft": [("Agua fresca", 6.0)]},
    "lucca": {"drinks": [("Bottle — Chianti Classico", 62.0)], "food": [("Cacio e pepe", 24.0), ("Grilled octopus", 22.0), ("Panna cotta", 11.0)], "soft": [("Sparkling water (bottle)", 7.0)]},
    "harborview": {"drinks": [("Glass — Albariño", 15.0)], "food": [("Oysters (dozen)", 42.0), ("Dungeness crab cakes", 26.0), ("Clam chowder", 12.0)], "soft": [("Iced tea", 5.0)]},
}

# evening, restaurant, she drank?, reservation email?, receipt email?, party size, with whom
DINNERS = [
    ("2026-07-10", "rosemary", True, True, True, 2, "Mark"),
    ("2026-07-17", "spice", False, True, True, 4, "family"),
    ("2026-07-24", "gilded", True, False, True, 3, "Sarah & Jen"),
    ("2026-07-31", "sora", True, True, False, 2, "Mark"),
    ("2026-08-07", "mesa", True, True, True, 4, "the Parks"),
    ("2026-08-14", "lucca", True, True, True, 2, "Mark"),
    ("2026-08-21", "rosemary", True, True, False, 4, "Dana & Priyanka"),
    ("2026-08-26", "sora", False, True, False, 2, "a colleague"),
    ("2026-08-28", "spice", False, True, True, 4, "family"),
    ("2026-09-05", "gilded", True, False, True, 3, "Sarah & Jen"),
    ("2026-09-11", "mesa", True, True, True, 2, "Mark"),
    ("2026-09-18", "spice", False, True, True, 4, "family"),
    ("2026-09-25", "rosemary", True, True, True, 2, "Mark"),
    ("2026-10-02", "sora", True, True, False, 2, "Mark"),
    ("2026-10-09", "lucca", True, True, True, 4, "the Nguyens"),
    ("2026-10-14", "harborview", True, False, True, 3, "the client team"),
    ("2026-10-17", "rosemary", True, True, True, 2, "Mark"),
    ("2026-10-23", "gilded", True, False, True, 3, "Sarah & Jen"),
    ("2026-10-30", "mesa", True, True, True, 4, "family"),
    ("2026-11-03", "lucca", True, True, True, 2, "Mark"),
]

# evening, calendar title, location, start hour, end hour, she drank?
SOCIAL = [
    ("2026-07-08", "Book club @ Anna's", "Anna's place", 19, 21, False),
    ("2026-07-18", "BBQ at the Parks'", "the Parks' backyard", 17, 21, True),
    ("2026-08-08", "Dinner at ours — the Nguyens", "Home", 18, 22, True),
    ("2026-08-12", "Book club @ Anna's", "Anna's place", 19, 21, True),
    ("2026-08-22", "Girls' night @ Sarah's", "Sarah's place", 19, 23, True),
    ("2026-09-09", "Book club @ Anna's", "Anna's place", 19, 21, True),
    ("2026-09-17", "Team offsite dinner", "Lakeside Grill, Oakland", 18, 21, True),
    ("2026-10-03", "Girls' night @ Sarah's", "Sarah's place", 19, 23, True),
    ("2026-10-15", "Team dinner — Seattle workshop", "Seattle", 18, 20, False),
    ("2026-10-24", "Jen's 50th", "Jen's house, Piedmont", 19, 23, True),
]

# Wine at home with no trace anywhere (except a one-tap answer if the agent asks)
HOME_DRINKS = ["2026-07-11", "2026-07-25", "2026-08-01", "2026-08-15", "2026-08-29", "2026-09-12", "2026-09-26"]

SKIPPED_TENNIS = {D("2026-08-27"), D("2026-09-17"), D("2026-10-15")}
TENNIS_LESSONS = ["2026-07-18", "2026-08-01", "2026-08-29", "2026-09-19", "2026-10-24"]
TRAVEL_NIGHTS = {D("2026-10-14"), D("2026-10-15")}       # hotel nights in Seattle
EARLY_FLIGHT_EVE = D("2026-10-13")
LATE_RETURN_EVE = D("2026-10-16")

# Period start dates (logged by Lisa in iPhone Health / Cycle Tracking, a habit she already had)
PERIOD_STARTS = ["2026-01-05", "2026-02-02", "2026-03-01", "2026-03-29", "2026-04-27", "2026-05-21",
                 "2026-06-14", "2026-07-10", "2026-08-17", "2026-09-08", "2026-10-21"]
PERIOD_LENGTH_DAYS = [5, 5, 4, 5, 4, 4, 5, 6, 3, 5, 5]


def build_life():
    """Per-evening ground truth."""
    life = {d: {"alcohol": False, "alcohol_context": "", "dinner": None, "social": None,
                "tennis": False, "travel": d in TRAVEL_NIGHTS} for d in evenings()}
    for ev, key, drank, res, rec, party, who in DINNERS:
        d = D(ev)
        life[d]["dinner"] = {"key": key, "drank": drank, "reservation": res, "receipt": rec, "party": party, "with": who}
        if drank:
            life[d]["alcohol"], life[d]["alcohol_context"] = True, f"dinner at {RESTAURANTS[key][0]}"
    for ev, title, loc, h0, h1, drank in SOCIAL:
        d = D(ev)
        life[d]["social"] = {"title": title, "location": loc, "start": h0, "end": h1, "drank": drank}
        if drank:
            life[d]["alcohol"], life[d]["alcohol_context"] = True, title
    for ev in HOME_DRINKS:
        life[D(ev)]["alcohol"], life[D(ev)]["alcohol_context"] = True, "wine at home"
    for d in life:
        if d.weekday() == 3 and d not in SKIPPED_TENNIS:
            life[d]["tennis"] = True
    return life


def luteal_bump(d: date) -> float:
    """Small temperature rise in the second half of ovulatory (<=30 day) cycles."""
    starts = [D(s) for s in PERIOD_STARTS] + [D("2026-11-24")]
    for a, b in zip(starts, starts[1:]):
        if a <= d < b:
            if (b - a).days > 30:
                return 0.0           # long cycles here are anovulatory: no biphasic shift
            days_before_next = (b - d).days
            return 0.12 if days_before_next <= 12 else 0.0
    return 0.0


def p_night_heat(i: int, alcohol: bool) -> float:
    """Chance of a vasomotor night (night sweat + wake-up). i = days since the first evening."""
    t0 = (TREATMENT_START - FIRST_EVENING).days
    if i < 28:
        base, bump = 0.05 + 0.05 * i / 27, 0.20
    elif i < t0:
        base, bump = 0.22 + 0.16 * (i - 28) / (t0 - 29), 0.52
    else:
        k = min(1.0, (i - t0) / 21)
        base, bump = 0.38 + (0.05 - 0.38) * k, 0.52 - 0.30 * k
    return min(0.9, base + (bump if alcohol else 0.0))


# ---------------------------------------------------------------------------
# Nights: one latent night drives both the Oura and the Apple Health files
# ---------------------------------------------------------------------------

def gen_night(d: date, i: int, ctx: dict) -> dict:
    wake_day = d + timedelta(days=1)
    alcohol, tennis = ctx["alcohol"], ctx["tennis"]
    heat_p = p_night_heat(i, alcohol)
    heat = rng.random() < heat_p

    # bedtime (minutes after midnight of the evening date; >1440 = after midnight)
    wd = d.weekday()
    if d == EARLY_FLIGHT_EVE:
        bed = 22 * 60 + 5
    elif ctx["travel"]:
        bed = 23 * 60 + 5
    elif ctx["social"] and ctx["social"]["end"] >= 22:
        bed = ctx["social"]["end"] * 60 + 55
    elif d == LATE_RETURN_EVE:
        bed = 23 * 60 + 50
    elif ctx["dinner"]:
        bed = 23 * 60 + 15
    elif wd in (4, 5):
        bed = 23 * 60 + 25
    else:
        bed = 22 * 60 + 50
    bed += round(rng.gauss(0, 14))

    if wake_day == EARLY_FLIGHT_EVE + timedelta(days=1):
        wake = 24 * 60 + 4 * 60 + 40
    elif wake_day.weekday() >= 5:
        wake = 24 * 60 + 7 * 60 + 35 + round(rng.gauss(0, 18))
    elif d in TRAVEL_NIGHTS:
        wake = 24 * 60 + 6 * 60 + 40 + round(rng.gauss(0, 8))
    else:
        wake = 24 * 60 + (6 * 60 + 45 if wake_day < SCHOOL_STARTS else 6 * 60 + 20) + round(rng.gauss(0, 7))
    bedtime_start = wall(d, 5 * round(bed / 5))
    bedtime_end = wall(d, 5 * round(wake / 5))
    n = mins_between(bedtime_start, bedtime_end) // 5

    latency = clip(round(rng.gauss(3, 1)), 1, 5)
    phases = ["4"] * latency
    c = 0
    while len(phases) < n - 1:
        cyc = round(rng.gauss(19, 1.5))
        deep = clip(round(rng.gauss(5.5 - 1.8 * c, 1)), 0, 7)
        rem = clip(round(rng.gauss(2 + 1.3 * c, 1)), 1, 8)
        if alcohol and c < 2:
            rem = max(0, rem - 2)
        light = max(2, cyc - deep - rem)
        half = light // 2
        phases += ["2"] * half + ["1"] * deep + ["2"] * (light - half) + ["3"] * rem
        c += 1
    phases = phases[: n - 1] + ["4"]

    def epoch_of(minute_of_evening: int) -> int:
        return mins_between(bedtime_start, wall(d, minute_of_evening)) // 5

    blocks = []  # (start_epoch, length) of awakenings we insert
    if heat:
        start = epoch_of(24 * 60 + 140 + rng.randrange(0, 100))   # 02:20-04:00
        blocks.append((start, rng.randint(4, 9)))                   # 20-45 min
        if rng.random() < 0.3:
            blocks.append((start + rng.randint(14, 24), rng.randint(2, 3)))
    elif i >= 28 and rng.random() < 0.25:
        blocks.append((epoch_of(24 * 60 + 165 + rng.randrange(0, 40)), rng.randint(2, 3)))
    for _ in range(rng.randint(1, 2) + (1 if alcohol else 0)):
        blocks.append((rng.randrange(n // 2, n - 3), 1))
    for s, length in blocks:
        for k in range(max(latency + 1, s), min(n - 1, s + length)):
            phases[k] = "4"
    heat_block = blocks[0] if heat else None

    temp_dev = rng.gauss(0, 0.09) + luteal_bump(d) + (0.08 if alcohol else 0) + (rng.uniform(0.32, 0.6) if heat else 0)
    if i >= 28:
        temp_dev += 0.03

    rhr = 57 + (3.5 if alcohol else 0) + (1.5 if heat else 0) + rng.gauss(0, 1.2)
    hr, hrv, move = [], [], []
    hrv_base = 38 - (9 if alcohol else 0) - (4 if heat else 0) + rng.gauss(0, 3)
    for k, ph in enumerate(phases):
        frac = k / n
        v = rhr + 9 * math.exp(-frac * 6) + 2.5 * max(0.0, frac - 0.7) / 0.3
        if alcohol:
            v += 3 * (1 - frac)
        if ph == "4":
            v += rng.uniform(7, 13)
        if heat_block and heat_block[0] <= k < heat_block[0] + heat_block[1]:
            v += rng.uniform(14, 21) if k < heat_block[0] + 2 else rng.uniform(6, 10)
        hr.append(round(v + rng.gauss(0, 1.3)))
        h = hrv_base + {"1": 8, "2": 0, "3": -6, "4": -12}[ph] + rng.gauss(0, 5)
        hrv.append(max(8, round(h)))
        if ph == "1":
            move.append("1" * 10)
        elif ph in "23":
            move.append("".join(rng.choice("1111111112") for _ in range(10)))
        else:
            move.append("".join(rng.choice("2334") for _ in range(10)))
    for k in rng.sample(range(n), k=max(1, n // 60)):
        hr[k] = None          # the ring drops a few samples every night
    sleeping = [k for k, ph in enumerate(phases) if ph != "4"]
    hr_sleep = [hr[k] for k in sleeping if hr[k] is not None]
    hrv_sleep = [hrv[k] for k in sleeping]

    return {
        "evening": d, "wake_day": wake_day, "i": i, "alcohol": alcohol, "tennis": tennis,
        "heat_latent": heat, "heat_p": round(heat_p, 3), "bedtime_start": bedtime_start, "bedtime_end": bedtime_end,
        "phases": "".join(phases), "movement": "".join(move), "hr": hr, "hrv": hrv,
        "latency_ep": latency, "temp_dev": round(temp_dev, 2), "lowest_hr": min(hr_sleep),
        "avg_hr": round(sum(hr_sleep) / len(hr_sleep), 3), "avg_hrv": round(sum(hrv_sleep) / len(hrv_sleep)),
        "breath": round(14.5 + rng.gauss(0, 0.3) + (0.5 if alcohol else 0) + (0.3 if heat else 0), 3),
        "steps": max(2500, round(rng.gauss(8300, 1800) + (3600 if tennis else 0) + (1500 if d.weekday() >= 5 else 0) + (3000 if ctx["travel"] else 0))),
    }


def wake_blocks(phases: str, bedtime_start: datetime, latency_ep: int):
    """Runs of awake epochs after sleep onset, as (start datetime, minutes)."""
    out, k = [], latency_ep
    while k < len(phases) - 1:
        if phases[k] == "4":
            j = k
            while j < len(phases) - 1 and phases[j] == "4":
                j += 1
            out.append((plus(bedtime_start, 5 * k), 5 * (j - k)))
            k = j
        else:
            k += 1
    return out


def observed_night_heat(night: dict) -> bool:
    """Same rule the analysis uses: warm night + a >=15 min wake-up between 01:30 and 05:00."""
    if night["temp_dev"] < 0.30:
        return False
    for start, minutes in wake_blocks(night["phases"], night["bedtime_start"], night["latency_ep"]):
        mins = start.hour * 60 + start.minute
        if minutes >= 15 and 90 <= mins <= 300:
            return True
    return False


# ---------------------------------------------------------------------------
# Oura API v2 shaped files (field names from Oura's OpenAPI spec 1.43)
# ---------------------------------------------------------------------------

def sleep_contributors(n: dict) -> tuple[dict, int]:
    ph = n["phases"]
    deep = ph.count("1") * 5
    rem = ph.count("3") * 5
    total = (len(ph) - ph.count("4")) * 5
    eff = round(100 * total / (len(ph) * 5))
    wakes = len(wake_blocks(ph, n["bedtime_start"], n["latency_ep"]))
    mid = plus(n["bedtime_start"], mins_between(n["bedtime_start"], n["bedtime_end"]) / 2)
    mid_off = abs((mid.hour * 60 + mid.minute + (1440 if mid.hour < 12 else 0)) - (1440 + 180))
    c = {
        "deep_sleep": clip(round(deep / 75 * 100), 1, 100),
        "efficiency": clip(round(100 - max(0, 93 - eff) * 4), 1, 100),
        "latency": clip(round(100 - abs(n["latency_ep"] * 5 - 15) * 2.5), 1, 100),
        "rem_sleep": clip(round(rem / 100 * 100), 1, 100),
        "restfulness": clip(round(100 - wakes * 6 - ph.count("4") * 1.2), 1, 100),
        "timing": clip(round(100 - mid_off / 2), 1, 100),
        "total_sleep": clip(round(total / 480 * 100), 1, 100),
    }
    w = {"deep_sleep": .1, "efficiency": .1, "latency": .1, "rem_sleep": .1, "restfulness": .15, "timing": .1, "total_sleep": .35}
    return c, clip(round(sum(c[k] * w[k] for k in c)), 1, 100)


def readiness_block(n: dict, sleep_score: int, recent: list[dict]) -> dict:
    dev = n["temp_dev"]
    avg_sleep_h = sum((len(r["phases"]) - r["phases"].count("4")) * 5 for r in recent) / 60 / len(recent)
    c = {
        "activity_balance": clip(round(rng.gauss(80, 6)), 1, 100),
        "body_temperature": clip(round(100 - max(0.0, abs(dev) - 0.1) * 110), 1, 100),
        "hrv_balance": clip(round(80 + (n["avg_hrv"] - 36) * 1.5), 1, 100),
        "previous_day_activity": clip(round(rng.gauss(78, 10) + (10 if n["tennis"] else 0)), 1, 100),
        "previous_night": sleep_score,
        "recovery_index": clip(round(rng.gauss(55 if n["alcohol"] else 86, 6)), 1, 100),
        "resting_heart_rate": clip(round(92 - (n["lowest_hr"] - 52) * 3), 1, 100),
        "sleep_balance": clip(round(75 + (avg_sleep_h - 7) * 20), 1, 100),
        "sleep_regularity": clip(round(rng.gauss(84, 5)), 1, 100),
    }
    score = clip(round(sum(c.values()) / len(c)), 1, 100)
    trend = round(sum(r["temp_dev"] for r in recent[-3:]) / len(recent[-3:]), 2)
    return {"contributors": c, "score": score, "temperature_deviation": dev, "temperature_trend_deviation": trend}


def write_oura(nights: list[dict], life: dict):
    base = OUT / "wearables" / "oura"
    base.mkdir(parents=True, exist_ok=True)
    sleep, daily_sleep, daily_ready, activity, workouts = [], [], [], [], []
    for idx, n in enumerate(nights):
        contrib, score = sleep_contributors(n)
        recent = nights[max(0, idx - 13): idx + 1]
        ready = readiness_block(n, score, recent)
        ph = n["phases"]
        day = n["wake_day"].isoformat()
        stamp = iso(n["bedtime_start"])
        sleep.append({
            "id": uid("sleep", day), "average_breath": n["breath"], "average_heart_rate": n["avg_hr"],
            "average_hrv": n["avg_hrv"], "awake_time": ph.count("4") * 300,
            "bedtime_end": iso(n["bedtime_end"]), "bedtime_start": stamp, "day": day,
            "deep_sleep_duration": ph.count("1") * 300,
            "efficiency": round(100 * (len(ph) - ph.count("4")) / len(ph)),
            "heart_rate": {"interval": 300.0, "items": n["hr"], "timestamp": stamp},
            "hrv": {"interval": 300.0, "items": n["hrv"], "timestamp": stamp},
            "latency": n["latency_ep"] * 300, "light_sleep_duration": ph.count("2") * 300,
            "low_battery_alert": False, "lowest_heart_rate": n["lowest_hr"],
            "movement_30_sec": n["movement"], "period": 0, "readiness": ready,
            "readiness_score_delta": None, "rem_sleep_duration": ph.count("3") * 300,
            "restless_periods": sum(1 for k in range(1, len(n["movement"])) if n["movement"][k] in "34" and n["movement"][k - 1] not in "34"),
            "sleep_algorithm_version": "v2", "sleep_analysis_reason": "foreground_sleep_analysis",
            "sleep_phase_30_sec": None, "sleep_phase_5_min": ph, "sleep_score_delta": None,
            "time_in_bed": len(ph) * 300, "total_sleep_duration": (len(ph) - ph.count("4")) * 300,
            "type": "long_sleep", "ring_id": None, "app_sleep_phase_5_min": ph,
        })
        ts = iso(at(n["wake_day"], 0))
        daily_sleep.append({"id": uid("daily_sleep", day), "contributors": contrib, "day": day, "score": score, "timestamp": ts})
        daily_ready.append({"id": uid("daily_readiness", day), "contributors": ready["contributors"], "day": day,
                            "score": ready["score"], "temperature_deviation": ready["temperature_deviation"],
                            "temperature_trend_deviation": ready["temperature_trend_deviation"], "timestamp": ts})
        d = n["evening"]
        steps = n["steps"]
        active = round(steps * 0.045 + (380 if n["tennis"] else 0))
        activity.append({
            "id": uid("activity", d), "active_calories": active, "average_met_minutes": round(1.4 + steps / 40000, 3),
            "class_5_min": None,
            "contributors": {"meet_daily_targets": clip(round(rng.gauss(70, 12)), 1, 100), "move_every_hour": clip(round(rng.gauss(85, 8)), 1, 100),
                             "recovery_time": clip(round(rng.gauss(88, 6)), 1, 100), "stay_active": clip(round(rng.gauss(72, 10)), 1, 100),
                             "training_frequency": clip(round(rng.gauss(80, 8)), 1, 100), "training_volume": clip(round(rng.gauss(76, 9)), 1, 100)},
            "day": d.isoformat(), "equivalent_walking_distance": round(steps * 0.72),
            "high_activity_met_minutes": 90 if n["tennis"] else rng.randint(0, 20),
            "high_activity_time": 1800 if n["tennis"] else rng.choice([0, 300, 600]),
            "inactivity_alerts": rng.randint(0, 3), "low_activity_met_minutes": rng.randint(120, 220),
            "low_activity_time": rng.randint(14000, 21000), "medium_activity_met_minutes": rng.randint(60, 160),
            "medium_activity_time": rng.randint(2400, 5400), "met": None, "meters_to_target": max(0, 9000 - round(steps * 0.72)),
            "non_wear_time": rng.choice([0, 0, 1200, 2400]), "resting_time": rng.randint(26000, 31000),
            "score": clip(round(60 + steps / 400), 1, 100), "sedentary_met_minutes": rng.randint(8, 16),
            "sedentary_time": rng.randint(30000, 38000), "steps": steps, "target_calories": 450, "target_meters": 9000,
            "timestamp": iso(at(d, 4)), "total_calories": 1650 + active,
        })
        if n["tennis"]:
            s = at(d, 19, 5 + rng.randint(0, 6))
            workouts.append({"id": uid("workout", d, "tennis"), "activity": "tennis", "calories": round(rng.uniform(430, 520), 1),
                             "day": d.isoformat(), "distance": None, "end_datetime": iso(s + timedelta(minutes=rng.randint(80, 88))),
                             "intensity": "moderate", "label": None, "source": "autodetected", "start_datetime": iso(s)})
    for ev in TENNIS_LESSONS:
        d = D(ev)
        workouts.append({"id": uid("workout", d, "lesson"), "activity": "tennis", "calories": round(rng.uniform(330, 380), 1),
                         "day": ev, "distance": None, "end_datetime": iso(at(d, 10, 2)), "intensity": "hard",
                         "label": "Lesson", "source": "confirmed", "start_datetime": iso(at(d, 9, 0))})
    for d in evenings():
        if d.weekday() == 6:
            s = at(d, 10, 20 + rng.randint(0, 15))
            workouts.append({"id": uid("workout", d, "walk"), "activity": "walking", "calories": round(rng.uniform(150, 210), 1),
                             "day": d.isoformat(), "distance": float(rng.randint(3200, 4400)), "end_datetime": iso(s + timedelta(minutes=rng.randint(40, 55))),
                             "intensity": "easy", "label": None, "source": "autodetected", "start_datetime": iso(s)})
    workouts.sort(key=lambda w: w["start_datetime"])

    def dump(name, data):
        (base / f"{name}.json").write_text(json.dumps({"data": data, "next_token": None}, indent=1, ensure_ascii=False) + "\n")

    dump("sleep", sleep)
    dump("daily_sleep", daily_sleep)
    dump("daily_readiness", daily_ready)
    dump("daily_activity", activity)
    dump("workout", workouts)
    dump("enhanced_tag", [])    # Lisa has never added a tag
    (base / "personal_info.json").write_text(json.dumps({
        "id": uid("personal_info"), "age": 46, "weight": 64.0, "height": 1.68,
        "biological_sex": "female", "email": LISA[1]}, indent=1) + "\n")


# ---------------------------------------------------------------------------
# Apple Health export.xml (same nights, as an Apple Watch would have recorded them)
# ---------------------------------------------------------------------------

def hk_time(t: datetime) -> str:
    return t.strftime("%Y-%m-%d %H:%M:%S %z")


def xml_attr(s) -> str:
    return html.escape(str(s), quote=True)


def write_apple_health(nights: list[dict]):
    base = OUT / "wearables" / "apple_health"
    base.mkdir(parents=True, exist_ok=True)
    watch, phone = "Lisa’s Apple Watch", "Lisa’s iPhone"
    rows = []

    def rec(t, src, unit, start, end, value, created=None, meta=None):
        attrs = f'type="{t}" sourceName="{xml_attr(src)}" sourceVersion="{ "11.1" if src == watch else "19.1"}"'
        if unit:
            attrs += f' unit="{unit}"'
        attrs += f' creationDate="{hk_time(created or end)}" startDate="{hk_time(start)}" endDate="{hk_time(end)}" value="{xml_attr(value)}"'
        if meta:
            inner = "".join(f'\n  <MetadataEntry key="{k}" value="{xml_attr(v)}"/>' for k, v in meta.items())
            rows.append((start, f" <Record {attrs}>{inner}\n </Record>"))
        else:
            rows.append((start, f" <Record {attrs}/>"))

    stage = {"1": "HKCategoryValueSleepAnalysisAsleepDeep", "2": "HKCategoryValueSleepAnalysisAsleepCore",
             "3": "HKCategoryValueSleepAnalysisAsleepREM", "4": "HKCategoryValueSleepAnalysisAwake"}
    for n in nights:
        b0, b1, ph = n["bedtime_start"], n["bedtime_end"], n["phases"]
        rec("HKCategoryTypeIdentifierSleepAnalysis", phone, None, b0, b1, "HKCategoryValueSleepAnalysisInBed")
        k, last = n["latency_ep"], len(ph) - 1
        while k < last:
            j = k
            while j < last and ph[j] == ph[k]:
                j += 1
            rec("HKCategoryTypeIdentifierSleepAnalysis", watch, None, plus(b0, 5 * k), plus(b0, 5 * j), stage[ph[k]])
            k = j
        rec("HKQuantityTypeIdentifierAppleSleepingWristTemperature", watch, "degC", b0, b1, f"{35.12 + n['temp_dev']:.2f}")
        for k in range(0, len(ph), 3):
            if n["hr"][k] is not None:
                t = plus(b0, 5 * k)
                rec("HKQuantityTypeIdentifierHeartRate", watch, "count/min", t, t, n["hr"][k])
        span = mins_between(b0, b1)
        for frac in (0.3, 0.8):
            t = plus(b0, round(span * frac))
            rec("HKQuantityTypeIdentifierHeartRateVariabilitySDNN", watch, "ms", t, plus(t, 1), f"{n['avg_hrv'] * 1.25 + rng.gauss(0, 4):.4f}")
        for frac in (0.25, 0.5, 0.75):
            t = plus(b0, round(span * frac))
            rec("HKQuantityTypeIdentifierRespiratoryRate", watch, "count/min", t, plus(t, 10), f"{n['breath'] + rng.gauss(0, 0.4):.1f}")
        wd = n["wake_day"]
        rec("HKQuantityTypeIdentifierRestingHeartRate", watch, "count/min", at(wd, 0), at(wd, 23, 59), n["lowest_hr"] + 3)
        d = n["evening"]
        split = [0.35, 0.4, 0.25]
        for part, (h0, h1) in zip(split, [(7, 12), (12, 18), (18, 22)]):
            rec("HKQuantityTypeIdentifierStepCount", watch, "count", at(d, h0), at(d, h1), round(n["steps"] * part))

    workouts = []
    for n in nights:
        if n["tennis"]:
            s = at(n["evening"], 19, 6)
            e = s + timedelta(minutes=84)
            workouts.append((s, f' <Workout workoutActivityType="HKWorkoutActivityTypeTennis" duration="84" durationUnit="min" sourceName="{xml_attr(watch)}" sourceVersion="11.1" creationDate="{hk_time(e)}" startDate="{hk_time(s)}" endDate="{hk_time(e)}">\n'
                                f'  <WorkoutStatistics type="HKQuantityTypeIdentifierActiveEnergyBurned" startDate="{hk_time(s)}" endDate="{hk_time(e)}" sum="{rng.randint(430, 520)}" unit="Cal"/>\n </Workout>'))

    flows = ["HKCategoryValueMenstrualFlowMedium", "HKCategoryValueMenstrualFlowHeavy", "HKCategoryValueMenstrualFlowMedium",
             "HKCategoryValueMenstrualFlowLight", "HKCategoryValueMenstrualFlowLight", "HKCategoryValueMenstrualFlowLight"]
    for s, length in zip(PERIOD_STARTS, PERIOD_LENGTH_DAYS):
        for k in range(length):
            d = D(s) + timedelta(days=k)
            meta = {"HKMenstrualCycleStart": 1 if k == 0 else 0, "HKWasUserEntered": 1}
            rec("HKCategoryTypeIdentifierMenstrualFlow", "Health", None, at(d, 0), at(d, 0) + timedelta(days=1), flows[k], created=at(d, 8, 30), meta=meta)

    rows.sort(key=lambda r: r[0])
    workouts.sort(key=lambda r: r[0])
    head = ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!-- Synthetic Apple Health export for the fictional demo persona Lisa Hartley. Same nights as wearables/oura. -->\n'
            '<HealthData locale="en_US">\n'
            f' <ExportDate value="{hk_time(at(D("2026-11-05"), 7, 30))}"/>\n'
            ' <Me HKCharacteristicTypeIdentifierDateOfBirth="1980-03-14" HKCharacteristicTypeIdentifierBiologicalSex="HKBiologicalSexFemale" '
            'HKCharacteristicTypeIdentifierBloodType="HKBloodTypeNotSet" HKCharacteristicTypeIdentifierFitzpatrickSkinType="HKFitzpatrickSkinTypeNotSet" '
            'HKCharacteristicTypeIdentifierCardioFitnessMedicationsUse="None"/>\n')
    body = "\n".join(r[1] for r in rows) + "\n" + "\n".join(w[1] for w in workouts) + "\n"
    (base / "export.xml").write_text(head + body + "</HealthData>\n")


# ---------------------------------------------------------------------------
# Emails
# ---------------------------------------------------------------------------

EMAILS: list[dict] = []
LIVE: list[dict] = []


def wrap_html(brand: str, color: str, inner: str, footer: str) -> str:
    return (
        '<!doctype html><html><body style="margin:0;background:#f4f4f5;font-family:-apple-system,\'Segoe UI\',Helvetica,Arial,sans-serif;color:#1f2937">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:24px 12px">'
        '<table role="presentation" width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;background:#ffffff;border-radius:10px;overflow:hidden">'
        f'<tr><td style="background:{color};padding:18px 24px;color:#ffffff;font-size:18px;font-weight:600;letter-spacing:.2px">{html.escape(brand)}</td></tr>'
        f'<tr><td style="padding:24px;font-size:15px;line-height:1.55">{inner}</td></tr>'
        f'<tr><td style="padding:14px 24px;background:#fafafa;color:#9ca3af;font-size:11px;line-height:1.5">{footer}<br>Synthetic demo email · fictional business · not a real transaction.</td></tr>'
        '</table></td></tr></table></body></html>'
    )


def p(text: str) -> str:
    return f'<p style="margin:0 0 14px">{text}</p>'


def kv_table(rows: list[tuple[str, str]], bold_last=False) -> str:
    out = ['<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin:6px 0 16px">']
    for k, (a, b) in enumerate(rows):
        strong = bold_last and k == len(rows) - 1
        style = "padding:7px 0;border-top:1px solid #eef0f3" + (";font-weight:700" if strong else "")
        out.append(f'<tr><td style="{style}">{html.escape(a)}</td><td align="right" style="{style}">{html.escape(b)}</td></tr>')
    out.append("</table>")
    return "".join(out)


def add_email(when: datetime, sender: tuple[str, str], subject: str, text: str, html_body: str | None = None,
              category: str = "updates", expected: dict | None = None, live: bool = False):
    item = {"when": when, "from": {"name": sender[0], "email": sender[1]}, "subject": subject,
            "text": text.strip() + "\n", "html": html_body, "category": category, "expected": expected or {"relevant": False}}
    (LIVE if live else EMAILS).append(item)


def money(x: float) -> str:
    return f"${x:,.2f}"


def gen_restaurant_emails(life: dict):
    for ev, key, drank, res, rec, party, who in DINNERS:
        d = D(ev)
        name, addr, domain = RESTAURANTS[key]
        seat = at(d, 19, rng.choice([0, 15, 30])) if key != "harborview" else at(d, 19, 30)
        if res:
            booked = at(d - timedelta(days=rng.randint(1, 6)), rng.randint(9, 21), rng.randint(0, 59))
            sub = f"Reservation confirmed: {name}, {short_date(d)} at {clock(seat)}"
            text = (f"Hi Lisa,\n\nYou're all set.\n\n{name}\n{nice_date(d)} · {clock(seat)} · Party of {party}\n{addr}\n\n"
                    "Need to make a change? Manage your reservation in the TableTime app.\n"
                    "Tables are held for 15 minutes past the reservation time.\n\n— TableTime")
            inner = (p("Hi Lisa,") + p("<strong>You're all set.</strong>") +
                     f'<div style="border:1px solid #e5e7eb;border-radius:8px;padding:14px 16px;margin:0 0 16px">'
                     f'<div style="font-size:17px;font-weight:600">{html.escape(name)}</div>'
                     f'<div style="color:#4b5563">{nice_date(d)} · {clock(seat)} · Party of {party}</div>'
                     f'<div style="color:#6b7280;font-size:13px">{html.escape(addr)}</div></div>' +
                     p("Need to make a change? Manage your reservation in the TableTime app.") +
                     p('<span style="color:#6b7280;font-size:13px">Tables are held for 15 minutes past the reservation time.</span>'))
            add_email(booked, ("TableTime", "no-reply@tabletime.example"), sub, text,
                      wrap_html("TableTime", "#b45309", inner, "TableTime · reservations for independent restaurants"),
                      expected={"relevant": True, "category": "restaurant_reservation", "event_date": ev,
                                "event_time": seat.strftime("%H:%M"), "merchant": name, "party_size": party, "alcohol_signal": "unknown"})
        if rec:
            menu = MENUS[key]
            lines = []
            if drank:
                item, price = menu["drinks"][0]
                qty = 1 if price > 40 else (2 if party <= 3 else rng.choice([2, 3]))
                lines.append((item, qty, price))
            else:
                item, price = menu["soft"][0]
                lines.append((item, party if key == "spice" else 1, price))
            for item, price in rng.sample(menu["food"], k=min(len(menu["food"]), 2 + (party > 2))):
                lines.append((item, 1 if party <= 2 else rng.choice([1, 2]), price))
            subtotal = sum(q * pr for _, q, pr in lines)
            tax = round(subtotal * (0.1025 if key == "harborview" else 0.1075), 2)
            tip = round(subtotal * 0.2, 2)
            total = subtotal + tax + tip
            paid = at(d, 21, rng.randint(5, 55))
            table, server = rng.randint(3, 24), rng.choice(["Marco", "Ana", "Jules", "Priya", "Tom", "Keiko"])
            item_rows = [(f"{q} × {it}", money(q * pr)) for it, q, pr in lines]
            text = (f"{name}\n{addr}\n{short_date(d)}, {d.year} · {clock(paid)} · Table {table} · Server: {server}\n\n" +
                    "\n".join(f"{a:<38}{b:>10}" for a, b in item_rows) +
                    f"\n\n{'Subtotal':<38}{money(subtotal):>10}\n{'Tax':<38}{money(tax):>10}\n{'Tip':<38}{money(tip):>10}\n{'Total':<38}{money(total):>10}\n"
                    "Visa ending in 4417\n\nThanks for dining with us!\nReceipt powered by Tabbit")
            inner = (f'<div style="font-size:17px;font-weight:600">{html.escape(name)}</div>'
                     f'<div style="color:#6b7280;font-size:13px;margin-bottom:12px">{html.escape(addr)}<br>{short_date(d)}, {d.year} · {clock(paid)} · Table {table} · Server: {server}</div>' +
                     kv_table(item_rows) +
                     kv_table([("Subtotal", money(subtotal)), ("Tax", money(tax)), ("Tip", money(tip)), ("Total", money(total))], bold_last=True) +
                     p('<span style="color:#6b7280;font-size:13px">Visa ending in 4417</span>') + p("Thanks for dining with us!"))
            add_email(paid + timedelta(minutes=1), (f"{name} via Tabbit", f"receipts@{domain}"), f"Your receipt from {name}", text,
                      wrap_html(name, "#111827", inner, "Receipt powered by Tabbit"),
                      expected={"relevant": True, "category": "restaurant_receipt", "event_date": ev, "event_time": paid.strftime("%H:%M"),
                                "merchant": name, "items": [it for it, _, _ in lines],
                                "alcohol_signal": "present" if drank else "absent"})


WINES = ["2023 Sonoma Coast Chardonnay", "2022 Paso Robles Zinfandel", "2023 Willamette Pinot Noir", "2024 Lodi Rosé",
         "2022 Napa Cabernet Sauvignon", "2023 Santa Barbara Syrah", "2024 Mendocino Sauvignon Blanc", "2023 Anderson Valley Pinot Gris"]


def gen_wine_club():
    for ship, deliver in [("2026-07-08", "2026-07-10"), ("2026-08-07", "2026-08-10"), ("2026-09-09", "2026-09-11"), ("2026-10-08", "2026-10-10")]:
        bottles = rng.sample(WINES, 3)
        sender = ("Cellar Door Wine Club", "members@cellardoorwine.example")
        month = D(ship).strftime("%B")
        text = (f"Hi Lisa,\n\nYour {month} shipment is on its way!\n\n" + "\n".join(f"• {b}" for b in bottles) +
                f"\n\nEstimated delivery: {short_date(D(deliver))}. An adult signature (21+) is required.\n\nCheers,\nCellar Door Wine Club")
        inner = p("Hi Lisa,") + p(f"Your <strong>{month} shipment</strong> is on its way!") + kv_table([(b, "750 ml") for b in bottles]) + \
            p(f"Estimated delivery: <strong>{short_date(D(deliver))}</strong>. An adult signature (21+) is required.")
        add_email(at(D(ship), 10, 14), sender, f"Your {month} shipment is on its way 🍷", text,
                  wrap_html("Cellar Door Wine Club", "#7f1d1d", inner, "Cellar Door Wine Club · 3 bottles a month"),
                  expected={"relevant": True, "category": "alcohol_purchase", "event_date": deliver, "merchant": "Cellar Door Wine Club",
                            "items": bottles, "alcohol_signal": "present", "note": "home stock; not evidence for a specific evening"})
        text2 = f"Hi Lisa,\n\nYour Cellar Door shipment was delivered today at {clock(at(D(deliver), 14, 20))}. Enjoy!\n\nCellar Door Wine Club"
        add_email(at(D(deliver), 14, 22), sender, "Delivered: your Cellar Door shipment", text2,
                  wrap_html("Cellar Door Wine Club", "#7f1d1d", p("Hi Lisa,") + p("Your shipment was delivered today. Enjoy!"), "Cellar Door Wine Club"),
                  expected={"relevant": True, "category": "alcohol_purchase", "event_date": deliver, "merchant": "Cellar Door Wine Club",
                            "alcohol_signal": "present", "note": "delivery notice"})


GROCERIES = ["Bananas", "Greek yogurt (32 oz)", "Spinach", "Chicken thighs (2 lb)", "Brown rice", "Eggs (dozen)", "Oat milk", "Apples (3 lb)",
             "Sourdough loaf", "Salmon fillet", "Cherry tomatoes", "Avocados (4)", "Cheddar", "Pasta", "Marinara", "Broccoli", "Granola",
             "Sparkling water (12 pk)", "Coffee beans", "Kids' cereal", "Hummus", "Peanut butter", "Tortillas", "Black beans"]


def gen_groceries():
    with_wine = {"2026-07-12", "2026-08-09", "2026-09-13", "2026-10-11"}
    for ds in ["2026-07-12", "2026-07-19", "2026-08-02", "2026-08-09", "2026-08-23", "2026-08-30", "2026-09-13",
               "2026-09-20", "2026-10-04", "2026-10-11", "2026-10-25", "2026-11-01"]:
        d = D(ds)
        items = [(g, round(rng.uniform(2.5, 14), 2)) for g in rng.sample(GROCERIES, rng.randint(9, 14))]
        wine = ds in with_wine
        if wine:
            items.append(("Sauvignon Blanc, 750 ml", 13.99))
        total = sum(pr for _, pr in items) + 5.99
        text = ("Hi Lisa,\n\nYour FreshCart order was delivered.\n\n" + "\n".join(f"{g:<36}{money(pr):>9}" for g, pr in items) +
                f"\n{'Delivery fee':<36}{money(5.99):>9}\n{'Total':<36}{money(total):>9}\n\nThanks for shopping with FreshCart.")
        inner = p("Hi Lisa,") + p("Your FreshCart order was delivered.") + kv_table([(g, money(pr)) for g, pr in items]) + \
            kv_table([("Delivery fee", money(5.99)), ("Total", money(total))], bold_last=True)
        add_email(at(d, 11, rng.randint(0, 50)), ("FreshCart", "orders@freshcart.example"), "Your FreshCart order was delivered", text,
                  wrap_html("FreshCart", "#15803d", inner, "FreshCart grocery delivery"),
                  expected={"relevant": True, "category": "alcohol_purchase" if wine else "grocery_order", "event_date": ds,
                            "merchant": "FreshCart", "alcohol_signal": "present" if wine else "absent",
                            "note": "home stock; not evidence for a specific evening" if wine else ""})


def gen_parcelly():
    orders = [
        ("2026-07-14", "Kids' soccer cleats, size 6", 54.99, False),
        ("2026-08-05", "Graph-paper notebooks (6-pack) + highlighters", 23.47, False),
        ("2026-08-12", "Cooling bamboo pillowcases (2-pack)", 32.99, True),
        ("2026-08-20", "Moisture-wicking pajama set, women's M", 44.00, True),
        ("2026-09-01", "Quiet bedside oscillating fan", 39.95, True),
        ("2026-09-21", "Phone case, clear", 18.99, False),
        ("2026-10-06", "Halloween costume — dinosaur, kids' L", 29.99, False),
    ]
    for ds, item, price, symptom in orders:
        d = D(ds)
        eta = d + timedelta(days=2)
        order_no = f"112-{rng.randint(1000000, 9999999)}"
        text = (f"Hello Lisa,\n\nThanks for your order #{order_no}.\n\n{item}    {money(price)}\n\n"
                f"Arriving {short_date(eta)}.\nShip to: Lisa Hartley, Oakland, CA\n\nParcelly")
        inner = p("Hello Lisa,") + p(f"Thanks for your order <strong>#{order_no}</strong>.") + kv_table([(item, money(price))]) + \
            p(f"Arriving <strong>{short_date(eta)}</strong>.")
        add_email(at(d, rng.randint(20, 22), rng.randint(0, 59)), ("Parcelly", "orders@parcelly.example"), f"Order confirmed: {item}", text,
                  wrap_html("Parcelly", "#1d4ed8", inner, "Parcelly online store"),
                  expected={"relevant": symptom, "category": "symptom_relief_purchase" if symptom else "other_purchase",
                            "event_date": ds, "merchant": "Parcelly", "items": [item],
                            **({"related_to": "night heat / sleep"} if symptom else {})})


PHARMACY = ("Harbor Pharmacy", "rx@harborpharmacy.example")


def gen_pharmacy():
    store = "Harbor Pharmacy — Grand Ave, Oakland"
    # front-store purchase (not a prescription)
    d = D("2026-08-22")
    text = (f"Harbor Pharmacy receipt\n{store}\n{short_date(d)}, 2026 · 6:40 PM\n\nMelatonin 3 mg gummies, 60 ct    $11.49\n"
            "Lip balm    $3.99\nTax    $1.66\nTotal    $17.14\n\nThank you for shopping at Harbor Pharmacy.")
    inner = p(f"<strong>{store}</strong><br><span style='color:#6b7280;font-size:13px'>{short_date(d)}, 2026 · 6:40 PM</span>") + \
        kv_table([("Melatonin 3 mg gummies, 60 ct", "$11.49"), ("Lip balm", "$3.99"), ("Tax", "$1.66"), ("Total", "$17.14")], bold_last=True)
    add_email(at(d, 18, 41), ("Harbor Pharmacy", "receipts@harborpharmacy.example"), "Your Harbor Pharmacy receipt", text,
              wrap_html("Harbor Pharmacy", "#0f766e", inner, "Harbor Pharmacy"),
              expected={"relevant": True, "category": "symptom_relief_purchase", "event_date": "2026-08-22", "merchant": "Harbor Pharmacy",
                        "items": ["Melatonin 3 mg gummies, 60 ct"], "related_to": "sleep"})

    def ready(ds, hh, mm):
        txt = (f"Hi Lisa,\n\n1 prescription is ready for pickup at {store}.\n\nPickup hours: Mon–Fri 9 AM–8 PM, Sat–Sun 10 AM–6 PM.\n"
               "For your privacy, medication names are not included in emails. Sign in to the Harbor Pharmacy app for details.\n\nHarbor Pharmacy")
        inn = p("Hi Lisa,") + p(f"<strong>1 prescription</strong> is ready for pickup at {store}.") + \
            p("<span style='color:#6b7280;font-size:13px'>For your privacy, medication names are not included in emails.</span>")
        add_email(at(D(ds), hh, mm), PHARMACY, "Your prescription is ready for pickup", txt, wrap_html("Harbor Pharmacy", "#0f766e", inn, "Harbor Pharmacy"),
                  expected={"relevant": True, "category": "pharmacy_rx_ready", "event_date": ds, "merchant": "Harbor Pharmacy"})

    def picked(ds, hh, mm, first):
        txt = (f"Hi Lisa,\n\nThanks for picking up your prescription today.\n\nRx #4471-206 · Qty 30 · Copay $15.00\n"
               f"{'Refills remaining: 5' if first else 'Refills remaining: ' + ('4' if ds < '2026-11-01' else '3')}\n\nHarbor Pharmacy")
        inn = p("Hi Lisa,") + p("Thanks for picking up your prescription today.") + \
            kv_table([("Rx #4471-206", "Qty 30"), ("Copay", "$15.00")])
        add_email(at(D(ds), hh, mm), PHARMACY, "Thanks for picking up your prescription", txt, wrap_html("Harbor Pharmacy", "#0f766e", inn, "Harbor Pharmacy"),
                  expected={"relevant": True, "category": "pharmacy_rx_pickup", "event_date": ds, "merchant": "Harbor Pharmacy",
                            "rx_number": "4471-206", "is_first_fill": first})

    ready("2026-09-03", 16, 5)
    picked("2026-09-04", 17, 48, True)
    txt = "Hi Lisa,\n\nRx #4471-206 is due for a refill. Reply REFILL or tap below to refill.\n\nHarbor Pharmacy"
    add_email(at(D("2026-10-01"), 10, 0), PHARMACY, "Refill reminder: Rx #4471-206", txt,
              wrap_html("Harbor Pharmacy", "#0f766e", p("Hi Lisa,") + p("Rx #4471-206 is due for a refill."), "Harbor Pharmacy"),
              expected={"relevant": True, "category": "pharmacy_refill_reminder", "event_date": "2026-10-01", "rx_number": "4471-206"})
    ready("2026-10-02", 15, 30)
    picked("2026-10-03", 11, 20, False)
    ready("2026-11-01", 10, 5)
    picked("2026-11-02", 12, 10, False)


CLINIC = ("Bayside Women's Health", "appointments@baysidewomenshealth.example")
CLINIC_ADDR = "350 30th St, Suite 400, Oakland, CA"


def clinic_email(when, subject, lead, appt: datetime, visit: str, expected, live=False, extra=""):
    text = (f"Hi Lisa,\n\n{lead}\n\n{visit}\n{nice_date(appt.date())} at {clock(appt)}\nElena Ruiz, MD · Obstetrics & Gynecology\n{CLINIC_ADDR}\n\n"
            f"{extra}To reschedule, call (510) 555-0142 or use the Bayside patient portal.\n\nBayside Women's Health")
    inner = (p("Hi Lisa,") + p(lead) +
             f'<div style="border-left:4px solid #9d174d;background:#fdf2f8;padding:12px 16px;margin:0 0 16px">'
             f'<div style="font-weight:600">{html.escape(visit)}</div><div>{nice_date(appt.date())} at {clock(appt)}</div>'
             f'<div style="color:#6b7280;font-size:13px">Elena Ruiz, MD · Obstetrics &amp; Gynecology<br>{html.escape(CLINIC_ADDR)}</div></div>' +
             (p(html.escape(extra.strip())) if extra else "") +
             p('<span style="color:#6b7280;font-size:13px">To reschedule, call (510) 555-0142 or use the Bayside patient portal.</span>'))
    add_email(when, CLINIC, subject, text, wrap_html("Bayside Women's Health", "#9d174d", inner, "Bayside Women's Health · patient portal notifications"),
              expected=expected, live=live)


def gen_clinic():
    appt1 = at(D("2026-09-02"), 10, 0)
    clinic_email(at(D("2026-08-19"), 10, 42), "Appointment confirmed: Annual well-woman exam on Sep 2",
                 "Your appointment is confirmed.", appt1, "Annual well-woman exam",
                 {"relevant": True, "category": "medical_appointment", "event_date": "2026-09-02", "event_time": "10:00",
                  "provider": "Elena Ruiz, MD", "specialty": "OB-GYN", "visit_type": "annual exam"})
    clinic_email(at(D("2026-08-31"), 9, 0), "Reminder: Annual well-woman exam on Wed, Sep 2",
                 "This is a reminder of your upcoming appointment.", appt1, "Annual well-woman exam",
                 {"relevant": True, "category": "appointment_reminder", "event_date": "2026-09-02", "event_time": "10:00",
                  "provider": "Elena Ruiz, MD", "specialty": "OB-GYN", "visit_type": "annual exam", "triggers": "doctor_visit_brief"},
                 extra="Please arrive 10 minutes early. ")
    txt = ("Hi Lisa,\n\nA new visit summary from your appointment with Elena Ruiz, MD on Sep 2 is available.\n"
           "For your privacy, details are only available in the Bayside patient portal.\n\nBayside Women's Health")
    add_email(at(D("2026-09-02"), 12, 5), CLINIC, "Your visit summary is ready", txt,
              wrap_html("Bayside Women's Health", "#9d174d", p("Hi Lisa,") + p("A new visit summary from your appointment on Sep 2 is available in the patient portal."), "Bayside Women's Health"),
              expected={"relevant": True, "category": "medical_portal_notice", "event_date": "2026-09-02"})
    appt2 = at(D("2026-11-10"), 9, 30)
    clinic_email(at(D("2026-09-02"), 12, 20), "Appointment confirmed: Follow-up visit on Nov 10",
                 "Your follow-up appointment is confirmed.", appt2, "Follow-up visit",
                 {"relevant": True, "category": "medical_appointment", "event_date": "2026-11-10", "event_time": "09:30",
                  "provider": "Elena Ruiz, MD", "specialty": "OB-GYN", "visit_type": "follow-up"})
    clinic_email(at(D("2026-11-05"), 8, 12), "Reminder: Follow-up visit on Tue, Nov 10",
                 "This is a reminder of your upcoming appointment.", appt2, "Follow-up visit",
                 {"relevant": True, "category": "appointment_reminder", "event_date": "2026-11-10", "event_time": "09:30",
                  "provider": "Elena Ruiz, MD", "specialty": "OB-GYN", "visit_type": "follow-up", "triggers": "doctor_visit_brief"},
                 live=True, extra="Please arrive 10 minutes early. ")


def gen_tennis_club():
    sender = ("Courtside Tennis Club", "bookings@courtsidetennis.example")
    for ds in TENNIS_LESSONS:
        d = D(ds)
        booked = at(d - timedelta(days=3), 20, rng.randint(0, 59))
        text = (f"Hi Lisa,\n\nYour private lesson is booked.\n\n{nice_date(d)} · 9:00–10:00 AM · Court 4\nCoach: Daniel Ortiz\n\n"
                "Cancel at least 24 hours ahead to avoid a fee.\n\nCourtside Tennis Club")
        inner = p("Hi Lisa,") + p("Your private lesson is booked.") + kv_table([("Date", nice_date(d)), ("Time", "9:00–10:00 AM"), ("Court", "4"), ("Coach", "Daniel Ortiz")])
        add_email(booked, sender, f"Lesson booked: {short_date(d)}, 9:00 AM", text, wrap_html("Courtside Tennis Club", "#047857", inner, "Courtside Tennis Club"),
                  expected={"relevant": True, "category": "exercise_booking", "event_date": ds, "event_time": "09:00", "activity": "tennis lesson"})
    for ds in ["2026-07-01", "2026-08-03", "2026-09-01", "2026-10-01", "2026-11-02"]:
        if D(ds) < FIRST_EVENING - timedelta(days=3):
            continue
        add_email(at(D(ds), 7, 30), ("Courtside Tennis Club", "news@courtsidetennis.example"),
                  f"Courtside Club News — {D(ds):%B}",
                  "Hi members,\n\nCourt resurfacing on courts 1–2 this month, junior clinics are open, and the fall doubles ladder starts soon.\n\nSee you on court!\nCourtside Tennis Club",
                  wrap_html("Courtside Tennis Club", "#047857", p("Hi members,") + p("Court resurfacing on courts 1–2 this month, junior clinics are open, and the fall doubles ladder starts soon."), "Courtside Tennis Club newsletter"),
                  category="promotions")


def gen_travel():
    air = ("Bayline Air", "itinerary@baylineair.example")
    text = ("Hi Lisa,\n\nYour trip is booked. Confirmation code: QZ7K4P\n\n"
            "Wed, Oct 14 · BL 412 · Oakland (OAK) 7:15 AM → Seattle (SEA) 9:20 AM\n"
            "Fri, Oct 16 · BL 419 · Seattle (SEA) 6:40 PM → Oakland (OAK) 8:45 PM\n\nPassenger: Lisa Hartley · Seat 8C / 9D\n\nBayline Air")
    inner = p("Hi Lisa,") + p("Your trip is booked. Confirmation code: <strong>QZ7K4P</strong>") + \
        kv_table([("Wed, Oct 14 · BL 412", "OAK 7:15 AM → SEA 9:20 AM"), ("Fri, Oct 16 · BL 419", "SEA 6:40 PM → OAK 8:45 PM")])
    add_email(at(D("2026-09-24"), 14, 3), air, "Your trip to Seattle is booked — QZ7K4P", text, wrap_html("Bayline Air", "#1e3a8a", inner, "Bayline Air"),
              expected={"relevant": True, "category": "travel_booking", "event_date": "2026-10-14", "end_date": "2026-10-16",
                        "details": "OAK→SEA Oct 14 07:15, SEA→OAK Oct 16 18:40"})
    hotel = ("The Marlowe Seattle", "stay@marloweseattle.example")
    text = ("Dear Lisa,\n\nWe look forward to welcoming you.\n\nCheck-in: Wed, Oct 14 (3 PM)\nCheck-out: Fri, Oct 16 (11 AM)\n"
            "1 King room · 2 nights · Confirmation 88213904\n\nThe Marlowe Seattle")
    add_email(at(D("2026-09-24"), 14, 40), hotel, "Reservation confirmed — The Marlowe Seattle, Oct 14–16", text,
              wrap_html("The Marlowe Seattle", "#374151", p("Dear Lisa,") + kv_table([("Check-in", "Wed, Oct 14 · 3 PM"), ("Check-out", "Fri, Oct 16 · 11 AM"), ("Room", "1 King · 2 nights")]), "The Marlowe Seattle"),
              expected={"relevant": True, "category": "hotel_booking", "event_date": "2026-10-14", "end_date": "2026-10-16"})
    add_email(at(D("2026-10-13"), 7, 15), air, "Check in now for your flight to Seattle tomorrow",
              "Hi Lisa,\n\nCheck-in is open for BL 412, Oakland (OAK) 7:15 AM → Seattle (SEA), Wed, Oct 14. Boarding begins at 6:35 AM.\n\nBayline Air",
              wrap_html("Bayline Air", "#1e3a8a", p("Hi Lisa,") + p("Check-in is open for <strong>BL 412</strong>, OAK 7:15 AM → SEA, Wed, Oct 14."), "Bayline Air"),
              expected={"relevant": True, "category": "travel_checkin", "event_date": "2026-10-14", "event_time": "07:15"})


def personal(when, name, addr, subject, text):
    add_email(when, (name, addr), subject, text, None, category="personal",
              expected={"relevant": False, "prefilter": "skip_personal"})


def gen_personal_and_work():
    personal(at(D("2026-07-06"), 18, 2), "Anna Lindqvist", "anna.lindqvist@mail.example", "Book club Wed!",
             "Hi all — book club Wednesday at mine, 7pm. We're on chapters 1–12. Tea and cake provided!\nAnna")
    personal(at(D("2026-07-13"), 20, 11), "Grace Park", "grace.park@mail.example", "BBQ Saturday?",
             "Hey Lisa! We're doing a backyard BBQ this Saturday from 5. Bring the kids. Let me know!\nGrace")
    personal(at(D("2026-08-06"), 12, 30), "Mark Hartley", "mark.hartley@mail.example", "Sat dinner",
             "Nguyens confirmed for Sat 6pm. I'll do the grill, can you get dessert?\nM")
    personal(at(D("2026-08-10"), 9, 15), "Anna Lindqvist", "anna.lindqvist@mail.example", "Book club this Wed",
             "Reminder: Wednesday 7pm at mine. Finishing the book!\nA")
    personal(at(D("2026-08-17"), 19, 48), "Sarah Kim", "sarah.kim@mail.example", "Girls' night Sat 22nd?",
             "Lisa!! Girls' night at mine Sat the 22nd, 7pm. Jen and Dana are in. Bring snacks 💛\nS")
    personal(at(D("2026-09-07"), 10, 2), "Anna Lindqvist", "anna.lindqvist@mail.example", "September book pick",
             "New book this month — see you Wednesday the 9th!\nAnna")
    personal(at(D("2026-09-28"), 21, 5), "Sarah Kim", "sarah.kim@mail.example", "Round two — Sat Oct 3?",
             "Last one was too fun. Same time, Sat Oct 3? 💃\nS")
    personal(at(D("2026-10-05"), 13, 40), "Jen Alvarez", "jen.alvarez@mail.example", "You're invited: Jen's 50th 🎉",
             "Lisa — I'm turning 50 (!!). Party at our place, Sat Oct 24 from 7. Partners welcome.\nJen")
    personal(at(D("2026-10-20"), 8, 55), "Mark Hartley", "mark.hartley@mail.example", "Leo dentist moved",
             "Dentist moved Leo to Thu 3:30. I can take him.\nM")
    work = [
        ("2026-07-07", "Dana Whitfield", "Q3 roadmap review — draft deck", "Draft deck attached for the Jul 29 review. Comments by Friday please."),
        ("2026-07-15", "Raj Patel", "Sprint 31 retro notes", "Notes from today's retro are in the team folder. Two action items for you."),
        ("2026-07-29", "Dana Whitfield", "Thanks for today", "Great job on the roadmap review. Let's sync Tuesday about staffing."),
        ("2026-08-04", "Priyanka Rao", "Vendor contract — redlines", "Legal sent redlines. Can you look before Thursday?"),
        ("2026-08-18", "Raj Patel", "Sprint 33 planning", "Planning moved to Wed 10am. Updated board link inside."),
        ("2026-09-08", "Dana Whitfield", "Offsite agenda — Sep 17", "Agenda for the offsite: workshops 1–5pm, then team dinner at Lakeside Grill at 6."),
        ("2026-09-22", "Priyanka Rao", "Seattle client workshop — logistics", "Workshop Oct 14–16. Please book travel; finance approved."),
        ("2026-10-06", "Raj Patel", "QBR slides due Oct 20", "Reminder that QBR slides are due Oct 20. Template inside."),
        ("2026-10-19", "Dana Whitfield", "QBR dry run", "Can we do a dry run Wednesday afternoon?"),
        ("2026-10-28", "HR @ Fernwood Labs", "Open enrollment: elections due Nov 13", "Open enrollment is live. Review your benefits by Nov 13."),
    ]
    for ds, who, subj, body in work:
        addr = "hr@fernwoodlabs.example" if who.startswith("HR") else who.split()[0].lower() + "@fernwoodlabs.example"
        add_email(at(D(ds), rng.randint(9, 16), rng.randint(0, 59)), (who, addr), subj, f"Hi Lisa,\n\n{body}\n\n{who.split()[0]}", None,
                  category="work", expected={"relevant": False, "prefilter": "skip_personal"})


def gen_noise():
    for ds in ["2026-07-11", "2026-07-25", "2026-08-08", "2026-08-22", "2026-09-05", "2026-09-19", "2026-10-03", "2026-10-17", "2026-10-31"]:
        trap = ds == "2026-09-19"
        topic = "This weekend: the Oakland Wine Walk, 30+ tasting rooms on Broadway" if trap else rng.choice(
            ["Farmers markets open late this month", "New bike lanes on Telegraph", "Lake Merritt lights festival", "Five hikes for fall colors", "School board meeting recap"])
        add_email(at(D(ds), 7, 0), ("Bay Weekly Digest", "digest@bayweekly.example"), f"Bay Weekly: {topic}",
                  f"This week in the East Bay:\n\n• {topic}\n• Restaurant openings\n• Weekend weather\n\nUnsubscribe anytime.",
                  wrap_html("Bay Weekly Digest", "#334155", p(f"• {html.escape(topic)}") + p("• Restaurant openings<br>• Weekend weather"), "Bay Weekly Digest"),
                  category="promotions", expected={"relevant": False, "category": "irrelevant", "note": "newsletter; the wine walk is not Lisa's plan" if trap else ""})
    for ds in ["2026-07-08", "2026-08-08", "2026-09-08", "2026-10-08"]:
        add_email(at(D(ds), 6, 30), ("Pinecone Credit Union", "statements@pineconecu.example"), "Your statement is ready",
                  "Hi Lisa,\n\nYour monthly statement is ready to view in online banking.\n\nPinecone Credit Union",
                  wrap_html("Pinecone Credit Union", "#365314", p("Your monthly statement is ready to view in online banking."), "Pinecone Credit Union"),
                  expected={"relevant": False, "category": "irrelevant"})
        add_email(at(D(ds) + timedelta(days=4), 8, 10), ("EastBay Power", "billing@eastbaypower.example"), "Your bill is ready",
                  "Hi Lisa,\n\nYour energy bill is ready. Autopay is on.\n\nEastBay Power",
                  wrap_html("EastBay Power", "#a16207", p("Your energy bill is ready. Autopay is on."), "EastBay Power"),
                  expected={"relevant": False, "category": "irrelevant"})
        add_email(at(D(ds) + timedelta(days=9), 3, 5), ("Streamly", "billing@streamly.example"), "Your Streamly receipt",
                  "Hi Lisa,\n\nThanks for being a member. Family plan $22.99.\n\nStreamly",
                  wrap_html("Streamly", "#6d28d9", p("Family plan — $22.99"), "Streamly"),
                  expected={"relevant": False, "category": "irrelevant"})
    for ds, subj in [("2026-08-03", "Welcome back! First day is Wed, Aug 12"), ("2026-08-20", "Back-to-school night: Thu, Aug 27, 6:30 PM"),
                     ("2026-09-11", "Picture day is Sep 24"), ("2026-10-09", "Fall conferences sign-up"), ("2026-10-23", "Halloween parade Oct 30")]:
        add_email(at(D(ds), 15, 0), ("Oakwood Middle School", "no-reply@oakwoodms.example"), subj,
                  f"Dear families,\n\n{subj}. More details on the school website.\n\nOakwood Middle School",
                  wrap_html("Oakwood Middle School", "#9a3412", p("Dear families,") + p(html.escape(subj) + "."), "Oakwood Middle School"),
                  expected={"relevant": False, "category": "irrelevant"})
    for ds in ["2026-08-24", "2026-09-07", "2026-09-21", "2026-10-05", "2026-10-19", "2026-11-02"]:
        add_email(at(D(ds), 17, 30), ("Bay Strikers U13", "team@baystrikers.example"), f"Game schedule — week of {short_date(D(ds))}",
                  "Hi families,\n\nSaturday game at 10:00, arrive 9:30 for warm-up. Snack rota attached.\n\nCoach Mia",
                  wrap_html("Bay Strikers U13", "#0369a1", p("Saturday game at 10:00, arrive 9:30 for warm-up."), "Bay Strikers U13"),
                  expected={"relevant": False, "category": "irrelevant"})


# ---------------------------------------------------------------------------
# Calendar (Google Calendar API v3 events.list, singleEvents=true)
# ---------------------------------------------------------------------------

def write_calendar(life: dict):
    items = []

    def ev(key, summary, start: datetime, end: datetime, location=None, recurring=None, all_day=False):
        e = {"kind": "calendar#event", "id": uid("cal", key, start.date()).replace("-", "")[:26], "status": "confirmed", "summary": summary}
        if location:
            e["location"] = location
        if all_day:
            e["start"], e["end"] = {"date": start.date().isoformat()}, {"date": end.date().isoformat()}
        else:
            e["start"] = {"dateTime": iso(start), "timeZone": "America/Los_Angeles"}
            e["end"] = {"dateTime": iso(end), "timeZone": "America/Los_Angeles"}
        if recurring:
            e["recurringEventId"] = recurring
        items.append(e)

    for d in evenings():
        if life[d]["tennis"]:
            ev("tennis", "Tennis doubles", at(d, 19), at(d, 20, 30), "Courtside Tennis Club", recurring="tennisdoublesthursday")
        if d.weekday() == 1 and d not in TRAVEL_NIGHTS:
            ev("1on1", "1:1 with Dana", at(d, 10), at(d, 10, 30), "Zoom", recurring="oneononedana")
        if d.weekday() == 0:
            ev("sync", "Project sync", at(d, 9, 30), at(d, 10), "Conf room Juniper", recurring="projectsyncmonday")
        if d.weekday() == 5 and D("2026-09-12") <= d <= D("2026-10-31"):
            ev("soccer", "Leo — soccer game", at(d, 10), at(d, 11, 30), "Bushrod Park", recurring="leosoccer")
    for ds, title, loc, h0, h1, _ in SOCIAL:
        ev("social", title, at(D(ds), h0), at(D(ds), h1), loc)
    for ds in TENNIS_LESSONS:
        ev("lesson", "Tennis lesson w/ Daniel", at(D(ds), 9), at(D(ds), 10), "Courtside Tennis Club")
    for ev_, key, drank, res, rec, party, who in DINNERS:
        if res:
            ev("dinner", f"Dinner — {RESTAURANTS[key][0]}", at(D(ev_), 19), at(D(ev_), 21), RESTAURANTS[key][1])
    ev("roadmap", "Q3 roadmap review", at(D("2026-07-29"), 13), at(D("2026-07-29"), 15), "Conf room Sequoia")
    ev("dentist", "Leo — dentist", at(D("2026-07-22"), 15, 30), at(D("2026-07-22"), 16, 30), "Grand Lake Dental")
    ev("bts", "Back-to-school night", at(D("2026-08-27"), 18, 30), at(D("2026-08-27"), 20), "Oakwood Middle School")
    ev("exam", "Annual exam — Dr. Ruiz", at(D("2026-09-02"), 10), at(D("2026-09-02"), 11), CLINIC_ADDR)
    ev("offsite", "Team offsite (workshops)", at(D("2026-09-17"), 13), at(D("2026-09-17"), 17), "Lakeside Grill, Oakland")
    ev("haircut", "Haircut", at(D("2026-09-30"), 12), at(D("2026-09-30"), 13), "Studio Nine")
    ev("seattle", "Seattle — client workshop", at(D("2026-10-14"), 0), at(D("2026-10-17"), 0), "Seattle, WA", all_day=True)
    ev("flight1", "Flight BL 412 OAK→SEA", at(D("2026-10-14"), 7, 15), at(D("2026-10-14"), 9, 20), "Oakland International Airport")
    ev("flight2", "Flight BL 419 SEA→OAK", at(D("2026-10-16"), 18, 40), at(D("2026-10-16"), 20, 45), "Seattle-Tacoma International Airport")
    ev("qbr", "QBR — presenting", at(D("2026-10-22"), 14), at(D("2026-10-22"), 15, 30), "Board room")
    ev("halloween", "Trick-or-treat with the kids", at(D("2026-10-31"), 17, 30), at(D("2026-10-31"), 20))
    ev("followup", "Follow-up — Dr. Ruiz", at(D("2026-11-10"), 9, 30), at(D("2026-11-10"), 10, 15), CLINIC_ADDR)
    items.sort(key=lambda e: e["start"].get("dateTime") or e["start"]["date"])
    out = OUT / "calendar"
    out.mkdir(exist_ok=True)
    (out / "events.json").write_text(json.dumps({"kind": "calendar#events", "summary": LISA[1], "timeZone": "America/Los_Angeles",
                                                 "items": items}, indent=1, ensure_ascii=False) + "\n")
    return items


# ---------------------------------------------------------------------------
# One-tap answers Lisa gave in the app (only during the learning window)
# ---------------------------------------------------------------------------

def evidence_for(d: date, life: dict) -> str:
    x = life[d]
    if x["dinner"] and x["dinner"]["receipt"]:
        return "receipt_alcohol" if x["dinner"]["drank"] else "receipt_no_alcohol"
    if (x["dinner"] and x["dinner"]["reservation"]) or x["social"]:
        return "possible"
    return "none"


def write_confirmations(nights: list[dict], life: dict):
    by_evening = {n["evening"]: n for n in nights}
    asked, asked_days = [], []
    d = LEARNING_WINDOW[0]
    while d <= LEARNING_WINDOW[1]:
        ev = evidence_for(d, life)
        heat = observed_night_heat(by_evening[d])
        reason = None
        if ev == "possible":
            x = life[d]
            reason = f"You had {x['social']['title']} on the calendar" if x["social"] else f"You had a reservation at {RESTAURANTS[x['dinner']['key']][0]}"
        elif heat and ev == "none" and d < TREATMENT_START:
            reason = "Your night temperature jumped and you woke up around 3 AM"
        week = [a for a in asked_days if (d - a).days < 7]
        if reason and len(week) < 2:
            asked_at = at(d + timedelta(days=1), 8, rng.randint(0, 25))
            asked.append({"id": uid("confirm", d), "asked_at": iso(asked_at), "about_evening": d.isoformat(),
                          "reason": reason, "question": "Did you have a drink last night?",
                          "answer": "yes" if life[d]["alcohol"] else "no",
                          "answered_at": iso(asked_at + timedelta(minutes=rng.randint(2, 90)))})
            asked_days.append(d)
        d += timedelta(days=1)
    asked.append({"id": uid("confirm", "treatment"), "asked_at": iso(at(TREATMENT_START, 18, 5)), "about_evening": TREATMENT_START.isoformat(),
                  "reason": "Harbor Pharmacy says you picked up a prescription today (first fill)",
                  "question": "Is this a new treatment your doctor started? I'll compare your nights before and after.",
                  "answer": "yes — starting today", "answered_at": iso(at(TREATMENT_START, 18, 21))})
    asked.sort(key=lambda a: a["asked_at"])
    out = OUT / "app_state"
    out.mkdir(exist_ok=True)
    (out / "confirmations.json").write_text(json.dumps({"confirmations": asked}, indent=1, ensure_ascii=False) + "\n")
    return asked


# ---------------------------------------------------------------------------
# Writers: emails, eml, profile, truth
# ---------------------------------------------------------------------------

def write_emails():
    out = OUT / "emails"
    (out / "eml").mkdir(parents=True, exist_ok=True)
    for old in (out / "eml").glob("*.eml"):
        old.unlink()
    EMAILS.sort(key=lambda e: e["when"])
    inbox, expected = [], []

    def record(e, mid):
        snippet = " ".join(e["text"].split())[:140]
        return {"id": mid, "thread_id": "t" + uid("thread", mid).replace("-", "")[:15], "date": iso(e["when"]),
                "from": e["from"], "to": [{"name": LISA[0], "email": LISA[1]}], "subject": e["subject"],
                "snippet": snippet, "category": e["category"], "is_read": e["when"] < datetime(2026, 11, 4, tzinfo=TZ),
                "body_text": e["text"], "body_html": e["html"]}

    def eml(e, mid):
        m = EmailMessage()
        m["From"] = f'{e["from"]["name"]} <{e["from"]["email"]}>'
        m["To"] = f"{LISA[0]} <{LISA[1]}>"
        m["Subject"] = e["subject"]
        m["Date"] = format_datetime(e["when"])
        m["Message-ID"] = f"<{mid}.{uid('mid', mid)[:8]}@demo.example>"
        m["X-Demo-Data"] = "synthetic"
        m.set_content(e["text"])
        if e["html"]:
            m.add_alternative(e["html"], subtype="html")
        (out / "eml" / f"{e['when']:%Y-%m-%d_%H%M}_{mid}.eml").write_bytes(bytes(m))

    for k, e in enumerate(EMAILS, 1):
        mid = f"msg_{k:04d}"
        inbox.append(record(e, mid))
        expected.append({"email_id": mid, "date": iso(e["when"]), "from": e["from"]["email"], "subject": e["subject"], **e["expected"]})
        eml(e, mid)
    live = LIVE[0]
    live_rec = record(live, "msg_live")
    live_rec["is_read"] = False
    eml(live, "msg_live")
    expected.append({"email_id": "msg_live", "date": iso(live["when"]), "from": live["from"]["email"], "subject": live["subject"], **live["expected"]})
    (out / "emails.json").write_text(json.dumps({"mailbox": LISA[1], "messages": inbox}, indent=1, ensure_ascii=False) + "\n")
    (out / "live_demo_email.json").write_text(json.dumps(live_rec, indent=1, ensure_ascii=False) + "\n")
    tdir = OUT / "truth"
    tdir.mkdir(exist_ok=True)
    (tdir / "email_expected_events.json").write_text(json.dumps({"note": "Answer key for the extraction step. Personal and work mail is skipped by the sender prefilter and never sent to Claude.",
                                                                 "expected": expected}, indent=1, ensure_ascii=False) + "\n")
    return inbox


def write_truth(nights: list[dict], life: dict):
    tdir = OUT / "truth"
    tdir.mkdir(exist_ok=True)
    with open(tdir / "nights_truth.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["evening", "oura_day", "phase", "on_treatment", "alcohol_truth", "alcohol_context", "evidence", "tennis",
                    "dinner_out", "travel", "p_night_heat", "night_heat_latent", "night_heat_observed", "temp_dev_c"])
        t0 = (TREATMENT_START - FIRST_EVENING).days
        for n in nights:
            d, x = n["evening"], life[n["evening"]]
            phase = "A_baseline" if n["i"] < 28 else ("B_symptoms" if n["i"] < t0 else "C_treatment")
            w.writerow([d, n["wake_day"], phase, int(d >= TREATMENT_START), int(x["alcohol"]), x["alcohol_context"], evidence_for(d, life),
                        int(x["tennis"]), int(bool(x["dinner"])), int(x["travel"]), n["heat_p"], int(n["heat_latent"]),
                        int(observed_night_heat(n)), n["temp_dev"]])


def write_profile():
    starts = [D(s) for s in PERIOD_STARTS]
    cycles = [{"start": s.isoformat(), "length_days": (b - s).days} for s, b in zip(starts, starts[1:])]
    cycles.append({"start": starts[-1].isoformat(), "length_days": None, "note": "current cycle"})
    prof = {
        "synthetic": True,
        "note": "Fictional persona for a hackathon demo. All names, merchants and addresses are made up (.example domains).",
        "name": LISA[0], "preferred_name": "Lisa", "email": LISA[1],
        "date_of_birth": "1980-03-14", "age": 46, "sex": "female", "height_cm": 168, "weight_kg": 64,
        "home": "Oakland, CA", "time_zone": "America/Los_Angeles",
        "occupation": "Senior project manager at Fernwood Labs (fictional)",
        "household": {"partner": "Mark Hartley, 48", "children": [{"name": "Emma", "age": 15}, {"name": "Leo", "age": 12}]},
        "routines": ["Tennis doubles, Thursdays 7–8:30 PM", "Occasional Saturday tennis lessons", "Dinner out about once a week",
                     "Wine club, 3 bottles a month", "Book club, 2nd Wednesday of the month", "Weekday wake-up 6:20 AM once school starts (Aug 12)"],
        "devices": [
            {"device": "Oura Ring Gen4", "since": "2024-11", "worn": "every night", "data": "wearables/oura"},
            {"device": "iPhone (Health app)", "data": "logs period start dates in Cycle Tracking — a habit she already had"},
            {"device": "Apple Watch Series 10", "data": "wearables/apple_health — the same nights as the Oura files, for the device-switch demo"}],
        "connected_in_demo": ["Oura API (read)", "Email inbox (read-only; only automated receipts, bookings, appointments)",
                              "Google Calendar (read-only)", "Apple Health (cycle logs)"],
        "health_background": {"diagnoses": "none", "regular_medications_before_sep_2026": "none", "smoking": "never",
                              "alcohol": "social drinker, about 2 evenings a week", "pregnancies": 2,
                              "previous_well_woman_visit": "2025-08-20",
                              "symptom_logging": "none — she has never used Oura tags or a symptom tracker"},
        "cycle_history": cycles,
        "in_her_words": "I keep waking up around 3 AM, hot and sweaty. I figured it was work stress.",
        "story": [
            {"when": "2026-07-06 → 2026-08-02", "what": "Baseline. A few warm nights; nothing stands out."},
            {"when": "2026-08 (first half)", "what": "Warm nights with ~3 AM wake-ups become frequent. Cycle lengths start to swing (26 → 38 → 22 days)."},
            {"when": "2026-08-12 → 2026-09-01", "what": "She buys cooling pillowcases, moisture-wicking pajamas, melatonin and a bedside fan."},
            {"when": "2026-08-19", "what": "Books her annual exam for Sep 2 (confirmation email)."},
            {"when": "2026-08-10 → 2026-09-18", "what": "The agent asks a handful of one-tap questions ('Did you have a drink last night?')."},
            {"when": "2026-09-02", "what": "Annual exam with Dr. Elena Ruiz; follow-up booked for Nov 10."},
            {"when": "2026-09-04", "what": "Picks up a new prescription (pharmacy email has no drug name); confirms in one tap it is a new treatment."},
            {"when": "2026-09-04 → 2026-11-04", "what": "Warm nights fall off over ~3 weeks. Drinking stays about the same. Refills on time (Oct 3, Nov 2)."},
            {"when": "2026-10-14 → 2026-10-16", "what": "Work trip to Seattle (flight + hotel emails)."},
            {"when": "2026-11-05 08:12", "what": "LIVE DEMO: the clinic's reminder email for the Nov 10 follow-up arrives → the agent prepares the visit summary."}],
    }
    out = OUT / "profile"
    out.mkdir(exist_ok=True)
    (out / "lisa_profile.json").write_text(json.dumps(prof, indent=1, ensure_ascii=False) + "\n")


def main():
    life = build_life()
    nights = [gen_night(d, i, life[d]) for i, d in enumerate(evenings())]
    write_oura(nights, life)
    write_apple_health(nights)
    gen_restaurant_emails(life)
    gen_wine_club()
    gen_groceries()
    gen_parcelly()
    gen_pharmacy()
    gen_clinic()
    gen_tennis_club()
    gen_travel()
    gen_personal_and_work()
    gen_noise()
    inbox = write_emails()
    write_calendar(life)
    confirmations = write_confirmations(nights, life)
    write_truth(nights, life)
    write_profile()
    heat = sum(observed_night_heat(n) for n in nights)
    print(f"{len(nights)} nights ({heat} with night heat), {len(inbox)} emails + 1 live email, {len(confirmations)} one-tap answers")


if __name__ == "__main__":
    main()
