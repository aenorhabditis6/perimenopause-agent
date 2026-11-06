#!/usr/bin/env python3
"""Reference analysis for the Lisa demo: plain statistics, no LLM.

Reads the same files the app reads. Until the Claude extraction step has run,
it uses truth/email_expected_events.json as a stand-in for Claude's output.

    python3 analysis/analyze.py                       # Oura, as of the live demo morning
    python3 analysis/analyze.py --source apple        # same analysis from Apple Health
    python3 analysis/analyze.py --events extracted_events.json --as-of 2026-08-25

Writes analysis/expected_insights.json (or --out) for the app and for tests.
"""
from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from math import comb
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# A "night heat" event: warm night AND a long wake-up in the small hours
HEAT_TEMP_C = 0.30
HEAT_WAKE_MIN = 15
HEAT_WINDOW = (90, 300)          # 01:30-05:00 local
BASELINE_NIGHTS = 28
AWARE_WINDOW, AWARE_MIN_NIGHTS = 14, 5
TRIGGER_WINDOW = 42
CHANGE_WINDOW = 28
NOT_SOCIAL = ("tennis", "flight", "soccer", "back-to-school", "trick-or-treat", "dinner —", "qbr", "follow-up", "annual exam", "1:1", "project sync")


def D(s: str) -> date:
    return date.fromisoformat(s[:10])


def heat_from(phases: str, start: datetime, onset_epoch: int, temp_dev: float | None):
    """Return (night_heat, wake blocks as [(local start, minutes)])."""
    blocks, k = [], onset_epoch
    while k < len(phases) - 1:
        if phases[k] == "4":
            j = k
            while j < len(phases) - 1 and phases[j] == "4":
                j += 1
            t = (start.astimezone(timezone.utc) + timedelta(minutes=5 * k)).astimezone(start.tzinfo)
            blocks.append((t, 5 * (j - k)))
            k = j
        else:
            k += 1
    long_small_hours = any(m >= HEAT_WAKE_MIN and HEAT_WINDOW[0] <= t.hour * 60 + t.minute <= HEAT_WINDOW[1] for t, m in blocks)
    return bool(temp_dev is not None and temp_dev >= HEAT_TEMP_C and long_small_hours), blocks


# ---------------------------------------------------------------- adapters

def nights_from_oura(folder: Path) -> list[dict]:
    """Oura assigns a sleep to the day you wake up; the evening before is day - 1."""
    out = []
    for s in json.loads((folder / "sleep.json").read_text())["data"]:
        if s["type"] != "long_sleep":
            continue
        start = datetime.fromisoformat(s["bedtime_start"])
        temp = (s.get("readiness") or {}).get("temperature_deviation")
        heat, blocks = heat_from(s["sleep_phase_5_min"], start, (s["latency"] or 0) // 300, temp)
        out.append({"evening": D(s["day"]) - timedelta(days=1), "temp_dev": temp, "night_heat": heat,
                    "awake_min": (s["awake_time"] or 0) // 60, "longest_wake_min": max([m for _, m in blocks] or [0]),
                    "total_sleep_min": (s["total_sleep_duration"] or 0) // 60})
    return sorted(out, key=lambda n: n["evening"])


def nights_from_apple(xml_path: Path) -> list[dict]:
    """Rebuild 5-minute phases from Apple sleep stages; wrist temperature becomes a deviation from the first 28 nights."""
    code = {"HKCategoryValueSleepAnalysisAsleepDeep": "1", "HKCategoryValueSleepAnalysisAsleepCore": "2",
            "HKCategoryValueSleepAnalysisAsleepREM": "3", "HKCategoryValueSleepAnalysisAwake": "4"}
    fmt = "%Y-%m-%d %H:%M:%S %z"
    inbed, stages, temps = [], [], {}
    for _, el in ET.iterparse(xml_path):
        if el.tag != "Record":
            continue
        t = el.get("type")
        if t == "HKCategoryTypeIdentifierSleepAnalysis":
            a, b = datetime.strptime(el.get("startDate"), fmt), datetime.strptime(el.get("endDate"), fmt)
            (inbed if el.get("value").endswith("InBed") else stages).append((a, b, el.get("value")))
        elif t == "HKQuantityTypeIdentifierAppleSleepingWristTemperature":
            temps[el.get("startDate")] = float(el.get("value"))
        el.clear()
    nights = []
    for a, b, _ in sorted(inbed):
        n_ep = round((b - a).total_seconds() / 300)
        ph = ["4"] * n_ep
        onset = None
        for s0, s1, v in stages:
            if a <= s0 < b:
                k0, k1 = round((s0 - a).total_seconds() / 300), round((s1 - a).total_seconds() / 300)
                for k in range(k0, min(k1, n_ep)):
                    ph[k] = code[v]
                if v != "HKCategoryValueSleepAnalysisAwake":
                    onset = k0 if onset is None else min(onset, k0)
        local = a.astimezone(a.tzinfo)
        nights.append({"start": local, "phases": "".join(ph), "onset": onset or 0, "abs_temp": temps.get(a.strftime(fmt))})
    base = sorted(n["abs_temp"] for n in nights[:BASELINE_NIGHTS] if n["abs_temp"] is not None)
    median = base[len(base) // 2]
    out = []
    for n in nights:
        dev = round(n["abs_temp"] - median, 2) if n["abs_temp"] is not None else None
        heat, blocks = heat_from(n["phases"], n["start"], n["onset"], dev)
        ev = n["start"].date() - (timedelta(days=1) if n["start"].hour < 12 else timedelta(0))
        out.append({"evening": ev, "temp_dev": dev, "night_heat": heat, "awake_min": n["phases"].count("4") * 5,
                    "longest_wake_min": max([m for _, m in blocks] or [0]), "total_sleep_min": (len(n["phases"]) - n["phases"].count("4")) * 5})
    return out


def period_starts_from_apple(xml_path: Path) -> list[date]:
    starts = []
    for _, el in ET.iterparse(xml_path):
        if el.tag == "Record" and el.get("type") == "HKCategoryTypeIdentifierMenstrualFlow":
            meta = {m.get("key"): m.get("value") for m in el.findall("MetadataEntry")}
            if meta.get("HKMenstrualCycleStart") == "1":
                starts.append(D(el.get("startDate")))
        if el.tag == "Record":
            el.clear()
    return sorted(starts)


# ---------------------------------------------------------------- context

def evening_context(events: list[dict], calendar: dict, confirmations: list[dict], workouts: list[dict]):
    """Per evening: alcohol evidence, tennis, travel. Evidence order: one-tap answer > receipt > possible > none."""
    ctx: dict[date, dict] = {}

    def c(d):
        return ctx.setdefault(d, {"evidence": "none", "why": "", "tennis": False, "travel": False, "restaurant": False})

    rank = {"none": 0, "possible": 1, "receipt_no_alcohol": 2, "receipt_alcohol": 2, "confirmed_no": 3, "confirmed_yes": 3}

    def set_ev(d, level, why):
        x = c(d)
        if rank[level] >= rank[x["evidence"]]:
            x["evidence"], x["why"] = level, why

    for e in events:
        cat, ed = e.get("category"), e.get("event_date")
        if not ed:
            continue
        d = D(ed)
        if cat == "restaurant_receipt":
            c(d)["restaurant"] = True
            set_ev(d, "receipt_alcohol" if e.get("alcohol_signal") == "present" else "receipt_no_alcohol", f"receipt: {e.get('merchant')}")
        elif cat == "restaurant_reservation":
            c(d)["restaurant"] = True
            set_ev(d, "possible", f"reservation: {e.get('merchant')}")
        elif cat in ("hotel_booking",):
            x = D(ed)
            while x < D(e.get("end_date") or ed):
                c(x)["travel"] = True
                x += timedelta(days=1)
    for item in calendar.get("items", []):
        st = item.get("start", {}).get("dateTime")
        if not st:
            continue
        t = datetime.fromisoformat(st)
        title = item.get("summary", "")
        if t.hour >= 17 and not any(w in title.lower() for w in NOT_SOCIAL):
            set_ev(t.date(), "possible", f"calendar: {title}")
    for w in workouts:
        t = datetime.fromisoformat(w["start_datetime"])
        if w["activity"] == "tennis" and t.hour >= 17:
            c(t.date())["tennis"] = True
    treatment = None
    for a in confirmations:
        if a["question"].startswith("Did you have a drink"):
            set_ev(D(a["about_evening"]), "confirmed_yes" if a["answer"].startswith("yes") else "confirmed_no", "one-tap answer")
        elif "new treatment" in a["question"] and a["answer"].startswith("yes"):
            treatment = D(a["about_evening"])
    return ctx, treatment


def fisher_two_sided(a: int, b: int, c: int, d: int) -> float:
    """2x2 [[a, b], [c, d]]: rows exposed/unexposed, columns heat/no heat."""
    n, r1, c1 = a + b + c + d, a + b, a + c
    if n == 0:
        return 1.0

    def pr(x):
        return comb(r1, x) * comb(n - r1, c1 - x) / comb(n, c1)

    p0 = pr(a)
    lo, hi = max(0, c1 - (n - r1)), min(r1, c1)
    return min(1.0, sum(pr(x) for x in range(lo, hi + 1) if pr(x) <= p0 * (1 + 1e-9)))


def rate(rows):
    return (sum(r["night_heat"] for r in rows), len(rows))


def compare(rows, exposed, label):
    ex = [r for r in rows if exposed(r)]
    un = [r for r in rows if not exposed(r)]
    (a, n1), (c_, n2) = rate(ex), rate(un)
    rr = (a / n1) / (c_ / n2) if n1 and n2 and c_ else None
    return {"label": label, "exposed": {"heat_nights": a, "nights": n1}, "unexposed": {"heat_nights": c_, "nights": n2},
            "rate_ratio": round(rr, 2) if rr else None, "fisher_p": round(fisher_two_sided(a, n1 - a, c_, n2 - c_), 4)}


# ---------------------------------------------------------------- analyses

def analyze(nights, ctx, treatment, period_starts, events, as_of: date):
    for n in nights:
        x = ctx.get(n["evening"], {})
        n.update(evidence=x.get("evidence", "none"), why=x.get("why", ""), tennis=x.get("tennis", False), travel=x.get("travel", False),
                 restaurant=x.get("restaurant", False))
    seen = [n for n in nights if n["evening"] < as_of]
    base = seen[:BASELINE_NIGHTS]
    out = {"as_of": as_of.isoformat(), "nights_seen": len(seen),
           "baseline": {"nights": len(base), "heat_nights": sum(n["night_heat"] for n in base),
                        "first": base[0]["evening"].isoformat(), "last": base[-1]["evening"].isoformat()}}

    # 1. awareness: first morning when the last 14 nights hold >= 5 heat nights
    aware = None
    base_rate = out["baseline"]["heat_nights"] / max(1, len(base))
    for k in range(BASELINE_NIGHTS, len(seen)):
        win = seen[k - AWARE_WINDOW + 1: k + 1]
        if base_rate < 0.15 and sum(n["night_heat"] for n in win) >= AWARE_MIN_NIGHTS:
            aware = {"morning": (seen[k]["evening"] + timedelta(days=1)).isoformat(),
                     "heat_nights_last_14": sum(n["night_heat"] for n in win),
                     "baseline_rate_per_week": round(base_rate * 7, 1)}
            break
    out["awareness"] = aware

    # 2. trigger: alcohol nights vs other nights, before treatment
    end = min(as_of, treatment) if treatment else as_of
    win = [n for n in seen if end - timedelta(days=TRIGGER_WINDOW) <= n["evening"] < end]
    likely = {"confirmed_yes", "receipt_alcohol"}
    known = [n for n in win if n["evidence"] != "possible"]
    trig = compare(known, lambda n: n["evidence"] in likely, "alcohol (receipt or one-tap yes) vs no sign of alcohol")
    trig["window"] = [win[0]["evening"].isoformat(), win[-1]["evening"].isoformat()] if win else None
    trig["unclear_nights"] = {"nights": sum(n["evidence"] == "possible" for n in win), "heat_nights": sum(n["night_heat"] for n in win if n["evidence"] == "possible")}
    trig["controls"] = [
        compare(win, lambda n: n["tennis"], "tennis evening vs not"),
        {"label": "dinner out without alcohol", "nights": sum(n["restaurant"] and n["evidence"] in ("receipt_no_alcohol", "confirmed_no") for n in win),
         "heat_nights": sum(n["night_heat"] for n in win if n["restaurant"] and n["evidence"] in ("receipt_no_alcohol", "confirmed_no"))},
    ]
    trig["examples"] = [{"evening": n["evening"].isoformat(), "evidence": n["why"], "night_heat": n["night_heat"]}
                        for n in win if n["evidence"] in likely][:12]
    out["trigger"] = trig

    # 3. change: 28 nights before the treatment vs the last 28 nights
    if treatment and as_of > treatment + timedelta(days=CHANGE_WINDOW):
        pre = [n for n in seen if treatment - timedelta(days=CHANGE_WINDOW) <= n["evening"] < treatment]
        post = [n for n in seen if as_of - timedelta(days=CHANGE_WINDOW) <= n["evening"] < as_of]

        def summ(rows):
            w = len(rows) / 7
            return {"from": rows[0]["evening"].isoformat(), "to": rows[-1]["evening"].isoformat(), "nights": len(rows),
                    "heat_nights": sum(n["night_heat"] for n in rows), "heat_per_week": round(sum(n["night_heat"] for n in rows) / w, 1),
                    "alcohol_likely_per_week": round(sum(n["evidence"] in likely for n in rows) / w, 1),
                    "alcohol_possible_per_week": round(sum(n["evidence"] == "possible" for n in rows) / w, 1),
                    "travel_nights": sum(n["travel"] for n in rows),
                    "avg_awake_min": round(sum(n["awake_min"] for n in rows) / len(rows)),
                    "avg_temp_dev_c": round(sum(n["temp_dev"] for n in rows if n["temp_dev"] is not None) / len(rows), 2)}
        out["change"] = {"change": "new treatment (pharmacy first fill, confirmed in one tap)", "start": treatment.isoformat(),
                         "before": summ(pre), "after": summ(post),
                         "fisher_p": round(fisher_two_sided(sum(n["night_heat"] for n in pre), len(pre) - sum(n["night_heat"] for n in pre),
                                                            sum(n["night_heat"] for n in post), len(post) - sum(n["night_heat"] for n in post)), 4)}
    else:
        out["change"] = None

    # 4. cycles
    st = [s for s in period_starts if s < as_of]
    lengths = [(b - a).days for a, b in zip(st, st[1:])]
    diffs = [abs(b - a) for a, b in zip(lengths, lengths[1:])]
    out["cycles"] = {"starts": [s.isoformat() for s in st], "lengths_days": lengths,
                     "consecutive_differences_days": diffs,
                     "differences_7_or_more_in_last_4": sum(d >= 7 for d in diffs[-4:])}

    # 5. what she has already tried, and what is coming up
    out["already_tried"] = [{"date": e["event_date"], "item": (e.get("items") or [""])[0], "merchant": e.get("merchant")}
                            for e in events if e.get("category") == "symptom_relief_purchase" and D(e["event_date"]) < as_of]
    out["prescription_pickups"] = sorted(e["event_date"] for e in events if e.get("category") == "pharmacy_rx_pickup" and D(e["event_date"]) < as_of)
    upcoming = [e for e in events if e.get("category") in ("medical_appointment", "appointment_reminder") and D(e["event_date"]) >= as_of]
    out["next_appointment"] = min(upcoming, key=lambda e: e["event_date"]) if upcoming else None
    if out["next_appointment"]:
        out["next_appointment"] = {k: out["next_appointment"].get(k) for k in ("event_date", "event_time", "provider", "specialty", "visit_type")}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["oura", "apple"], default="oura")
    ap.add_argument("--events", default=str(ROOT / "truth" / "email_expected_events.json"))
    ap.add_argument("--as-of", default="2026-11-05")
    ap.add_argument("--out", default=str(ROOT / "analysis" / "expected_insights.json"))
    args = ap.parse_args()
    as_of = D(args.as_of)

    raw = json.loads(Path(args.events).read_text())
    events = [e for e in raw.get("expected", raw.get("events", [])) if e.get("relevant")]
    calendar = json.loads((ROOT / "calendar" / "events.json").read_text())
    confirmations = [a for a in json.loads((ROOT / "app_state" / "confirmations.json").read_text())["confirmations"]
                     if D(a["asked_at"]) <= as_of]
    workouts = json.loads((ROOT / "wearables" / "oura" / "workout.json").read_text())["data"]
    apple = ROOT / "wearables" / "apple_health" / "export.xml"
    nights = nights_from_oura(ROOT / "wearables" / "oura") if args.source == "oura" else nights_from_apple(apple)
    ctx, treatment = evening_context(events, calendar, confirmations, workouts)
    res = analyze(nights, ctx, treatment, period_starts_from_apple(apple), events, as_of)
    res["source"] = args.source
    Path(args.out).write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n")

    t, ch = res["trigger"], res["change"]
    print(f"[{args.source}] as of {res['as_of']}: {res['nights_seen']} nights; baseline {res['baseline']['heat_nights']}/{res['baseline']['nights']} heat nights")
    print("awareness:", res["awareness"])
    print(f"trigger {t['window']}: alcohol {t['exposed']['heat_nights']}/{t['exposed']['nights']} vs other {t['unexposed']['heat_nights']}/{t['unexposed']['nights']}"
          f"  RR={t['rate_ratio']} p={t['fisher_p']}  unclear={t['unclear_nights']}")
    for c in t["controls"]:
        print("  control:", c)
    if ch:
        b, a = ch["before"], ch["after"]
        print(f"change since {ch['start']}: heat/week {b['heat_per_week']} -> {a['heat_per_week']} (p={ch['fisher_p']}); "
              f"alcohol likely/week {b['alcohol_likely_per_week']} -> {a['alcohol_likely_per_week']}; possible/week {b['alcohol_possible_per_week']} -> {a['alcohol_possible_per_week']}; "
              f"awake min {b['avg_awake_min']} -> {a['avg_awake_min']}; travel nights {b['travel_nights']} -> {a['travel_nights']}")
    print("cycles:", res["cycles"]["lengths_days"][-5:], "diffs", res["cycles"]["consecutive_differences_days"][-4:])
    print("tried:", [x["item"] for x in res["already_tried"]])
    print("next appointment:", res["next_appointment"])


if __name__ == "__main__":
    main()
