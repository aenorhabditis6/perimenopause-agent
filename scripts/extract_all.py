#!/usr/bin/env python3
"""Run Claude extraction over every automated email (personal mail is skipped) and cache the result.

    .venv/bin/python scripts/extract_all.py --limit 10     # try 10 first -> cache/extracted_events_first10.json
    .venv/bin/python scripts/extract_all.py                # all -> cache/extracted_events.json (the app switches to it)
"""
import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from app import claude_calls, data  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, help="only the first N automated emails")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    todo = [m for m in data.emails() if not data.is_personal(m)][: args.limit]
    results, errors = {}, {}
    t0 = time.time()
    with ThreadPoolExecutor(args.workers) as pool:
        futures = {pool.submit(claude_calls.extract_event, m): m for m in todo}
        for f in as_completed(futures):
            m = futures[f]
            try:
                results[m["id"]] = f.result()
            except Exception as e:  # noqa: BLE001 - recorded and reported, the rest keep going
                errors[m["id"]] = f"{type(e).__name__}: {e}"
            print(f"\r{len(results) + len(errors)}/{len(todo)}", end="", flush=True)
    print(f"\n{len(results)} ok, {len(errors)} errors in {time.time() - t0:.0f}s")

    data.CACHE.mkdir(exist_ok=True)
    # A partial run never replaces the full cache the app reads
    out = data.CACHE / ("extracted_events.json" if not args.limit else f"extracted_events_first{args.limit}.json")
    events = [results[m["id"]] for m in todo if m["id"] in results]
    out.write_text(json.dumps({"model": claude_calls.MODEL, "events": events, "errors": errors}, indent=1, ensure_ascii=False) + "\n")
    print("wrote", out.relative_to(ROOT))
    for eid, err in errors.items():
        print("  error", eid, err)


if __name__ == "__main__":
    main()
