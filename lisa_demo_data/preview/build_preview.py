#!/usr/bin/env python3
"""Build preview/inbox_preview.html: a generic mail client over Lisa's synthetic inbox.

    python3 preview/build_preview.py

Embeds emails/emails.json, the live demo email, the extraction answer key and
analysis/expected_insights.json, so the page opens straight from disk.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load(rel):
    return json.loads((ROOT / rel).read_text())


data = {
    "messages": load("emails/emails.json")["messages"],
    "live": load("emails/live_demo_email.json"),
    "expected": {e["email_id"]: e for e in load("truth/email_expected_events.json")["expected"]},
    "insights": load("analysis/expected_insights.json"),
}

PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Lisa's Inbox</title>
<style>
:root {
  --bg: #f6f7f9; --panel: #ffffff; --line: #e6e8ec; --ink: #1f2430; --muted: #6b7280; --faint: #9aa1ad;
  --accent: #5b4b8a; --accent-soft: #efeaf8; --read: #e7f5ee; --read-ink: #0f6b45; --skip: #f1f2f4; --skip-ink: #6b7280;
  --live: #fff6db; --warn-ink: #8a5a00;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink); font: 14px/1.45 -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; height: 100vh; display: flex; flex-direction: column; }
header { height: 54px; display: flex; align-items: center; gap: 14px; padding: 0 18px; background: var(--panel); border-bottom: 1px solid var(--line); }
header .brand { font-weight: 650; letter-spacing: .2px; }
header .who { color: var(--muted); }
header .spacer { flex: 1; }
.switch { display: flex; align-items: center; gap: 8px; cursor: pointer; user-select: none; color: var(--ink); }
.switch input { display: none; }
.switch .track { width: 36px; height: 20px; border-radius: 10px; background: #cfd3da; position: relative; transition: background .15s; }
.switch .track::after { content: ""; position: absolute; top: 2px; left: 2px; width: 16px; height: 16px; border-radius: 50%; background: #fff; transition: left .15s; }
.switch input:checked + .track { background: var(--accent); }
.switch input:checked + .track::after { left: 18px; }
button.live { border: 0; border-radius: 8px; padding: 8px 12px; background: var(--accent); color: #fff; font-weight: 600; cursor: pointer; }
button.live:disabled { opacity: .45; cursor: default; }
main { flex: 1; display: grid; grid-template-columns: 380px 1fr; min-height: 0; }
.list { overflow-y: auto; background: var(--panel); border-right: 1px solid var(--line); }
.list .filters { position: sticky; top: 0; background: var(--panel); border-bottom: 1px solid var(--line); padding: 8px 12px; display: flex; gap: 6px; flex-wrap: wrap; z-index: 1; }
.chipbtn { border: 1px solid var(--line); background: var(--panel); border-radius: 999px; padding: 3px 10px; font-size: 12px; cursor: pointer; color: var(--muted); }
.chipbtn.on { background: var(--accent-soft); border-color: transparent; color: var(--accent); font-weight: 600; }
.item { display: grid; grid-template-columns: 34px 1fr; gap: 10px; padding: 11px 14px; border-bottom: 1px solid var(--line); cursor: pointer; }
.item:hover { background: #fafbfc; }
.item.sel { background: var(--accent-soft); }
.item.new { background: var(--live); animation: pop .6s ease-out; }
@keyframes pop { from { transform: translateY(-10px); opacity: 0; } to { transform: none; opacity: 1; } }
.avatar { width: 34px; height: 34px; border-radius: 50%; display: grid; place-items: center; color: #fff; font-weight: 650; font-size: 13px; }
.row1 { display: flex; gap: 8px; align-items: baseline; }
.from { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.unread .from, .unread .subj { font-weight: 650; }
.when { color: var(--faint); font-size: 12px; white-space: nowrap; }
.subj { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.snip { color: var(--muted); font-size: 12.5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tag { display: none; margin-top: 5px; font-size: 11.5px; border-radius: 6px; padding: 2px 7px; width: fit-content; }
.agent .tag { display: block; }
.tag.read { background: var(--read); color: var(--read-ink); }
.tag.skip { background: var(--skip); color: var(--skip-ink); }
.tag.none { background: #f7f7f8; color: var(--faint); }
.pane { overflow-y: auto; padding: 18px 22px 40px; }
.pane h1 { font-size: 19px; margin: 0 0 6px; }
.meta { color: var(--muted); font-size: 13px; margin-bottom: 14px; }
.agentbox { display: none; border: 1px solid #ddd5ef; background: #fbf9ff; border-radius: 10px; padding: 12px 14px; margin-bottom: 14px; }
.agent .agentbox { display: block; }
.agentbox .head { font-weight: 650; color: var(--accent); margin-bottom: 6px; }
.agentbox table { border-collapse: collapse; font-size: 13px; }
.agentbox td { padding: 2px 14px 2px 0; vertical-align: top; }
.agentbox td:first-child { color: var(--muted); white-space: nowrap; }
.agentbox .why { color: var(--muted); font-size: 12.5px; margin-top: 6px; }
iframe { width: 100%; border: 0; min-height: 560px; background: #f4f4f5; border-radius: 8px; }
pre.plain { white-space: pre-wrap; font: 14px/1.55 -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 16px; }
.brief { border: 1px solid var(--line); background: var(--panel); border-radius: 12px; padding: 18px 20px; margin-bottom: 16px; }
.brief h2 { margin: 0 0 2px; font-size: 17px; }
.brief .sub { color: var(--muted); font-size: 12.5px; margin-bottom: 12px; }
.brief h3 { font-size: 13px; text-transform: uppercase; letter-spacing: .6px; color: var(--accent); margin: 14px 0 6px; }
.brief ul { margin: 0; padding-left: 18px; }
.brief li { margin: 3px 0; }
.brief .note { color: var(--warn-ink); background: #fff8e6; border-radius: 6px; padding: 6px 10px; font-size: 12.5px; margin-top: 12px; }
.empty { color: var(--faint); margin-top: 30vh; text-align: center; }
@media (max-width: 760px) { main { grid-template-columns: 1fr; } .pane { display: none; } .pane.open { display: block; } }
</style>
</head>
<body>
<header>
  <div class="brand">Mail</div>
  <div class="who">lisa.hartley@mail.example</div>
  <div class="spacer"></div>
  <label class="switch"><input type="checkbox" id="agentToggle"><span class="track"></span><span>Agent view</span></label>
  <button class="live" id="liveBtn">▶ Simulate new email</button>
</header>
<main id="main">
  <section class="list" id="list">
    <div class="filters" id="filters"></div>
  </section>
  <section class="pane" id="pane"><div class="empty">Select an email</div></section>
</main>
<script>
const DATA = /*__DATA__*/;
const COLORS = ["#5b4b8a", "#0f766e", "#b45309", "#1d4ed8", "#9d174d", "#15803d", "#7f1d1d", "#334155", "#a16207", "#0369a1"];
const LABELS = {
  restaurant_reservation: "Restaurant reservation", restaurant_receipt: "Restaurant receipt", alcohol_purchase: "Alcohol purchase",
  grocery_order: "Grocery order", symptom_relief_purchase: "Symptom-relief purchase", other_purchase: "Other purchase",
  pharmacy_rx_ready: "Prescription ready", pharmacy_rx_pickup: "Prescription picked up", pharmacy_refill_reminder: "Refill reminder",
  medical_appointment: "Medical appointment", appointment_reminder: "Appointment reminder", medical_portal_notice: "Portal notice",
  exercise_booking: "Exercise booking", travel_booking: "Flight booking", hotel_booking: "Hotel booking", travel_checkin: "Flight check-in",
  irrelevant: "Nothing kept"
};
let messages = DATA.messages.slice().reverse();
let selected = null, filter = "all", liveShown = false;
const list = document.getElementById("list"), pane = document.getElementById("pane"), main = document.getElementById("main");

function colorFor(s) { let h = 0; for (const c of s) h = (h * 31 + c.charCodeAt(0)) >>> 0; return COLORS[h % COLORS.length]; }
function when(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "America/Los_Angeles" });
}
function full(iso) {
  return new Date(iso).toLocaleString("en-US", { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit", timeZone: "America/Los_Angeles" });
}
function exp(m) { return DATA.expected[m.id] || { relevant: false }; }
function tagFor(m) {
  const e = exp(m);
  if (e.prefilter === "skip_personal") return ["skip", "🔒 Skipped · personal email, never read"];
  if (!e.relevant) return ["none", "Checked · nothing kept"];
  let t = "Read · " + (LABELS[e.category] || e.category);
  if (e.alcohol_signal === "present") t += " · alcohol";
  if (e.alcohol_signal === "absent") t += " · no alcohol";
  return ["read", t];
}
function kind(m) { const e = exp(m); return e.prefilter === "skip_personal" ? "skip" : (e.relevant ? "read" : "none"); }

const FILTERS = [["all", "All"], ["read", "Read by agent"], ["skip", "Skipped"], ["none", "Nothing kept"]];
function renderFilters() {
  const f = document.getElementById("filters");
  f.innerHTML = "";
  for (const [k, label] of FILTERS) {
    const n = k === "all" ? messages.length : messages.filter(m => kind(m) === k).length;
    const b = document.createElement("button");
    b.className = "chipbtn" + (filter === k ? " on" : "");
    b.textContent = `${label} ${n}`;
    b.onclick = () => { filter = k; renderList(); };
    f.appendChild(b);
  }
  f.style.display = document.body.classList.contains("agent") ? "flex" : "none";
}

function renderList() {
  renderFilters();
  list.querySelectorAll(".item").forEach(n => n.remove());
  for (const m of messages) {
    if (filter !== "all" && kind(m) !== filter) continue;
    const [cls, txt] = tagFor(m);
    const el = document.createElement("div");
    el.className = "item" + (m.is_read ? "" : " unread") + (selected === m ? " sel" : "") + (m.id === "msg_live" ? " new" : "");
    el.innerHTML = `<div class="avatar" style="background:${colorFor(m.from.name)}">${m.from.name[0]}</div>
      <div style="min-width:0"><div class="row1"><div class="from"></div><div class="when">${when(m.date)}</div></div>
      <div class="subj"></div><div class="snip"></div><div class="tag ${cls}"></div></div>`;
    el.querySelector(".from").textContent = m.from.name;
    el.querySelector(".subj").textContent = m.subject;
    el.querySelector(".snip").textContent = m.snippet;
    el.querySelector(".tag").textContent = txt;
    el.onclick = () => { selected = m; m.is_read = true; renderList(); renderPane(); pane.classList.add("open"); };
    list.appendChild(el);
  }
}

function agentBox(m) {
  const e = exp(m);
  const box = document.createElement("div");
  box.className = "agentbox";
  if (e.prefilter === "skip_personal") {
    box.innerHTML = `<div class="head">Agent: skipped</div><div class="why">Person-to-person mail is filtered out by sender before anything is sent to Claude. Its content is never read or stored.</div>`;
    return box;
  }
  if (!e.relevant) {
    box.innerHTML = `<div class="head">Agent: nothing kept</div><div class="why">Automated sender, so Claude classified it, found no health-relevant event and stored nothing.${e.note ? " (" + e.note + ")" : ""}</div>`;
    return box;
  }
  const rows = [["Type", LABELS[e.category] || e.category]];
  if (e.event_date) rows.push(["When", e.event_date + (e.event_time ? " " + e.event_time : "") + (e.end_date ? " → " + e.end_date : "")]);
  if (e.merchant) rows.push(["Where", e.merchant]);
  if (e.items) rows.push(["Items", e.items.join(", ")]);
  if (e.alcohol_signal) rows.push(["Alcohol", { present: "yes, on the receipt", absent: "no", unknown: "unknown (may ask one tap later)" }[e.alcohol_signal] || e.alcohol_signal]);
  if (e.provider) rows.push(["With", `${e.provider} · ${e.specialty} · ${e.visit_type}`]);
  if (e.related_to) rows.push(["Relevant to", e.related_to]);
  if (e.note) rows.push(["Note", e.note]);
  box.innerHTML = `<div class="head">Agent: stored as a structured event (expected Claude output)</div><table></table><div class="why">Only this row is kept. The email text itself is not stored.</div>`;
  const t = box.querySelector("table");
  for (const [k, v] of rows) { const tr = t.insertRow(); tr.insertCell().textContent = k; tr.insertCell().textContent = v; }
  return box;
}

function briefCard() {
  const I = DATA.insights, ch = I.change, t = I.trigger, ten = t.controls[0], ap = I.next_appointment, cy = I.cycles;
  const d = s => new Date(s + "T12:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric" });
  const el = document.createElement("div");
  el.className = "brief";
  el.innerHTML = `
    <h2>Visit summary for ${ap.provider}: ${ap.visit_type[0].toUpperCase() + ap.visit_type.slice(1)}, ${d(ap.event_date)} at ${ap.event_time}</h2>
    <div class="sub">Sample output for the build. Claude writes this from the numbers in analysis/expected_insights.json. Prepared from Lisa's ring, calendar and inbox; not a diagnosis.</div>
    <h3>Since the new treatment started (${d(ch.start)})</h3>
    <ul>
      <li>Night-heat wake-ups: <b>${ch.before.heat_per_week} per week</b> (${d(ch.before.from)}–${d(ch.before.to)}) → <b>${ch.after.heat_per_week} per week</b> (${d(ch.after.from)}–${d(ch.after.to)}).</li>
      <li>Time awake at night: ${ch.before.avg_awake_min} → ${ch.after.avg_awake_min} minutes on average.</li>
      <li>Evenings with alcohol stayed about the same (${ch.before.alcohol_likely_per_week} → ${ch.after.alcohol_likely_per_week} per week), so drinking less doesn't explain the change.</li>
      <li>Prescription picked up ${I.prescription_pickups.map(d).join(", ")} (first fill, then monthly refills).</li>
    </ul>
    <h3>Pattern found before the treatment</h3>
    <ul>
      <li>Evenings with alcohol: ${t.exposed.heat_nights} of ${t.exposed.nights} nights had a night-heat wake-up, vs ${t.unexposed.heat_nights} of ${t.unexposed.nights} other nights.</li>
      <li>Tennis evenings made no difference (${ten.exposed.heat_nights} of ${ten.exposed.nights} vs ${ten.unexposed.heat_nights} of ${ten.unexposed.nights}).</li>
    </ul>
    <h3>Cycle (from Apple Health)</h3>
    <ul><li>Recent cycle lengths: ${cy.lengths_days.slice(-4).join(", ")} days.</li></ul>
    <h3>Already tried (from purchases)</h3>
    <ul>${I.already_tried.map(x => `<li>${x.item} (${d(x.date)})</li>`).join("")}</ul>
    <h3>Questions Lisa may want to ask</h3>
    <ul><li>Is this improvement what you'd expect, and how long should I stay on it?</li>
        <li>My cycles have become very irregular. Is that expected at this stage?</li>
        <li>Given the pattern with alcohol, is it worth cutting back further?</li></ul>
    <div class="note">Lisa reviews this before her visit and decides whether to share it.</div>`;
  return el;
}

function renderPane() {
  const m = selected;
  pane.innerHTML = "";
  if (!m) { pane.innerHTML = '<div class="empty">Select an email</div>'; return; }
  const h = document.createElement("h1"); h.textContent = m.subject; pane.appendChild(h);
  const meta = document.createElement("div"); meta.className = "meta";
  meta.textContent = `${m.from.name} <${m.from.email}> · ${full(m.date)}`; pane.appendChild(meta);
  if (m.id === "msg_live" && document.body.classList.contains("agent")) {
    const b = document.createElement("div"); b.className = "agentbox";
    b.innerHTML = `<div class="head">Agent: appointment reminder detected → visit summary prepared</div><div class="why">The follow-up is in 5 days. Lisa gets a notification to review the summary below.</div>`;
    pane.appendChild(b); pane.appendChild(briefCard());
  } else {
    pane.appendChild(agentBox(m));
  }
  if (m.body_html) {
    const f = document.createElement("iframe");
    f.setAttribute("sandbox", "");
    f.srcdoc = m.body_html;
    f.onload = () => { try { f.style.height = (f.contentDocument.body.scrollHeight + 30) + "px"; } catch (e) {} };
    pane.appendChild(f);
  } else {
    const pre = document.createElement("pre"); pre.className = "plain"; pre.textContent = m.body_text; pane.appendChild(pre);
  }
}

document.getElementById("agentToggle").onchange = e => { document.body.classList.toggle("agent", e.target.checked); renderList(); renderPane(); };
document.getElementById("liveBtn").onclick = e => {
  if (liveShown) return;
  liveShown = true; e.target.disabled = true;
  const m = Object.assign({}, DATA.live, { is_read: false });
  messages.unshift(m); selected = m; filter = "all";
  renderList(); renderPane(); list.scrollTop = 0;
};
renderList();
</script>
</body>
</html>
"""

html_out = PAGE.replace("/*__DATA__*/", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
(ROOT / "preview" / "inbox_preview.html").write_text(html_out)
print("wrote preview/inbox_preview.html", f"({len(html_out) // 1024} KB)")
