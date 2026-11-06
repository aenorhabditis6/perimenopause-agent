"""Lisa's demo data, the reference analysis, and the text the app falls back to without Claude."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import date
from functools import lru_cache
from pathlib import Path

from app.local_model import classifier, extract

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "lisa_demo_data"
CACHE = ROOT / "cache"

# The demo's date stops and what each one shows ("question": a one-tap question, no card)
STOPS = {"2026-08-13": "awareness", "2026-08-23": "trigger", "2026-09-04": "question", "2026-10-08": "change", "2026-11-05": "brief"}
CARD_KINDS = ("awareness", "trigger", "change")
# Person-to-person mail is never sent to Claude (friends and family, and colleagues)
PERSONAL_DOMAINS = ("mail.example", "fernwoodlabs.example")
# Auto: emails the on-device model calls relevant go to Claude. Private: nothing goes to Claude;
# events are extracted on the device, and only for the kinds of email she chose to share.
SETTINGS = {"mode": "auto", "share": list(classifier.SHAREABLE)}

_spec = importlib.util.spec_from_file_location("lisa_analyze", DATA / "analysis" / "analyze.py")
analyze = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(analyze)


def load_json(path: Path):
    return json.loads(Path(path).read_text())


@lru_cache
def emails() -> list[dict]:
    return load_json(DATA / "emails" / "emails.json")["messages"]


def live_email() -> dict:
    return load_json(DATA / "emails" / "live_demo_email.json")


def is_personal(msg: dict) -> bool:
    return msg["from"]["email"].split("@")[-1] in PERSONAL_DOMAINS


def answer_key() -> dict[str, dict]:
    return {e["email_id"]: e for e in load_json(DATA / "truth" / "email_expected_events.json")["expected"]}


def events_path() -> Path:
    """Claude's extraction once scripts/extract_all.py has run; the answer key until then."""
    p = CACHE / "extracted_events.json"
    return p if p.exists() else DATA / "truth" / "email_expected_events.json"


def events_source() -> str:
    return "claude" if events_path().parent == CACHE else "answer key"


def extracted_by_id() -> dict[str, dict]:
    raw = load_json(events_path())
    return {e["email_id"]: e for e in raw.get("events", raw.get("expected", []))}


@lru_cache
def local_labels() -> dict[str, dict]:
    """The on-device model's label for every email. Falls back to the answer key if fastText is missing."""
    msgs = emails() + [live_email()]
    if classifier.available():
        return {m["id"]: classifier.classify(m) for m in msgs}
    key = answer_key()
    out = {}
    for m in msgs:
        k = key[m["id"]]
        label = "personal" if k.get("prefilter") == "skip_personal" else classifier.COARSE.get(k.get("category") or "irrelevant", "noise")
        out[m["id"]] = {"label": label, "confidence": None, "p_personal": None, "guarded": False, "ms": None, "fallback": True}
    return out


@lru_cache
def on_device_events() -> dict[str, dict]:
    """Private mode: events extracted on the device from emails the local model calls relevant."""
    labels, out = local_labels(), {}
    for m in emails() + [live_email()]:
        loc = labels[m["id"]]
        if classifier.may_leave(loc) and (ev := extract.extract(m, loc["label"])):
            out[m["id"]] = ev
    return out


def email_status(msg: dict, extracted: dict[str, dict]) -> dict:
    loc = local_labels()[msg["id"]]
    label = loc["label"]
    if label == "personal":
        return {"state": "on_device_personal", "local": loc, "event": None}
    if loc.get("guarded"):
        return {"state": "on_device_guard", "local": loc, "event": None}
    if label not in classifier.RELEVANT:
        return {"state": "on_device_nothing", "local": loc, "event": None}
    if SETTINGS["mode"] == "private":
        if label not in SETTINGS["share"]:
            return {"state": "not_shared", "local": loc, "event": None}
        return {"state": "on_device_event", "local": loc, "event": on_device_events().get(msg["id"])}
    e = extracted.get(msg["id"])
    keep = e and e.get("relevant") and e.get("category") not in (None, "irrelevant")
    return {"state": "sent_to_claude", "local": loc,
            "event": {k: v for k, v in e.items() if k not in ("from", "subject", "date", "expected")} if keep else None}


def active_events_path() -> Path:
    """The events the statistics may use in the current mode, written to cache/ for the analysis to read."""
    labels = local_labels()
    if SETTINGS["mode"] == "private":
        evs = [ev for eid, ev in on_device_events().items() if labels[eid]["label"] in SETTINGS["share"]]
        tag = "private_" + hashlib.md5(",".join(sorted(SETTINGS["share"])).encode()).hexdigest()[:8]
    else:
        evs = [e for eid, e in extracted_by_id().items() if eid in labels and classifier.may_leave(labels[eid])]
        tag = f"auto_{events_source().replace(' ', '_')}_{int(events_path().stat().st_mtime)}"
    CACHE.mkdir(exist_ok=True)
    p = CACHE / f"events_{tag}.json"
    if not p.exists():
        p.write_text(json.dumps({"events": evs}, ensure_ascii=False) + "\n")
    return p


def privacy_summary() -> dict:
    labels = local_labels()
    ids = [m["id"] for m in emails()]
    relevant = [i for i in ids if classifier.may_leave(labels[i])]
    personal = sum(labels[i]["label"] == "personal" for i in ids)
    guarded = sum(bool(labels[i].get("guarded")) for i in ids)
    if SETTINGS["mode"] == "auto":
        return {"mode": "auto", "emails": len(ids), "sent_to_claude": len(relevant), "stayed_on_device": len(ids) - len(relevant),
                "personal_on_device": personal, "held_might_be_personal": guarded}
    shared = [i for i in relevant if labels[i]["label"] in SETTINGS["share"] and i in on_device_events()]
    return {"mode": "private", "emails": len(ids), "sent_to_claude": 0, "stayed_on_device": len(ids), "events_shared": len(shared),
            "personal_on_device": personal, "held_might_be_personal": guarded}


def model_info() -> dict:
    p = classifier.HERE / "metrics.json"
    m = load_json(p) if p.exists() else {}
    return {"available": classifier.available(), "kind": "fastText (quantized)", "size_kb": m.get("model_size_kb"),
            "accuracy": m.get("accuracy"), "personal_leaks": m.get("personal_emails_that_would_leave_device"),
            "relevant_missed": m.get("relevant_emails_missed"), "ms_per_email": m.get("median_ms_per_email")}


@lru_cache(maxsize=32)
def insights(as_of: str, source: str = "oura", events_file: str | None = None, unasked: tuple[str, ...] = ()) -> dict:
    return analyze.run_analysis(date.fromisoformat(as_of), source, events_file or events_path(), unasked)


def unasked_questions() -> tuple[str, ...]:
    """In Private mode, questions prompted by an email she did not share were never asked."""
    if SETTINGS["mode"] != "private":
        return ()
    return tuple(q for q, label in (("treatment", "pharmacy"), ("reservation", "restaurant")) if label not in SETTINGS["share"])


def fired(kind: str, res: dict) -> bool:
    """Has this card's rule been met (see the thresholds at the top of analyze.py)?"""
    if kind == "awareness":
        return bool(res["awareness"])
    if kind == "trigger":
        return res["trigger"]["fires"]
    return bool(res["change"] and res["change"]["fires"])


def cached_cards() -> dict:
    p = CACHE / "cards.json"
    return load_json(p) if p.exists() else {}


# ---------------------------------------------------------------- cards

def card_numbers(kind: str, res: dict) -> dict:
    """The numbers one card may use. Claude writes the words; it never sees anything else."""
    t, ch = res["trigger"], res["change"]
    if kind == "awareness":
        a = res["awareness"]
        return {"heat_nights_last_14": a["heat_nights_last_14"], "baseline_heat_nights_first_28": res["baseline"]["heat_nights"]}
    if kind == "trigger":
        ten = t["controls"][0]
        return {"alcohol_nights": t["exposed"]["nights"], "alcohol_nights_with_heat": t["exposed"]["heat_nights"],
                "other_nights": t["unexposed"]["nights"], "other_nights_with_heat": t["unexposed"]["heat_nights"], "p_value": t["fisher_p"],
                "tennis_nights": ten["exposed"]["nights"], "tennis_nights_with_heat": ten["exposed"]["heat_nights"]}
    if kind == "change":
        return {"change_start": ch["start"], "heat_per_week_before": ch["before"]["heat_per_week"], "heat_per_week_after": ch["after"]["heat_per_week"],
                "alcohol_per_week_before": ch["before"]["alcohol_likely_per_week"], "alcohol_per_week_after": ch["after"]["alcohol_likely_per_week"],
                "drinking_also_changed": ch["confounded"], "p_value": ch["fisher_p"]}
    raise ValueError(kind)


def fallback_card(kind: str, res: dict) -> dict:
    n = card_numbers(kind, res)
    if kind == "awareness":
        return {"headline": "Your nights have changed",
                "body": f"In the last two weeks you woke up hot in the small hours on {n['heat_nights_last_14']} nights. "
                        f"In the month before, that happened on {n['baseline_heat_nights_first_28']}. This pattern is common in the "
                        "menopause transition, though other things can cause it too. Want me to keep an eye on it?"}
    if kind == "trigger":
        return {"headline": "Nights after a drink look different",
                "body": f"On evenings with alcohol, {n['alcohol_nights_with_heat']} of {n['alcohol_nights']} nights had a hot wake-up; "
                        f"on other evenings, {n['other_nights_with_heat']} of {n['other_nights']}. Tennis evenings made no difference "
                        f"({n['tennis_nights_with_heat']} of {n['tennis_nights']}). Alcohol is a common hot-flash trigger. "
                        "Want to try skipping it at your next dinner out and see?"}
    start = date.fromisoformat(n["change_start"])
    head = f"Since you started the new prescription on {start:%b} {start.day}, hot wake-ups went from {n['heat_per_week_before']} to {n['heat_per_week_after']} a week."
    if n["drinking_also_changed"]:
        tail = (f" You also had fewer evenings with alcohol ({n['alcohol_per_week_before']} → {n['alcohol_per_week_after']} a week), "
                "so I can't tell yet which one helped. I'll keep watching.")
    else:
        tail = f" Your drinking stayed about the same ({n['alcohol_per_week_before']} → {n['alcohol_per_week_after']} a week), so that isn't the reason."
    return {"headline": "Fewer hot nights", "body": head + tail}


def card(kind: str, as_of: str, res: dict) -> dict:
    text = cached_cards().get(f"{as_of}:{kind}") or fallback_card(kind, res)
    why = {"awareness": lambda: res["awareness"]["evidence"], "trigger": lambda: res["trigger"]["evidence"],
           "change": lambda: [res["change"]["before"], res["change"]["after"]]}[kind]()
    return {"kind": kind, "as_of": as_of, **text, "numbers": card_numbers(kind, res), "why": why,
            "written_by": "claude" if f"{as_of}:{kind}" in cached_cards() else "template"}


# ---------------------------------------------------------------- visit summary

def brief_input(res: dict, appointment: dict | None = None) -> dict:
    """Everything the visit summary may say, and nothing else."""
    t, ch = res["trigger"], res["change"]
    return {
        "appointment": appointment or res["next_appointment"],
        "change": ch and {k: ch[k] for k in ("change", "start", "before", "after", "fisher_p", "confounded")},
        "pattern_before_treatment": {"window": t["window"], "alcohol": t["exposed"], "other": t["unexposed"], "p_value": t["fisher_p"],
                                     "tennis_control": t["controls"][0]},
        "first_noticed": res["awareness"] and {k: res["awareness"][k] for k in ("morning", "heat_nights_last_14", "baseline_rate_per_week")},
        "cycle_lengths_days": res["cycles"]["lengths_days"][-4:],
        "recent_habits": res["recent_habits"],
        "medications": res["medications"],
        "already_tried": [x for x in res["already_tried"] if x["merchant"] != "Harbor Pharmacy"],
    }


def fallback_brief(inp: dict) -> str:
    ap, ch, pat, rh, med = inp["appointment"], inp["change"], inp["pattern_before_treatment"], inp["recent_habits"], inp["medications"]

    def d(s):
        x = date.fromisoformat(s)
        return f"{x:%b} {x.day}"

    rx = med["prescription"]
    title = f"## Visit summary for {ap['provider']}: {ap['visit_type']}, {d(ap['event_date'])} at {ap['event_time']}" if ap else "## Visit summary"
    lines = [title, "", "Prepared from Lisa's ring, calendar and inbox. Not a diagnosis.", ""]
    if ch:
        lines += [
            f"### Since the new prescription ({d(ch['start'])})",
            f"- Hot wake-ups at night: {ch['before']['heat_per_week']} a week ({d(ch['before']['from'])}–{d(ch['before']['to'])}) → "
            f"{ch['after']['heat_per_week']} a week ({d(ch['after']['from'])}–{d(ch['after']['to'])}).",
            f"- Time awake at night: {ch['before']['avg_awake_min']} → {ch['after']['avg_awake_min']} minutes on average.",
            f"- Evenings with alcohol: {ch['before']['alcohol_likely_per_week']} → {ch['after']['alcohol_likely_per_week']} a week"
            + (", so drinking less doesn't explain the change." if not ch["confounded"] else "."), ""]
    if pat["alcohol"]["nights"]:
        lines += [
            "### Pattern found before the prescription" if ch else "### Pattern found",
            f"- Evenings with alcohol: {pat['alcohol']['heat_nights']} of {pat['alcohol']['nights']} nights had a hot wake-up, "
            f"vs {pat['other']['heat_nights']} of {pat['other']['nights']} other nights.",
            f"- Tennis evenings made no difference ({pat['tennis_control']['exposed']['heat_nights']} of {pat['tennis_control']['exposed']['nights']}).", ""]
    lines += [
        "### Cycle",
        f"- Recent cycle lengths: {', '.join(map(str, inp['cycle_lengths_days']))} days.",
        "",
        f"### Recent habits and medications ({d(rh['from'])}–{d(rh['to'])})",
        f"- Evenings with alcohol: {rh['alcohol_evenings']} ({rh['alcohol_per_week']} a week); dinners out: {rh['dinners_out']}; tennis: {rh['tennis_evenings']} evenings; travel: {rh['travel_nights']} nights.",
    ]
    if rx["first_fill"]:
        lines.append(f"- Prescription: first fill {d(rx['first_fill'])}, refills {', '.join(d(x) for x in rx['refills']) or 'none yet'} (name not in the pharmacy emails).")
    lines += [f"- Over the counter: {x['item']} ({d(x['date'])})." for x in med["over_the_counter"]]
    lines += ["", "### Already tried"] + [f"- {x['item']} ({d(x['date'])})" for x in inp["already_tried"]]
    lines += ["", "### Questions Lisa may want to ask",
              "- Is this improvement what you'd expect, and how long should I stay on it?",
              "- My cycles have become very irregular. Is that expected at this stage?",
              "- Given the pattern with alcohol, is it worth cutting back further?"]
    return "\n".join(lines) + "\n"
