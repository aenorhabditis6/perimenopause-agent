# Lisa's synthetic data (for the hackathon demo)

Lisa Hartley is fictional: 46, lives in Oakland, wears an Oura ring, never logs symptoms. All names, merchants and addresses here are made up, and every email address uses the reserved `.example` domain. The data covers 122 nights, 2026-07-06 to 2026-11-04; the clinic reminder on the morning of 11-05 “arrives” during the live demo.

```bash
python3 generate_lisa_data.py      # regenerate all data (seed fixed at 94, same result every time)
python3 analysis/analyze.py        # reference analysis without an LLM, writes analysis/expected_insights.json
python3 preview/build_preview.py   # rebuild the inbox preview page preview/inbox_preview.html
```

To use another seed: `LISA_SEED=7 python3 generate_lisa_data.py`. Seed 94 was picked out of 300: on it, the trigger, the comparison groups and the before-and-after difference are clearest.

## Files

| Path | Contents | Format |
| --- | --- | --- |
| `profile/lisa_profile.json` | Profile, routines, devices, cycle history, story timeline | Custom JSON |
| `emails/emails.json` | The inbox, 134 emails (plain text + HTML bodies) | Gmail-like message list |
| `emails/live_demo_email.json` | The follow-up reminder that arrives during the live demo (11-05 08:12) | Same, one message |
| `emails/eml/*.eml` | The same 135 emails as .eml files, which you can drag into Apple Mail or Outlook | RFC 5322 |
| `calendar/events.json` | Calendar events (tennis, book club, get-togethers, work trips, doctor visits) | Google Calendar API v3 `events.list` |
| `wearables/oura/*.json` | sleep, daily_sleep, daily_readiness, daily_activity, workout, enhanced_tag (empty), personal_info | Oura API v2, field names checked against the official OpenAPI 1.43 |
| `wearables/apple_health/export.xml` | The same nights as recorded by an Apple Watch, plus the period logs from the iPhone | Apple Health export format |
| `app_state/confirmations.json` | The 9 one-tap confirmations Lisa made in the app | Custom JSON |
| `truth/` | **The answer key, for the team only; never feed it to the agent**: what really happened each night, and what should be extracted from each email | CSV / JSON |
| `analysis/analyze.py` | Reference statistics: adapters, the night-heat rule, trigger, before and after, cycles | Python standard library |
| `preview/inbox_preview.html` | A generic inbox UI with an “Agent view” switch and a “simulate new email” button | Single HTML file, double-click to open |

## The story built into the data (actual output of the reference analysis)

| Scene | When | What the data shows |
| --- | --- | --- |
| Noticing | Morning of 08-13 | 5 of the last 14 nights had a hot wake-up; the baseline over the first 28 nights was 0.2 a week |
| Finding the trigger | 07-24 to 09-03 | 6 of 7 evenings with alcohol had a hot night, vs 8 of 32 other nights (p = 0.005). Tennis evenings made no difference (2 of 5, vs 13 of the other 37); the 1 dinner out without alcohol had no hot night |
| Did the change help | New prescription from 09-04 | Hot nights 3.2 → 0.5 a week (08-07 to 09-03 vs 10-08 to 11-04, p = 0.002); drinking stayed at 1.5 evenings a week before and after; time awake at night averaged 44 → 34 minutes |
| Visit summary | Reminder arrives 11-05 | Follow-up on 11-10 (Dr. Elena Ruiz); already tried cooling pillowcases, moisture-wicking pajamas, melatonin, a bedside fan; the last 4 cycles were 26, 38, 22 and 43 days |

The “night heat” rule: that night's `temperature_deviation ≥ +0.30 °C`, and at least one wake-up of 15 minutes or more between 01:30 and 05:00. The Oura and Apple data use the same rule and give exactly the same conclusions.

## Gotchas

- **Oura's `day` is the day she wakes up.** A drink on the evening of 10-14 belongs to the sleep with `day = 10-15`. The synthetic data follows this rule; check it again when connecting real data.
- **Oura's public API has no cycle endpoint** (OpenAPI 1.43 has no cycle or period endpoints). So periods come from the period logs Lisa keeps in Apple Health, a habit she already had.
- **Daylight saving time**: DST ends at 2 AM on 11-01, and timestamps after that are `-08:00`. Compute durations in UTC; don't subtract local times directly.
- **Personal emails are not read**: emails from friends, family and coworkers are filtered out by sender before anything goes to Claude (marked `skip_personal` in the answer key); only automated receipts, bookings and appointments are processed. Clues about social plans come from calendar titles.
- **Drug names never appear in the emails**: the pharmacy emails only say “1 prescription is ready for pickup”; the treatment start date comes from one tap of confirmation by Lisa in the app.
- **A trap email**: the local newsletter on 09-19 mentions the “Oakland Wine Walk”; that's not one of Lisa's plans, and extraction should not count it as drinking evidence.
- **Every HTML email's footer says “Synthetic demo email”**, so even a leaked screenshot shows it's fake data.
