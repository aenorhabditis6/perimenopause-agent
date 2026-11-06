#!/usr/bin/env python3
"""Render a few of Lisa's receipts as phone photos of paper receipts, for the Manual mode demo.

    .venv/bin/python lisa_demo_data/receipt_photos/make_receipt_photos.py

Writes *.jpg plus samples.json (sha256 -> the event the photo should yield), which the app uses
to read a sample photo when Claude is offline. Each photo carries camera EXIF, including a GPS
position, so the demo can show that location metadata is stripped before Claude sees anything.
"""
import hashlib
import json
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
DATA = HERE.parent
FONTS = Path("/System/Library/Fonts/Supplemental")
SAMPLES = [  # (file stem, sender email, email date)
    ("osteria_lucca_aug14", "receipts@osterialucca.example", "2026-08-14"),
    ("mesa_verde_aug07", "receipts@mesaverde.example", "2026-08-07"),
    ("gilded_tap_jul24", "receipts@gildedtap.example", "2026-07-24"),
    ("spice_route_aug28", "receipts@spiceroute.example", "2026-08-28"),
    ("harbor_pharmacy_aug22", "receipts@harborpharmacy.example", "2026-08-22"),
    ("freshcart_aug09", "orders@freshcart.example", "2026-08-09"),
]
GPS = {1: "N", 2: (37.0, 49.0, 30.0), 3: "W", 4: (122.0, 15.0, 12.0)}   # Oakland-ish, fake


def render(lines: list[str], rng: random.Random) -> Image.Image:
    font = ImageFont.truetype(str(FONTS / "Courier New.ttf"), 20)
    bold = ImageFont.truetype(str(FONTS / "Courier New Bold.ttf"), 24)
    small = ImageFont.truetype(str(FONTS / "Courier New.ttf"), 14)
    pw, lh = 640, 30
    ph = 70 + lh * len(lines) + 70
    paper = Image.new("RGB", (pw, ph), (250, 248, 242))
    d = ImageDraw.Draw(paper)
    y = 36
    for k, line in enumerate(lines):
        f = bold if k == 0 else font
        w = d.textlength(line, font=f)
        x = (pw - w) / 2 if k == 0 or not line.strip() else 28
        d.text((x, y), line, font=f, fill=(38, 36, 34))
        y += lh
    d.text((28, ph - 40), "Synthetic demo receipt - fictional business", font=small, fill=(150, 146, 140))
    canvas = Image.new("RGB", (pw + 260, ph + 220), (96, 84, 72))
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rectangle([140, 122, 140 + pw, 122 + ph], fill=(0, 0, 0, 110))
    canvas.paste(shadow.filter(ImageFilter.GaussianBlur(14)), (0, 0), shadow.filter(ImageFilter.GaussianBlur(14)))
    angle = rng.uniform(-3, 3)
    rot = paper.convert("RGBA").rotate(angle, expand=True, resample=Image.BICUBIC)
    canvas.paste(rot, (130 - (rot.width - pw) // 2, 110 - (rot.height - ph) // 2), rot)
    noise = Image.effect_noise(canvas.size, 18).convert("RGB")
    return Image.blend(canvas, noise, 0.06).filter(ImageFilter.GaussianBlur(0.5))


def main():
    emails = json.loads((DATA / "emails/emails.json").read_text())["messages"]
    key = {e["email_id"]: e for e in json.loads((DATA / "truth/email_expected_events.json").read_text())["expected"]}
    rng = random.Random(3)
    out = []
    for stem, sender, day in SAMPLES:
        m = next(e for e in emails if e["from"]["email"] == sender and e["date"].startswith(day))
        lines = [ln for ln in m["body_text"].splitlines() if not ln.lower().startswith(("hi lisa", "receipt powered", "thanks for"))]
        img = render([ln[:52] for ln in lines], rng)
        exif = Image.Exif()
        exif[0x010F], exif[0x0110], exif[0x0132] = "Apple", "Lisa's iPhone", f"{day.replace('-', ':')} 21:58:00"
        exif[0x8825] = GPS
        path = HERE / f"{stem}.jpg"
        img.save(path, "JPEG", quality=86, exif=exif)
        expected = {k: v for k, v in key[m["id"]].items() if k not in ("email_id", "date", "from", "subject", "note")}
        out.append({"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "from_email": m["id"], "expected": expected})
        print(f"{path.name}: {img.size[0]}x{img.size[1]}, {path.stat().st_size // 1024} KB")
    (HERE / "samples.json").write_text(json.dumps({"note": "Sample receipt photos; expected = what reading the photo should yield.",
                                                   "samples": out}, indent=1, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
