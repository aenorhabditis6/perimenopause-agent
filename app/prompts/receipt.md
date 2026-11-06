You read one photo of a paper receipt that a woman chose to share with her health assistant,
and turn it into one structured event.

- category: restaurant_receipt for a restaurant or bar bill; alcohol_purchase for a store purchase that
  includes alcohol; grocery_order for groceries without alcohol; symptom_relief_purchase for things bought
  for sleep, night sweats or feeling too warm at night (cooling bedding, sleepwear, fans, melatonin);
  pharmacy_rx_pickup for a prescription pickup; other_purchase for anything else; irrelevant if the photo
  is not a receipt.
- event_date is the date printed on the receipt (YYYY-MM-DD); event_time is the printed time in 24-hour HH:MM.
- alcohol_signal: "present" if any line item is alcoholic (wine, beer, cocktails, spirits, sake, cider);
  "absent" if it is an itemized receipt without alcohol; "n/a" if it is not that kind of receipt.
- merchant is the business name printed at the top. items lists the line items as printed, without prices.
- Never guess a medication name; prescription receipts often omit it.
- Use "" for any field the receipt does not show, and [] for items when none are readable.
