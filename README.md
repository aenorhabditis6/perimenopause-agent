# Perimenopause agent (Claude hackathon)

A passive perimenopause agent: it reads wearable data, plus the receipts, bookings and appointments that arrive automatically in her inbox and her calendar, finds her own patterns, and prepares a one-page visit summary for her before her follow-up. Everything in this repo is **synthetic data**; Lisa Hartley is a fictional person.

## Run it

```bash
/opt/homebrew/bin/python3.12 -m venv .venv      # or any Python 3.12
.venv/bin/pip install -r requirements.txt
cp .env.example .env                              # add your ANTHROPIC_API_KEY; never commit .env
.venv/bin/uvicorn app.server:app --reload
```

Open http://127.0.0.1:8000. It also runs without an API key: the top right shows offline mode, extraction uses the answer file, and the cards and the summary use templates. Set `OFFLINE=1` to force offline mode.

## Demo path

Click the four dates at the top in order: **Aug 13** (noticing) → **Aug 23** (trigger) → **Oct 8** (before and after) → **Nov 5**, then click **▶ New email**: the clinic's follow-up reminder arrives and the visit summary streams into the right column. Turn on **Agent view** to see whether each email was read, skipped, or left nothing behind. On each card, click “Why I said this” to open the evidence table; rows that came from an email link back to it.

## Recording the demo video

Click **▶ Play story** at the top (or press P) and the page walks through the story by itself in about 90 seconds, with the agent's first-person “diary” captions at the bottom: 8/13 noticing → 8/23 trigger → 9/4 pharmacy question → 10/8 before and after → 11/5 the follow-up reminder arrives and the summary streams in → Sarah's personal email is not read → Manual mode uploads a receipt (GPS removed) → Full mode's data sources → closing line “logged 0 times, interrupted 13 times”. All numbers in the captions are computed from the current data.

- Press P again or click ■ Stop to stop; press C to hide the captions, for example when you record your own voiceover
- `http://127.0.0.1:8000/?autoplay=1` starts it on load; `&speed=1.5` holds every step 1.5 times as long, which helps with voiceover
- Before recording, run `scripts/precompute.py`, so the card text is written by Claude and the summary has a cached fallback
- A browser window 1440 wide works best; keep the phone visible

## Layout

| Path | Contents |
| --- | --- |
| `app/server.py` | FastAPI: the page and the endpoints (`/api/emails`, `/api/insights?as_of=`, `/api/live-email`, `/api/brief/stream`) |
| `app/data.py` | Data loading, sender filtering, card numbers and template text, the visit summary's input |
| `app/claude_calls.py` | The three Claude calls: email extraction, card text, the visit summary (streamed). Model `claude-opus-5-5` |
| `app/prompts/` | The three system prompts |
| `app/static/index.html` | The frontend: one file, vanilla JS |
| `scripts/` | Batch extraction, evaluation against the answer key, precomputing the cards and the fallback summary |
| `cache/` | Claude's outputs; the app switches to them automatically when present (the demo fallback relies on them too) |
| `lisa_demo_data/` | Synthetic data, the reference statistics `analysis/analyze.py`, the answer key `truth/`. Read its README first |

## Privacy: three modes and a local model

The three modes go from most private to least effort. When the inbox is connected, every email first goes through a **local classification model** (fastText, 363 KB quantized, 0.016 ms per email) that decides on the device what it is. Personal emails stop here and are never sent in any mode. There is one more safeguard: if the model thinks an email has a 10% or higher chance of being personal, it doesn't leave the device either (`PERSONAL_GUARD`).

| Mode | What leaves the device | Who extracts | What she has to do |
| --- | --- | --- | --- |
| **Manual** | Only the receipt photos she uploads herself, with the GPS location and all other metadata removed before sending; the photo isn't kept, only the extracted row | Claude reads the photo | Snap a receipt each time |
| **Filtered** (default) | The full text of emails that the local model judges useful and that fall in categories she ticked (75 of Lisa's 134). With “extract on this device” ticked, no email is sent at all, only the structured rows | Claude, or on-device rules | Tick categories once |
| **Full** | Every email except personal ones (98), and every data source, including Places: the location app on the phone uploads only restaurant and bar visits (place name, type, arrival and departure time, no coordinates); Card transactions: only restaurant, liquor-store and pharmacy charges are uploaded, with amounts as ranges | Claude | Nothing |

On Lisa's data, Filtered with “extract on this device” gives exactly the same findings on all 4 dates as handing the emails to Claude. The cost is that the rules only know email formats they have seen; and turning off a category removes a kind of finding. For example, with pharmacy turned off, the agent doesn't know when treatment started, so there is no “did the change help” card. Manual mode only has the few receipts she uploads, which is usually not enough evidence, so the trigger card doesn't appear; that is its cost.

Places data is in `lisa_demo_data/places/`: we assume a location app already exists that classifies every place on the phone (Google Maps can already classify places); only restaurant and bar visits are uploaded, 31 for Lisa; visits to home, work, friends' homes, the clinic and the pharmacy (305) stay on the phone, and only their count is kept. For Lisa, Places mostly confirms the receipts and the calendar and adds no new findings; it is more useful for someone who goes out in the evening without leaving an email trail.

Card transactions data is in `lisa_demo_data/transactions/` and mimics a spending app like Rocket Money. Rocket Money has no public API; apps like it usually read card charges through a bank-data service such as Plaid, so we built Lisa's 130 charges in Plaid's data format (`on_phone.json`, stays on the phone). The filter on the phone lets only three kinds through: restaurants, liquor stores and pharmacies, 42 charges in all: 31 restaurant charges (11 of them lunches), 7 for alcohol (4 of them the online wine club), 4 at the pharmacy. The agent reads only these 42 (`shared.json`), and each has only the merchant name, the date, an amount range (such as “$100–150”), whether it was in the evening, and whether it was paid in store or online. The other 88 charges (coffee, groceries, gas, online shopping, utilities, streaming, tennis dues, her kid's team fee, flights, hotel) stay on the phone, and only their count is kept.

The rule: an in-store restaurant or liquor-store charge in the evening counts as “maybe drank” for that evening, at the same level as a reservation, the calendar or location, and weaker than a receipt or her own answer; lunches and wine ordered online don't count. When an evening has several clues, the evidence table keeps the first (usually the one that links back to an email) and lists the rest as “also location, card”.

For Lisa, card charges mostly just confirm the receipts and reservations. The new information is three bottles bought at Grand Lake Wine & Spirits on 7/25, 8/29 and 9/26, with no email trail at all. So the evening of 7/25 moves from “no clue” to “maybe drank”, and the trigger card's comparison group goes from 5/33 to 5/32; the finding doesn't change. The pharmacy charges are the same events as the pharmacy emails, so the treatment start date still comes from the emails and her answer; card charges carry no drug name, and the agent doesn't guess one.

```bash
.venv/bin/python lisa_demo_data/transactions/make_transactions.py   # regenerate on_phone.json and shared.json
```

To demo Manual mode: click Manual, then click a sample receipt in the left column (`lisa_demo_data/receipt_photos/`, with fake GPS metadata); the right column shows the extracted row and “GPS location removed”. Without an API key, the sample photos are read from the answer file; reading a new photo needs Claude.

**Local model test results** (trained on 2,600 separately synthesized emails whose merchants, wording and years all differ from Lisa's; tested on Lisa's 135):

- Personal emails misjudged as “useful” that would leave the device: 0
- Useful emails missed: 0 / 76
- Irrelevant emails that would be sent to Claude: 4 (the tennis club newsletter); 0 with the 10% safeguard, still without missing a single useful email
- Overall accuracy 86%; the errors are mostly 14 newsletters or school notices taken for personal emails, which errs on the safe side and leaks nothing
- Tested again with sender names and addresses removed: same accuracy, still 0 leaks and 0 misses, so the model relies on content, not on memorized senders

These numbers come from synthetic data: they only show the pipeline works, not how it would do on a real inbox. A production Private mode could use an on-device LLM on the phone for extraction instead of the current rules.

```bash
.venv/bin/python app/local_model/make_corpus.py   # generate the training emails
.venv/bin/python app/local_model/train.py         # train + test on Lisa's emails → app/local_model/metrics.json
.venv/bin/python scripts/eval_private_mode.py     # Private mode end to end: extraction accuracy + whether findings match the answer key
```

## The Claude step (owner: C)

```bash
.venv/bin/python scripts/extract_all.py --limit 10                              # try 10 emails first
.venv/bin/python scripts/eval_extraction.py cache/extracted_events_first10.json # check against the answer key
.venv/bin/python scripts/extract_all.py                                         # the 75 emails the local model lets through → cache/extracted_events.json
.venv/bin/python scripts/eval_extraction.py
.venv/bin/python scripts/precompute.py                                          # Claude writes the cards + the fallback visit summary
```

Once the full extraction is written, the app switches to Claude's results automatically (the top right shows `events from claude`). The statistics should match the ones from the answer file; if they don't, look at the rows `eval_extraction.py` reports.

The code turns on `fallbacks="default"`: when the safety classifier refuses, the server automatically reruns on another model.

## Who does what, and checkpoints

- **A · Data and statistics**: `lisa_demo_data/analysis/analyze.py`, `app/data.py`, the endpoints.
- **B · Frontend**: `app/static/index.html`: how the timeline, cards, evidence tables and visit summary look.
- **C · Claude and slides**: `app/claude_calls.py`, `app/prompts/`, `scripts/`, then the slides at the end.

Checkpoints (from the start): 1:20 extraction of 10 emails matches the answer key → 3:00 everyone's P0 done → 3:40 the live demo path works end to end → 5:00 on stage. After 3:40, polish only, no new features.

## Rules

- Never commit `.env`; `truth/` is only for the team to check answers and must never be fed to the agent.
- Everyone edits only the files they own; run `git pull --rebase` before pushing.
