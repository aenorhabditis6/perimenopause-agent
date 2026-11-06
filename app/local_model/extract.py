"""On-device extraction for Private mode: plain rules on top of the classifier's label. No network, no LLM.

Less flexible than Claude (it knows these email shapes, not every shape), but nothing it reads
leaves the device: only the structured event it returns is shared.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
DATE_RE = re.compile(r"\b(?:mon|tue|wed|thu|fri|sat|sun)[a-z]*,\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})(?:,\s+(\d{4}))?", re.I)
TIME_RE = re.compile(r"\b(\d{1,2}):(\d{2})\s*(am|pm)\b", re.I)
ALCOHOL_RE = re.compile(r"\b(wine|chianti|barbera|sauvignon|albari[nñ]o|margarita|sake|beer|singha|ipa|lager|pinot|cabernet|ros[eé]|chardonnay|"
                        r"zinfandel|syrah|grenache|malbec|rioja|prosecco|champagne|cocktail|negroni|mezcal|tequila|whiske?y|bourbon|vodka|spritz|sangria|cider)\b", re.I)
PROVIDER_RE = re.compile(r"\b([A-Z][a-z]+ [A-Z][a-z]+, (?:MD|DO|NP))\b")


def _dates(text: str, ref: date) -> list[date]:
    out = []
    for mon, d, y in DATE_RE.findall(text):
        guess = date(int(y) if y else ref.year, MONTHS.index(mon.lower()[:3]) + 1, int(d))
        if not y and guess < ref - timedelta(days=200):
            guess = guess.replace(year=guess.year + 1)
        out.append(guess)
    return out


def _time(text: str) -> str:
    m = TIME_RE.search(text)
    if not m:
        return ""
    h, mi, ap = int(m.group(1)), int(m.group(2)), m.group(3).lower()
    return f"{(h % 12) + (12 if ap == 'pm' else 0):02d}:{mi:02d}"


def _after_colon(subject: str) -> str:
    m = re.search(r":\s*(.+?)(?:,\s*(?:mon|tue|wed|thu|fri|sat|sun)\b|\s+on\s+|$)", subject, re.I)
    return m.group(1).strip() if m else ""


def extract(msg: dict, label: str) -> dict | None:
    """Structured event for one email the classifier labelled `label`; None for labels that carry nothing."""
    subject, body, sender = msg["subject"], msg.get("body_text", ""), msg["from"]["name"]
    ref = date.fromisoformat(msg["date"][:10])
    dates = _dates(body, ref)
    first = (dates[0] if dates else ref).isoformat()
    ev = {"email_id": msg["id"], "relevant": True, "category": "", "event_date": first, "event_time": _time(body), "end_date": "",
          "merchant": re.sub(r"\s+via\s+\w+$", "", sender), "items": [], "alcohol_signal": "n/a", "provider": "", "visit_type": "",
          "extracted_by": "on-device rules"}
    low = (subject + "\n" + body).lower()
    if label == "restaurant":
        if re.search(r"\b(subtotal|total|receipt)\b", low):
            ev.update(category="restaurant_receipt", alcohol_signal="present" if ALCOHOL_RE.search(body) else "absent")
        else:
            ev.update(category="restaurant_reservation", alcohol_signal="unknown", merchant=_after_colon(subject) or ev["merchant"])
    elif label == "grocery_alcohol":
        wine = ALCOHOL_RE.search(sender + "\n" + subject + "\n" + body)
        ev.update(category="alcohol_purchase" if wine else "grocery_order", alcohol_signal="present" if wine else "absent",
                  event_date=(dates[0] if dates and "deliver" in low else ref).isoformat())
    elif label in ("sleep_purchase", "other_purchase"):
        item = _after_colon(subject) if subject.lower().startswith("order confirmed") else next(
            (ln.split("  ")[0].strip() for ln in body.splitlines() if re.search(r"melatonin|magnesium|sleep|valerian", ln, re.I)), "")
        ev.update(category="symptom_relief_purchase" if label == "sleep_purchase" else "other_purchase", items=[item] if item else [],
                  event_date=ref.isoformat(), event_time="", relevant=label == "sleep_purchase")
    elif label == "pharmacy":
        cat = ("pharmacy_rx_ready" if "ready for pickup" in low else "pharmacy_rx_pickup" if re.search(r"picking up|picked up|pickup complete", low)
               else "pharmacy_refill_reminder" if "refill" in low else "pharmacy_rx_ready")
        ev.update(category=cat, event_date=ref.isoformat(), event_time="")
    elif label == "medical":
        if "reminder" in subject.lower():
            cat = "appointment_reminder"
        elif re.search(r"visit summary|patient portal|results", low) and not dates:
            cat = "medical_portal_notice"
        else:
            cat = "medical_appointment"
        p = PROVIDER_RE.search(body)
        ev.update(category=cat, provider=p.group(1) if p else "", visit_type=_after_colon(subject),
                  event_date=(first if cat != "medical_portal_notice" else ref.isoformat()))
    elif label == "travel":
        cat = "travel_checkin" if "check in" in subject.lower() else "hotel_booking" if "check-out" in low else "travel_booking"
        ev.update(category=cat, end_date=dates[1].isoformat() if len(dates) > 1 and cat != "travel_checkin" else "")
    elif label == "exercise":
        ev.update(category="exercise_booking")
    else:
        return None
    return ev
