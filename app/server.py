"""FastAPI app: Lisa's inbox, the agent's cards, and the live path (new email -> visit summary).

    uvicorn app.server:app --reload      # then open http://127.0.0.1:8000

Without ANTHROPIC_API_KEY (or with OFFLINE=1) every Claude step falls back to the answer key,
the cached outputs in cache/, or a template, so the demo always runs.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import queue
import re
import threading
import time
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from app import claude_calls, data  # noqa: E402  (after .env is loaded)
from app.local_model import classifier  # noqa: E402

STATIC = Path(__file__).resolve().parent / "static"
FIRST_TOKEN_TIMEOUT_S = 10
EXTRACT_TIMEOUT_S = 25

app = FastAPI(title="Perimenopause agent demo")
_live = {"event": None, "extracted_by": None, "state": None}


def claude_on() -> bool:
    return os.getenv("OFFLINE") != "1" and bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"))


def _insights(as_of: str, source: str = "oura") -> dict:
    return data.insights(as_of, source, str(data.active_events_path()), data.unasked_questions(), data.use_calendar())


def _key_event(email_id: str) -> dict:
    e = data.answer_key()[email_id]
    return {k: v for k, v in e.items() if k not in ("from", "subject", "date")}


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/status")
def status():
    s = data.SETTINGS
    events_from = ("your receipt photos" if s["mode"] == "manual" else
                   "on-device rules" if s["mode"] == "filtered" and s["on_device"] else data.events_source())
    return {"claude": claude_on(), "events_from": events_from, "stops": data.STOPS,
            "mode": s["mode"], "on_device": s["on_device"], "share": s["share"], "shareable": classifier.SHAREABLE,
            "privacy": data.privacy_summary(), "local_model": data.model_info()}


@app.post("/api/settings")
def settings(body: dict = Body(...)):
    """{"mode": "manual" | "filtered" | "full", "on_device": bool, "share": [labels]}: what may leave the device, and how."""
    mode = {"auto": "filtered", "private": "filtered"}.get(body.get("mode"), body.get("mode", data.SETTINGS["mode"]))
    if mode not in data.MODES:
        raise HTTPException(400, f"mode must be one of {data.MODES}")
    on_device = bool(body.get("on_device", body.get("mode") == "private" or data.SETTINGS["on_device"]))
    share = [s for s in body.get("share", data.SETTINGS["share"]) if s in classifier.SHAREABLE]
    data.SETTINGS.update(mode=mode, on_device=on_device, share=share)
    _live.update(event=None, extracted_by=None, state=None)
    return status()


# ---------------------------------------------------------------- manual mode: receipt photos

@app.get("/api/receipts")
def list_receipts():
    samples = [{"file": s["file"], "url": f"/samples/{s['file']}"} for s in data.sample_receipts().values()]
    return {"receipts": data.receipts(), "samples": samples}


@app.post("/api/receipts")
def upload_receipt(body: dict = Body(...)):
    """{"filename", "data_url"}: strip metadata, read the photo, keep only the structured row."""
    try:
        raw = base64.b64decode(body["data_url"].split(",", 1)[-1])
        jpeg, privacy = data.clean_photo(raw)
    except Exception as e:  # noqa: BLE001 - anything that is not a readable image
        raise HTTPException(400, f"not a readable image: {type(e).__name__}")
    sample = data.sample_receipts().get(hashlib.sha256(raw).hexdigest())
    event, by = None, None
    if claude_on():
        box: dict = {}
        t = threading.Thread(target=lambda: box.update(ev=claude_calls.read_receipt(jpeg)), daemon=True)
        t.start()
        t.join(EXTRACT_TIMEOUT_S)
        if "ev" in box:
            event, by = box["ev"], "claude (photo)"
    if event is None and sample:
        event, by = dict(sample["expected"]), "sample answer key (Claude offline)" if not claude_on() else "sample answer key (Claude timed out)"
    if event is None:
        raise HTTPException(503, "Reading a new photo needs Claude; set ANTHROPIC_API_KEY (offline mode only knows the sample photos).")
    rows = data.receipts()
    rid = f"rcpt_{len(rows) + 1:03d}_{hashlib.sha256(raw).hexdigest()[:6]}"
    event.update(email_id=None, receipt_id=rid)
    row = {"id": rid, "filename": body.get("filename", "photo.jpg"), "uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "extracted_by": by, "privacy": privacy | {"photo_kept": False}, "event": event}
    data.save_receipts(rows + [row])
    return row


@app.delete("/api/receipts/{rid}")
def delete_receipt(rid: str):
    data.save_receipts([r for r in data.receipts() if r["id"] != rid])
    return {"receipts": data.receipts()}


@app.delete("/api/receipts")
def clear_receipts():
    data.save_receipts([])
    return {"receipts": []}


@app.get("/samples/{name}")
def sample_photo(name: str):
    known = {s["file"] for s in data.sample_receipts().values()}
    if name not in known:
        raise HTTPException(404)
    return FileResponse(data.DATA / "receipt_photos" / name, media_type="image/jpeg")


@app.get("/api/emails")
def emails():
    ex = data.extracted_by_id()
    return [{k: m[k] for k in ("id", "date", "from", "subject", "snippet", "is_read")} | {"status": data.email_status(m, ex)}
            for m in reversed(data.emails())]


@app.get("/api/emails/{email_id}")
def email(email_id: str):
    if email_id == "msg_live":
        st = {"state": _live["state"] or "sent_to_claude", "local": data.local_labels()["msg_live"], "event": _live["event"]}
        return data.live_email() | {"status": st, "extracted_by": _live["extracted_by"]}
    for m in data.emails():
        if m["id"] == email_id:
            return m | {"status": data.email_status(m, data.extracted_by_id())}
    raise HTTPException(404)


@app.get("/api/nights")
def nights(source: str = "oura"):
    return _insights("2026-11-05", source)["nights"]


@app.get("/api/insights")
def insights(as_of: str = "2026-11-05", source: str = "oura"):
    """Cards that have gone out by `as_of`, each as it looked on the day it was sent."""
    res = _insights(as_of, source)
    cards = []
    for stop, kind in data.STOPS.items():
        if kind in data.CARD_KINDS and stop <= as_of:
            r = _insights(stop, source)
            if data.fired(kind, r):
                cards.append(data.card(kind, stop, r))
    return {"as_of": as_of, "source": source, "today": data.STOPS.get(as_of), "cards": cards,
            "confirmations": res["confirmations"], "treatment_start": res["change"] and res["change"]["start"],
            "summary": {k: res[k] for k in ("baseline", "cycles", "recent_habits", "medications", "next_appointment")}}


@app.post("/api/live-email")
def live_email():
    """The clinic's reminder arrives: on-device model first, then Claude or the on-device rules, by mode."""
    m = data.live_email()
    loc = data.local_labels()["msg_live"]
    mode, event = data.SETTINGS["mode"], None
    if mode == "manual":
        state, by = "not_connected", "inbox not connected"
    elif loc["label"] == "personal" or loc.get("guarded"):
        state, by = ("on_device_guard" if loc.get("guarded") else "on_device_personal"), "on-device model"
    elif mode == "filtered" and loc["label"] not in classifier.RELEVANT:
        state, by = "on_device_nothing", "on-device model"
    elif mode == "filtered" and loc["label"] not in data.SETTINGS["share"]:
        state, by = "not_shared", "not shared (your setting)"
    elif mode == "filtered" and data.SETTINGS["on_device"]:
        event, state, by = data.on_device_events().get("msg_live"), "on_device_event", "on-device rules (nothing sent)"
    else:
        state, by = "sent_to_claude", "answer key (offline)"
        if claude_on():
            box: dict = {}
            t = threading.Thread(target=lambda: box.update(ev=claude_calls.extract_event(m)), daemon=True)
            t.start()
            t.join(EXTRACT_TIMEOUT_S)
            if "ev" in box:
                event, by = box["ev"], "claude"
            else:
                by = "answer key (Claude did not answer in time)"
        if event is None:
            event = _key_event("msg_live")
    _live.update(event=event, extracted_by=by, state=state)
    return {"email_id": "msg_live", "local": loc, "state": state, "event": event, "extracted_by": by, "mode": data.SETTINGS["mode"],
            "triggers_brief": bool(event) and event.get("category") in ("appointment_reminder", "medical_appointment")}


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj)}\n\n"


@app.get("/api/brief/stream")
def brief_stream():
    """Server-sent events: {"text": ...} chunks, then {"done": true, "by": ...}."""
    res = _insights("2026-11-05")
    ev = _live["event"] or {}
    appt = {k: ev.get(k) for k in ("event_date", "event_time", "provider", "visit_type")} if ev.get("event_date") else None
    inp = data.brief_input(res, appt and (res["next_appointment"] or {}) | {k: v for k, v in appt.items() if v})

    def replay(text: str, by: str):
        for piece in re.split(r"(\s+)", text):
            yield _sse({"text": piece})
            time.sleep(0.01)
        yield _sse({"done": True, "by": by})

    def gen():
        if not claude_on():
            yield from replay(_cached_brief() or data.fallback_brief(inp), "cache" if _cached_brief() else "template")
            return
        q: queue.Queue = queue.Queue()

        def produce():
            try:
                for chunk in claude_calls.stream_brief(inp):
                    q.put(("text", chunk))
                q.put(("done", None))
            except Exception as e:  # noqa: BLE001 - shown in the stream, then we fall back
                q.put(("error", type(e).__name__))

        threading.Thread(target=produce, daemon=True).start()
        try:
            kind, val = q.get(timeout=FIRST_TOKEN_TIMEOUT_S)
        except queue.Empty:
            kind, val = "error", "timeout"
        if kind == "error":
            yield from replay(_cached_brief() or data.fallback_brief(inp), f"fallback ({val})")
            return
        while kind == "text":
            yield _sse({"text": val})
            kind, val = q.get()
        yield _sse({"done": True, "by": "claude" if kind == "done" else f"claude (stopped: {val})"})

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


def _cached_brief() -> str | None:
    p = data.CACHE / "brief.md"
    return p.read_text() if p.exists() else None
