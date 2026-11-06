#!/usr/bin/env python3
"""Compare Claude's extraction with the answer key on the three fields the statistics use.

    .venv/bin/python scripts/eval_extraction.py cache/extracted_events_first10.json
    .venv/bin/python scripts/eval_extraction.py                      # cache/extracted_events.json
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import data  # noqa: E402


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else data.CACHE / "extracted_events.json"
    got = {e["email_id"]: e for e in json.loads(path.read_text())["events"]}
    key = data.answer_key()
    checks = {"category": 0, "event_date": 0, "alcohol_signal": 0}
    totals = dict.fromkeys(checks, 0)
    misses = []
    for eid, g in got.items():
        k = key[eid]
        want_cat = k.get("category") or "irrelevant"
        pairs = [("category", want_cat, g.get("category"))]
        if k.get("relevant") and k.get("event_date"):
            pairs.append(("event_date", k["event_date"], g.get("event_date")))
        if k.get("alcohol_signal"):
            pairs.append(("alcohol_signal", k["alcohol_signal"], g.get("alcohol_signal")))
        for field, want, have in pairs:
            totals[field] += 1
            if want == have:
                checks[field] += 1
            else:
                misses.append((eid, k.get("subject", ""), field, want, have))
    for field in checks:
        if totals[field]:
            print(f"{field:15} {checks[field]}/{totals[field]}  ({100 * checks[field] / totals[field]:.0f}%)")
    for eid, subj, field, want, have in misses:
        print(f"  {eid} {field}: want {want!r}, got {have!r}  | {subj[:60]}")


if __name__ == "__main__":
    main()
