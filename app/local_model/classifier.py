"""On-device email classifier (fastText, quantized). Runs before anything can leave the device.

Ten coarse labels. Only the ones in RELEVANT can ever reach Claude (Auto mode) or the
on-device extractor (Private mode); personal mail and noise stop here.
"""
from __future__ import annotations

import re
import time
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODEL_PATH = HERE / "email_classifier.ftz"

LABELS = ["personal", "noise", "restaurant", "grocery_alcohol", "sleep_purchase", "other_purchase", "pharmacy", "medical", "travel", "exercise"]
RELEVANT = ("restaurant", "grocery_alcohol", "sleep_purchase", "pharmacy", "medical", "travel", "exercise")
SHAREABLE = {  # what a Private-mode user can switch on or off, in the words the UI shows
    "restaurant": "Restaurants & bars", "grocery_alcohol": "Groceries & wine", "sleep_purchase": "Things bought for sleep",
    "pharmacy": "Pharmacy", "medical": "Doctor's appointments", "travel": "Travel", "exercise": "Exercise bookings",
}
MAX_BODY_CHARS = 600   # the model only ever looks at the start of an email
PERSONAL_GUARD = 0.10  # an email the model gives this much chance of being personal never leaves the device
COARSE = {  # answer-key category -> coarse label (for evaluation, and the fallback when fastText is missing)
    "restaurant_reservation": "restaurant", "restaurant_receipt": "restaurant",
    "alcohol_purchase": "grocery_alcohol", "grocery_order": "grocery_alcohol",
    "symptom_relief_purchase": "sleep_purchase", "other_purchase": "other_purchase",
    "pharmacy_rx_ready": "pharmacy", "pharmacy_rx_pickup": "pharmacy", "pharmacy_refill_reminder": "pharmacy",
    "medical_appointment": "medical", "appointment_reminder": "medical", "medical_portal_notice": "medical",
    "travel_booking": "travel", "hotel_booking": "travel", "travel_checkin": "travel",
    "exercise_booking": "exercise", "irrelevant": "noise",
}


def model_text(from_name: str, from_email: str, subject: str, body: str) -> str:
    """One line of lowercase tokens; the same function feeds training and prediction."""
    domain = from_email.split("@")[-1]
    local = from_email.split("@")[0]
    raw = f"{from_name} sender_{local} domain_{domain} {subject} {body[:MAX_BODY_CHARS]}".lower()
    return " ".join(re.findall(r"[a-z0-9_']+|[$%#@→•]", raw))


@lru_cache
def _model():
    import fasttext  # imported lazily so the rest of the app runs without it

    fasttext.FastText.eprint = lambda *a, **k: None   # silence a load-time warning
    return fasttext.load_model(str(MODEL_PATH))


def available() -> bool:
    try:
        return MODEL_PATH.exists() and _model() is not None
    except Exception:  # noqa: BLE001 - missing package or model: the app falls back to the sender rule
        return False


def classify(msg: dict) -> dict:
    """{'label', 'confidence', 'p_personal', 'guarded', 'ms'} for one email dict (emails.json shape)."""
    text = model_text(msg["from"]["name"], msg["from"]["email"], msg["subject"], msg.get("body_text", ""))
    t0 = time.perf_counter()
    labels, probs = _model().predict(text, k=-1)
    ms = round((time.perf_counter() - t0) * 1000, 3)
    p = {lab.removeprefix("__label__"): float(v) for lab, v in zip(labels, probs)}
    top = max(p, key=p.get)
    return {"label": top, "confidence": round(p[top], 3), "p_personal": round(p.get("personal", 0.0), 3),
            "guarded": top in RELEVANT and p.get("personal", 0.0) >= PERSONAL_GUARD, "ms": ms}


def may_leave(loc: dict) -> bool:
    """Only a relevant email the model is not even slightly worried is personal may leave the device."""
    return loc["label"] in RELEVANT and not loc.get("guarded")
