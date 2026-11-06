#!/usr/bin/env python3
"""Private mode, end to end on the device: fastText label -> rules -> events -> the same statistics.

    .venv/bin/python scripts/eval_private_mode.py

Prints extraction accuracy against the answer key and whether the three findings come out the same
as with the answer key, without any email text going to Claude.
"""
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import data  # noqa: E402
from app.local_model import classifier, extract  # noqa: E402


def main():
    key = data.answer_key()
    events, checked, right = [], 0, {"category": 0, "event_date": 0, "alcohol_signal": 0}
    misses = []
    for m in data.emails() + [data.live_email()]:
        label = classifier.classify(m)["label"]
        if label not in classifier.RELEVANT:
            continue
        ev = extract.extract(m, label)
        events.append(ev)
        k = key[m["id"]]
        if not k.get("relevant"):
            continue
        checked += 1
        for f in right:
            want, have = k.get(f), ev.get(f)
            if f == "alcohol_signal" and not want:
                right[f] += 1
                continue
            if want == have:
                right[f] += 1
            else:
                misses.append(f"{m['id']} {f}: want {want!r}, got {have!r} | {m['subject'][:55]}")
    print(f"on-device extraction on {checked} relevant emails:", {f: f"{n}/{checked}" for f, n in right.items()})
    for x in misses:
        print("  ", x)

    path = data.CACHE / "private_events_eval.json"
    data.CACHE.mkdir(exist_ok=True)
    path.write_text(json.dumps({"events": events}, indent=1, ensure_ascii=False))
    for as_of in ("2026-08-13", "2026-08-23", "2026-10-08", "2026-11-05"):
        ref = data.analyze.run_analysis(date.fromisoformat(as_of))
        priv = data.analyze.run_analysis(date.fromisoformat(as_of), "oura", path)

        def sig(r):
            t, c = r["trigger"], r["change"]
            return (r["awareness"] and r["awareness"]["morning"], (t["exposed"]["heat_nights"], t["exposed"]["nights"], t["unexposed"]["heat_nights"], t["unexposed"]["nights"]),
                    c and (c["before"]["heat_per_week"], c["after"]["heat_per_week"], c["confounded"]))
        print(as_of, "same findings as the answer key" if sig(ref) == sig(priv) else f"DIFFERENT: {sig(ref)} vs {sig(priv)}")
    path.unlink()


if __name__ == "__main__":
    main()
