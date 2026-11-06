#!/usr/bin/env python3
"""Training emails for the on-device classifier.

Deliberately NOT Lisa's inbox: different merchants, people, phrasings and year (2025), so that
Lisa's 135 emails stay a held-out test set. Still synthetic: the accuracy it yields says the
pipeline works, not how it would do on a real inbox.

    .venv/bin/python app/local_model/make_corpus.py      # -> app/local_model/data/train.jsonl
"""
import json
import random
from datetime import date, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parent / "data" / "train.jsonl"
rng = random.Random(7)
PER_CLASS = 260

FIRST = ["Maya", "Jordan", "Priya", "Elena", "Sam", "Chris", "Nadia", "Tom", "Aiko", "Luis", "Rachel", "Ben", "Fatima", "Grace", "Omar", "Hannah", "Dev", "Claire", "Marco", "Yuki"]
LAST = ["Okafor", "Brennan", "Shah", "Morales", "Weiss", "Kowalski", "Haddad", "Nakamura", "Costa", "Lindgren", "Reyes", "Fischer", "Osei", "Dubois"]
PERSONAL_DOMAINS = ["inbox.example", "postbox.example", "home.example", "mymail.example"]
WORK_DOMAINS = ["northpeak.example", "brightline.example", "cobaltworks.example"]
RESTAURANTS = ["Juniper Table", "Casa Olivo", "The Copper Pot", "Kumo Ramen", "Little Fig", "Harbor & Rye", "Saffron House", "Trattoria Bella", "Blue Door Bistro", "Pho Saigon", "El Farolito", "The Oak Room"]
PLATFORMS = [("SeatSnap", "noreply@seatsnap.example"), ("DineDash", "reservations@dinedash.example"), ("Reservo", "hello@reservo.example")]
DRINKS = ["Glass of Pinot Noir", "Bottle of Rioja", "Negroni", "Draft IPA", "Prosecco", "Old Fashioned", "Glass of Chardonnay", "Sangria pitcher", "Mezcal margarita", "Hot sake"]
SOFT = ["Iced tea", "Lemonade", "Sparkling water", "Kombucha", "Diet soda", "Mango lassi", "Club soda"]
FOOD = ["Roast chicken", "Margherita pizza", "Spicy tuna roll", "Caesar salad", "Pad thai", "Lamb chops", "Mushroom risotto", "Fish tacos", "Ramen", "Burger", "Crème brûlée", "Tiramisu"]
GROCERS = [("GreenBasket", "orders@greenbasket.example"), ("PantryNow", "receipts@pantrynow.example"), ("Corner Market Delivery", "orders@cornermarket.example")]
WINESHOPS = [("Vineyard Box", "club@vineyardbox.example"), ("Bottle Shop Co.", "orders@bottleshop.example")]
WINES = ["2022 Malbec", "2023 Sauvignon Blanc", "2021 Rioja Reserva", "Prosecco DOC", "2022 Grenache", "Craft lager 6-pack", "Hard cider 4-pack"]
GROCERY = ["Milk", "Eggs", "Bread", "Apples", "Rice", "Chicken breast", "Spinach", "Yogurt", "Pasta", "Tomatoes", "Cheese", "Oats", "Bananas", "Coffee", "Tofu", "Salmon"]
STORES = [("ShopRiver", "orders@shopriver.example"), ("Homeward Goods", "orders@homeward.example"), ("QuickCart", "noreply@quickcart.example")]
SLEEP_ITEMS = ["Cooling gel pillow", "Breathable cotton sheets", "Moisture-wicking nightgown", "Desk fan with quiet mode", "Melatonin 5 mg tablets", "Magnesium glycinate capsules", "Cooling mattress topper", "Lightweight summer duvet", "Sleep mask", "White noise machine", "Bamboo sleep shorts", "Chilled pillow insert"]
OTHER_ITEMS = ["Running shoes", "Kids' backpack", "Phone charger", "Cookbook", "Yoga mat", "Water bottle", "Desk lamp", "Printer ink", "Board game", "Rain jacket", "Picture frame", "Headphones"]
PHARMACIES = [("Bayline Pharmacy", "rx@baylinerx.example"), ("Corner Drug", "notify@cornerdrug.example"), ("Wellway Pharmacy", "pharmacy@wellway.example")]
CLINICS = [("Riverside Family Medicine", "appointments@riversidefm.example"), ("Lakeview Women's Clinic", "noreply@lakeviewwc.example"), ("Summit Dermatology", "scheduling@summitderm.example")]
DOCTORS = ["Anna Park, MD", "James Liu, MD", "Sofia Grant, DO", "Rita Menon, NP", "David Cho, MD"]
VISITS = ["Annual physical", "Follow-up visit", "New patient visit", "Telehealth check-in", "Lab work", "Well-woman exam"]
AIRLINES = [("SkyHop Airlines", "itinerary@skyhop.example"), ("Pacifica Air", "noreply@pacifica-air.example")]
HOTELS = [("The Wren Hotel", "stay@wrenhotel.example"), ("Harborline Inn", "reservations@harborline.example")]
AIRPORTS = ["SFO", "OAK", "SEA", "LAX", "PDX", "DEN", "JFK", "BOS"]
GYMS = [("CoreFit Studio", "bookings@corefit.example"), ("Riverside Tennis Center", "courts@riversidetennis.example"), ("Flow Yoga", "classes@flowyoga.example")]
CLASSES = ["Spin class", "Court 3 reservation", "Vinyasa yoga", "Pilates reformer", "HIIT bootcamp", "Doubles clinic", "Swim lesson"]
NEWS = [("City Pulse", "digest@citypulse.example"), ("The Weekend Edit", "news@weekendedit.example"), ("Neighborhood Notes", "updates@neighborhoodnotes.example")]
BILLS = [("Summit Credit Union", "alerts@summitcu.example"), ("ClearWave Internet", "billing@clearwave.example"), ("Metro Water", "billing@metrowater.example"), ("StreamBox", "billing@streambox.example")]
SCHOOLS = [("Maple Elementary", "no-reply@mapleelementary.example"), ("Westside Soccer Club", "team@westsidesoccer.example")]
PROMOS = [("ShopRiver", "deals@shopriver.example"), ("Trailhead Outdoor", "sale@trailhead.example"), ("Bloom Beauty", "hello@bloombeauty.example")]


def person():
    return f"{rng.choice(FIRST)} {rng.choice(LAST)}"


def day():
    return date(2025, 1, 1) + timedelta(days=rng.randrange(0, 360))


def long_d(d):
    return f"{d:%A}, {d:%B} {d.day}, {d.year}"


def short_d(d):
    return f"{d:%a}, {d:%b} {d.day}"


def clock():
    h, m = rng.randint(7, 21), rng.choice([0, 15, 30, 45])
    return f"{h % 12 or 12}:{m:02d} {'AM' if h < 12 else 'PM'}"


def money():
    return f"${rng.uniform(4, 60):.2f}"


def ex(label, sender, subject, body):
    return {"label": label, "from_name": sender[0], "from_email": sender[1], "subject": subject, "body": body}


def personal():
    who = person()
    domain = rng.choice(PERSONAL_DOMAINS + WORK_DOMAINS)
    first = who.split()[0]
    d = day()
    texts = [
        (f"Dinner {short_d(d)}?", f"Hi! Want to grab dinner on {short_d(d)}? Maybe {rng.choice(RESTAURANTS)}, I heard their wine list is great.\n{first}"),
        ("Pickup today", f"Can you get the kids at 4? I'm stuck in a meeting. Thanks!!\n{first}"),
        ("Photos from the weekend", f"Here are the photos from the lake. So fun, let's do it again soon.\n— {first}"),
        ("Thank you!", f"Thanks for having us last night, the food was amazing and the kids loved it.\nxo {first}"),
        ("Quick question", f"Hey, do you still have that recipe? Also are you free {short_d(d)}?\nSent from my phone"),
        ("Re: notes from today", f"Hi,\n\nAttached are my notes from the meeting. Let me know if I missed anything before Friday.\n\nBest,\n{first}"),
        ("Re: budget draft", f"Looks good to me. Can we move the review to {short_d(d)} at {clock()}?\n{first}"),
        ("Book club pick", f"I vote for the mystery one. Bringing snacks and a bottle of red!\n{first}"),
        ("Happy birthday!!", f"Happy birthday! Hope you have the best day. Drinks on me next week 🎉\n{first}"),
        ("Carpool next week", f"I can drive Monday and Wednesday, can you take Thursday?\n{first}"),
    ]
    subj, body = rng.choice(texts)
    return ex("personal", (who, f"{first.lower()}.{who.split()[1].lower()}@{domain}"), subj, f"Hi,\n\n{body}" if rng.random() < .4 else body)


def noise():
    kind = rng.random()
    if kind < .35:
        s = rng.choice(NEWS)
        topic = rng.choice(["Restaurant week is back", "Wine tasting at the waterfront", "Five new cafés to try", "Road closures this weekend",
                            "The best hikes this fall", "Farmers market guide", "Free concerts in the park", "Bar crawl for charity"])
        return ex("noise", s, f"{s[0]}: {topic}", f"This week:\n• {topic}\n• Local events\n• Weather outlook\n\nYou're receiving this because you subscribed. Unsubscribe")
    if kind < .6:
        s = rng.choice(BILLS)
        return ex("noise", s, rng.choice(["Your statement is ready", "Your bill is available", "Autopay scheduled", "Payment received"]),
                  f"Hello,\n\nYour latest statement is ready to view online. Amount due: {money()}. Autopay is on.\n\n{s[0]}")
    if kind < .8:
        s = rng.choice(SCHOOLS)
        return ex("noise", s, rng.choice(["Weekly update", "Picture day reminder", "Schedule change", "Volunteer sign-up"]),
                  f"Dear families,\n\nPlease see this week's announcements and the updated calendar on our website.\n\n{s[0]}")
    s = rng.choice(PROMOS)
    return ex("noise", s, rng.choice(["40% off everything", "Last chance: sale ends tonight", "New arrivals you'll love", "A gift for you"]),
              f"Don't miss out! Shop the sale now. Free shipping over $50.\n\nUnsubscribe · Manage preferences")


def restaurant():
    name, d, t = rng.choice(RESTAURANTS), day(), clock()
    if rng.random() < .5:
        p = rng.choice(PLATFORMS)
        party = rng.randint(2, 6)
        subj = rng.choice([f"Your table at {name} is booked", f"Confirmed: {name} on {short_d(d)}", f"Reservation for {party} at {name}"])
        body = (f"Hi,\n\nYour reservation is confirmed.\n\n{name}\n{long_d(d)} at {t}\nTable for {party}\n\n"
                f"Running late? Let the restaurant know. Modify or cancel in the {p[0]} app.")
        return ex("restaurant", p, subj, body)
    lines = rng.sample(FOOD, rng.randint(1, 3)) + ([rng.choice(DRINKS)] if rng.random() < .6 else [rng.choice(SOFT)])
    body = (f"{name}\nReceipt · {short_d(d)}, {d.year} · {t}\n\n" + "\n".join(f"{rng.randint(1, 2)} x {x}   {money()}" for x in lines) +
            f"\n\nSubtotal {money()}\nTax {money()}\nGratuity {money()}\nTotal {money()}\n\nThank you for dining with us!")
    dom = name.lower().replace(" ", "").replace("&", "and")
    return ex("restaurant", (name, f"receipts@{dom}.example"), rng.choice([f"Receipt from {name}", f"Thanks for visiting {name}", f"{name}: your receipt"]), body)


def grocery_alcohol():
    if rng.random() < .4:
        s = rng.choice(WINESHOPS)
        items = rng.sample(WINES, rng.randint(1, 3))
        d = day()
        return ex("grocery_alcohol", s, rng.choice(["Your shipment is on the way", "Order confirmed", "Your club box has shipped", "Delivered: your order"]),
                  "Hi,\n\nYour order includes:\n" + "\n".join(f"• {x}" for x in items) + f"\n\nArriving {short_d(d)}. Adult signature (21+) required.\n\n{s[0]}")
    s = rng.choice(GROCERS)
    items = rng.sample(GROCERY, rng.randint(5, 10)) + ([rng.choice(WINES)] if rng.random() < .35 else [])
    return ex("grocery_alcohol", s, rng.choice(["Your groceries were delivered", "Order complete", "Your delivery receipt"]),
              "Hi,\n\nYour order was delivered.\n\n" + "\n".join(f"{x}   {money()}" for x in items) + f"\n\nDelivery fee {money()}\nTotal {money()}\n\n{s[0]}")


def purchase(label, items):
    s = rng.choice(STORES)
    item, d = rng.choice(items), day()
    order = f"{rng.randint(100, 999)}-{rng.randint(1000000, 9999999)}"
    return ex(label, s, rng.choice([f"Order confirmed: {item}", f"Your order #{order} has shipped", f"Thanks for your order: {item}"]),
              f"Hello,\n\nThanks for shopping with us. Order #{order}\n\n{item}   {money()}\n\nArriving {short_d(d)}.\n\n{s[0]}")


def sleep_purchase():
    if rng.random() < .25:
        s = rng.choice(PHARMACIES)
        item = rng.choice(["Melatonin 5 mg tablets", "Magnesium glycinate capsules", "Valerian root tea", "Sleep aid gummies"])
        d = day()
        return ex("sleep_purchase", (s[0], s[1].replace("rx@", "receipts@")), f"Your {s[0]} receipt",
                  f"{s[0]}\n{short_d(d)}, {d.year} · {clock()}\n\n{item}   {money()}\nHand cream   {money()}\nTotal {money()}\n\nThank you for shopping with us.")
    return purchase("sleep_purchase", SLEEP_ITEMS)


def other_purchase():
    return purchase("other_purchase", OTHER_ITEMS)


def pharmacy():
    s = rng.choice(PHARMACIES)
    rx = f"{rng.randint(1000, 9999)}-{rng.randint(100, 999)}"
    kind = rng.choice(["ready", "picked", "refill", "transfer"])
    if kind == "ready":
        return ex("pharmacy", s, rng.choice(["Your prescription is ready", "Ready for pickup", "Prescription ready at your pharmacy"]),
                  f"Hi,\n\n{rng.randint(1, 2)} prescription(s) ready for pickup at {s[0]}. For your privacy, medication names are not shown.\n\n{s[0]}")
    if kind == "picked":
        return ex("pharmacy", s, rng.choice(["Thanks for picking up your prescription", "Pickup complete", "Your prescription receipt"]),
                  f"Hi,\n\nThanks for picking up today. Rx #{rx} · Qty {rng.choice([30, 60, 90])} · Copay {money()}\nRefills remaining: {rng.randint(0, 5)}\n\n{s[0]}")
    if kind == "refill":
        return ex("pharmacy", s, rng.choice([f"Refill reminder: Rx #{rx}", "Time to refill", "Your refill is due"]),
                  f"Hi,\n\nRx #{rx} is due for a refill. Reply REFILL or use the app.\n\n{s[0]}")
    return ex("pharmacy", s, "Prescription transfer complete", f"Hi,\n\nYour prescription transfer to {s[0]} is complete. We'll let you know when it's ready.\n\n{s[0]}")


def medical():
    s, doc, visit, d = rng.choice(CLINICS), rng.choice(DOCTORS), rng.choice(VISITS), day()
    kind = rng.choice(["confirm", "remind", "portal", "lab", "resched"])
    if kind == "portal":
        return ex("medical", s, rng.choice(["New message in your patient portal", "Your visit summary is available"]),
                  f"Hello,\n\nYou have a new message from {doc}. For your privacy, sign in to the patient portal to read it.\n\n{s[0]}")
    if kind == "lab":
        return ex("medical", s, "Your test results are available", f"Hello,\n\nNew results from your recent visit are available in the patient portal.\n\n{s[0]}")
    lead = {"confirm": "Your appointment is confirmed.", "remind": "This is a reminder about your upcoming appointment.", "resched": "Your appointment has been rescheduled."}[kind]
    subj = {"confirm": f"Appointment confirmed: {visit}", "remind": f"Reminder: {visit} on {short_d(d)}", "resched": f"Appointment rescheduled to {short_d(d)}"}[kind]
    return ex("medical", s, subj, f"Hello,\n\n{lead}\n\n{visit}\n{long_d(d)} at {clock()}\n{doc}\n\nPlease arrive 15 minutes early. Call us to make changes.\n\n{s[0]}")


def travel():
    kind = rng.choice(["flight", "checkin", "hotel"])
    d = day()
    a, b = rng.sample(AIRPORTS, 2)
    if kind == "hotel":
        s = rng.choice(HOTELS)
        return ex("travel", s, rng.choice([f"Reservation confirmed — {s[0]}", "Your stay is booked", "See you soon!"]),
                  f"Dear guest,\n\nCheck-in: {short_d(d)} (3 PM)\nCheck-out: {short_d(d + timedelta(days=rng.randint(1, 4)))} (11 AM)\nConfirmation {rng.randint(10000000, 99999999)}\n\n{s[0]}")
    s = rng.choice(AIRLINES)
    if kind == "checkin":
        return ex("travel", s, rng.choice(["Check in now for your flight", "Your boarding pass is ready"]),
                  f"Hi,\n\nCheck-in is open for your flight {a} → {b} on {short_d(d)} at {clock()}.\n\n{s[0]}")
    code = "".join(rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6))
    return ex("travel", s, rng.choice([f"Your trip is booked — {code}", f"Flight confirmation {code}", "Itinerary receipt"]),
              f"Hi,\n\nConfirmation code: {code}\n{short_d(d)} · {a} {clock()} → {b}\n{short_d(d + timedelta(days=rng.randint(2, 7)))} · {b} → {a}\n\n{s[0]}")


def exercise():
    s, c, d = rng.choice(GYMS), rng.choice(CLASSES), day()
    return ex("exercise", s, rng.choice([f"Booked: {c}", f"You're in! {c} on {short_d(d)}", "Class reminder"]),
              f"Hi,\n\nYou're booked.\n\n{c}\n{long_d(d)} · {clock()}\nInstructor: {person()}\n\nCancel at least 12 hours ahead.\n\n{s[0]}")


MAKERS = [personal, noise, restaurant, grocery_alcohol, sleep_purchase, other_purchase, pharmacy, medical, travel, exercise]


def main():
    rows = [make() for make in MAKERS for _ in range(PER_CLASS)]
    rng.shuffle(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} emails ({PER_CLASS} per class) to {OUT.relative_to(OUT.parents[3])}")


if __name__ == "__main__":
    main()
