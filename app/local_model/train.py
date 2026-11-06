#!/usr/bin/env python3
"""Train the on-device email classifier with fastText and test it on Lisa's inbox (held out).

    .venv/bin/python app/local_model/make_corpus.py          # training emails (not Lisa's)
    .venv/bin/python app/local_model/train.py                # train -> email_classifier.ftz + metrics.json
    .venv/bin/python app/local_model/train.py --eval-only    # re-test the saved model
"""
import json
import sys
import tempfile
import time
from collections import Counter, defaultdict
from pathlib import Path

import fasttext

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))

from app.local_model.classifier import COARSE, LABELS, MODEL_PATH, PERSONAL_GUARD, RELEVANT, model_text  # noqa: E402


def lisa_test_set():
    msgs = json.loads((ROOT / "lisa_demo_data/emails/emails.json").read_text())["messages"]
    msgs.append(json.loads((ROOT / "lisa_demo_data/emails/live_demo_email.json").read_text()))
    key = {e["email_id"]: e for e in json.loads((ROOT / "lisa_demo_data/truth/email_expected_events.json").read_text())["expected"]}
    out = []
    for m in msgs:
        k = key[m["id"]]
        label = "personal" if k.get("prefilter") == "skip_personal" else COARSE.get(k.get("category") or "irrelevant", "noise")
        out.append((m, label))
    return out


def train(rows):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        for r in rows:
            f.write(f"__label__{r['label']} {model_text(r['from_name'], r['from_email'], r['subject'], r['body'])}\n")
        train_path = f.name
    model = fasttext.train_supervised(input=train_path, epoch=25, lr=0.5, wordNgrams=2, minn=3, maxn=5,
                                      dim=16, bucket=200_000, loss="softmax", thread=1, verbose=0)
    model.quantize(input=train_path, qnorm=True, retrain=True, cutoff=20_000, verbose=0)
    model.save_model(str(MODEL_PATH))
    return model


def evaluate(model) -> dict:
    test = lisa_test_set()
    confusion = defaultdict(Counter)
    leaves = []          # (true label, may this email leave the device under the personal guard?)
    ms = []
    for m, want in test:
        text = model_text(m["from"]["name"], m["from"]["email"], m["subject"], m.get("body_text", ""))
        t = time.perf_counter()
        labels, probs = model.predict(text, k=-1)
        ms.append((time.perf_counter() - t) * 1000)
        p = {lab.removeprefix("__label__"): float(v) for lab, v in zip(labels, probs)}
        got = max(p, key=p.get)
        confusion[want][got] += 1
        leaves.append((want, got in RELEVANT and p.get("personal", 0.0) < PERSONAL_GUARD))
    correct = sum(confusion[c][c] for c in confusion)
    rel = lambda c: c in RELEVANT  # noqa: E731
    relevant_total = sum(sum(confusion[c].values()) for c in confusion if rel(c))
    return {
        "test_emails": len(test), "test_set": "Lisa's inbox (held out; different senders and phrasing)",
        "accuracy": round(correct / len(test), 3),
        "per_class_recall": {c: f"{confusion[c][c]}/{sum(confusion[c].values())}" for c in LABELS if confusion[c]},
        "personal_emails_that_would_leave_device": sum(n for got, n in confusion["personal"].items() if rel(got)),
        "relevant_emails_missed": f"{sum(n for w in confusion if rel(w) for g, n in confusion[w].items() if not rel(g))}/{relevant_total}",
        "noise_emails_that_would_be_sent": sum(n for w in ("noise", "other_purchase") for g, n in confusion[w].items() if rel(g)),
        "with_personal_guard": {
            "rule": f"never send if P(personal) >= {PERSONAL_GUARD}",
            "personal_emails_that_would_leave_device": sum(w == "personal" and ok for w, ok in leaves),
            "relevant_emails_missed": f"{sum(rel(w) and not ok for w, ok in leaves)}/{relevant_total}",
            "noise_emails_that_would_be_sent": sum(w in ("noise", "other_purchase") and ok for w, ok in leaves),
        },
        "model_size_kb": round(MODEL_PATH.stat().st_size / 1024, 1),
        "median_ms_per_email": round(sorted(ms)[len(ms) // 2], 3),
        "errors": [f"{want} → {got} ({n})" for want in confusion for got, n in confusion[want].items() if got != want],
    }


def main():
    rows = [json.loads(line) for line in (HERE / "data/train.jsonl").read_text().splitlines()]
    if "--eval-only" in sys.argv:
        fasttext.FastText.eprint = lambda *a, **k: None
        model, train_s = fasttext.load_model(str(MODEL_PATH)), None
    else:
        t0 = time.time()
        model = train(rows)
        train_s = round(time.time() - t0, 1)
    old = json.loads((HERE / "metrics.json").read_text()) if (HERE / "metrics.json").exists() else {}
    metrics = {"train_emails": len(rows), **evaluate(model), "train_seconds": train_s or old.get("train_seconds")}
    (HERE / "metrics.json").write_text(json.dumps(metrics, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(metrics, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
