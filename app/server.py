"""FastAPI app: Lisa's inbox, the agent's cards, and the live path (new email -> visit summary).

    uvicorn app.server:app --reload      # then open http://127.0.0.1:8000

Without ANTHROPIC_API_KEY (or with OFFLINE=1) every Claude step falls back to the answer key,
the cached outputs in cache/, or a template, so the demo always runs.
"""
from __future__ import annotations

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
    return data.insights(as_of, source, str(data.active_events_path()), data.unasked_questions())


def _key_event(email_id: str) -> dict:
    e = data.answer_key()[email_id]
    return {k: v for k, v in e.items() if k not in ("from", "subject", "date")}


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/status")
def status():
    private = data.SETTINGS["mode"] == "private"
    return {"claude": claude_on(), "events_from": "on-device rules" if private else data.events_source(), "stops": data.STOPS,
            "mode": data.SETTINGS["mode"], "share": data.SETTINGS["share"], "shareable": classifier.SHAREABLE,
            "privacy": data.privacy_summary(), "local_model": data.model_info()}


@app.post("/api/settings")
def settings(body: dict = Body(...)):
    """{"mode": "auto" | "private", "share": [labels]}: what may leave the device, and how."""
    mode = body.get("mode", data.SETTINGS["mode"])
    if mode not in ("auto", "private"):
        raise HTTPException(400, "mode must be auto or private")
    share = [s for s in body.get("share", data.SETTINGS["share"]) if s in classifier.SHAREABLE]
    data.SETTINGS.update(mode=mode, share=share)
    _live.update(event=None, extracted_by=None, state=None)
    return status()


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
    """The clinic's reminder arrives: on-device model -> (Auto) Claude extraction, or (Private) on-device rules."""
    m = data.live_email()
    loc = data.local_labels()["msg_live"]
    event = None
    if loc["label"] not in classifier.RELEVANT:
        state, by = "on_device_nothing", "on-device model"
    elif data.SETTINGS["mode"] == "private":
        if loc["label"] in data.SETTINGS["share"]:
            event, state, by = data.on_device_events().get("msg_live"), "on_device_event", "on-device rules (nothing sent)"
        else:
            state, by = "not_shared", "not shared (your setting)"
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
