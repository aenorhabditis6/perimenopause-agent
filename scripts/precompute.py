#!/usr/bin/env python3
"""Have Claude write the three cards and a backup visit summary for the demo dates, and cache them.

    .venv/bin/python scripts/precompute.py

The app shows cached card text when it exists (otherwise a template), and replays cache/brief.md
if the live summary does not start streaming within 10 seconds.
"""
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from app import claude_calls, data  # noqa: E402


def main():
    data.CACHE.mkdir(exist_ok=True)
    events = str(data.events_path())
    print("events from", data.events_source())
    cards = {}
    for stop, kind in data.STOPS.items():
        if kind not in data.CARD_KINDS:
            continue
        res = data.insights(stop, "oura", events)
        if not data.fired(kind, res):
            print(f"  {stop} {kind}: rule not met, skipped")
            continue
        cards[f"{stop}:{kind}"] = claude_calls.write_card(kind, data.card_numbers(kind, res))
        print(f"  {stop} {kind}: {cards[f'{stop}:{kind}']['headline']}")
    (data.CACHE / "cards.json").write_text(json.dumps(cards, indent=1, ensure_ascii=False) + "\n")

    inp = data.brief_input(data.insights("2026-11-05", "oura", events))
    text = "".join(claude_calls.stream_brief(inp))
    (data.CACHE / "brief.md").write_text(text)
    print("wrote cache/cards.json and cache/brief.md")


if __name__ == "__main__":
    main()
