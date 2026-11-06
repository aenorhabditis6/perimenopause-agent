"""The three places the agent uses Claude. All numbers come from app.data; Claude only reads email and writes words."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

import anthropic

MODEL = "claude-opus-5-5"
# On a safety-classifier decline, the API re-runs the request on a fallback model server-side.
FALLBACK = {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}
PROMPTS = Path(__file__).resolve().parent / "prompts"

CATEGORIES = [
    "restaurant_reservation", "restaurant_receipt", "alcohol_purchase", "grocery_order",
    "symptom_relief_purchase", "other_purchase", "pharmacy_rx_ready", "pharmacy_rx_pickup",
    "pharmacy_refill_reminder", "medical_appointment", "appointment_reminder", "medical_portal_notice",
    "exercise_booking", "travel_booking", "hotel_booking", "travel_checkin", "irrelevant",
]
TEXT = {"type": "string"}
EVENT_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": CATEGORIES},
        "event_date": TEXT, "event_time": TEXT, "end_date": TEXT,
        "merchant": TEXT, "provider": TEXT, "visit_type": TEXT,
        "items": {"type": "array", "items": TEXT},
        "alcohol_signal": {"type": "string", "enum": ["present", "absent", "unknown", "n/a"]},
    },
    "required": ["category", "event_date", "event_time", "end_date", "merchant", "provider", "visit_type", "items", "alcohol_signal"],
    "additionalProperties": False,
}
CARD_SCHEMA = {
    "type": "object",
    "properties": {"headline": TEXT, "body": TEXT},
    "required": ["headline", "body"],
    "additionalProperties": False,
}

_client: anthropic.Anthropic | None = None


def client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()  # ANTHROPIC_API_KEY from the environment (.env is loaded by the server)
    return _client


def prompt(name: str) -> str:
    return (PROMPTS / f"{name}.md").read_text()


def _json_reply(resp) -> dict:
    if resp.stop_reason == "refusal":
        raise RuntimeError("refused")
    return json.loads(next(b.text for b in resp.content if b.type == "text"))


def extract_event(email: dict) -> dict:
    """One automated email -> at most one structured event (LifeEvent)."""
    resp = client().beta.messages.create(
        model=MODEL,
        max_tokens=4000,
        **FALLBACK,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": EVENT_SCHEMA}},
        system=prompt("extract"),
        messages=[{"role": "user", "content": (
            f"From: {email['from']['name']} <{email['from']['email']}>\n"
            f"Date: {email['date']}\nSubject: {email['subject']}\n\n{email['body_text']}")}],
    )
    event = _json_reply(resp)
    return {"email_id": email["id"], "relevant": event["category"] not in ("irrelevant", "other_purchase"), **event}


def write_card(kind: str, numbers: dict) -> dict:
    """Headline + body for one insight card, from its numbers only."""
    resp = client().beta.messages.create(
        model=MODEL,
        max_tokens=4000,
        **FALLBACK,
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": CARD_SCHEMA}},
        system=prompt("cards"),
        messages=[{"role": "user", "content": f"Card type: {kind}\nNumbers (final; do not compute new ones):\n{json.dumps(numbers)}"}],
    )
    return _json_reply(resp)


def stream_brief(inp: dict) -> Iterator[str]:
    """The one-page visit summary, streamed as it is written."""
    with client().beta.messages.stream(
        model=MODEL,
        max_tokens=8000,
        **FALLBACK,
        output_config={"effort": "medium"},
        system=prompt("brief"),
        messages=[{"role": "user", "content": "Findings (final numbers; do not compute new ones):\n" + json.dumps(inp, indent=1)}],
    ) as stream:
        yield from stream.text_stream
        if stream.get_final_message().stop_reason == "refusal":
            raise RuntimeError("refused")
