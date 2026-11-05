#!/usr/bin/env python3
"""Generate a SMALL SYNTHETIC dataset so the pipeline runs end to end.

IMPORTANT: this data is template-based. Metrics on it are NOT meaningful
(expect near-perfect scores). Its only job is to let you test the code.
Replace it with real public datasets before reporting any results
(see data/README.md).

Usage:
    python scripts/make_sample_data.py --n-per-class 300
"""
import argparse
import csv
import random
from pathlib import Path

# label 1 = smishing / phishing
SMISHING_WITH_LINK = [
    "Dear customer, your bank account will be blocked today. Complete KYC update now: {link}",
    "URGENT: your KYC has expired. Update immediately to avoid account suspension {link}",
    "Congratulations! You have won Rs {amt} in our lucky draw. Claim your prize now {link}",
    "Your courier is on hold due to an incomplete address. Update details and pay Rs {small} fee: {link}",
    "Your UPI account is suspended. Verify now to reactivate: {link}",
    "Income tax refund of Rs {amt} approved. Submit your bank details here {link} to receive it",
    "Your SIM will be deactivated in 24 hours. Verify your details here {link}",
    "Dear user, your reward points worth Rs {amt} expire today. Redeem now {link}",
    "Your parcel could not be delivered. Reschedule and confirm payment here {link}",
    "Security alert: unusual login detected. Confirm your identity within 1 hour {link}",
]
SMISHING_NO_LINK = [
    "Your electricity will be disconnected tonight at 9:30 pm as the previous bill is not updated. Call {phone} immediately",
    "Part time job offer! Earn Rs {amt} daily working from home. Message on WhatsApp {phone}",
    "Your account is blocked. Call {phone} now to avoid permanent closure",
    "You have won a lucky draw of Rs {amt}. Send your bank details to {phone} to claim",
    "Dear customer your KYC is pending, account will be suspended today. Contact {phone} urgently",
]

# label 0 = legitimate
LEGIT = [
    "Your OTP is {otp}. Do not share it with anyone. Valid for 10 minutes.",
    "Rs {amt} debited from your account ending {last4}. If this was not you, call the number on your card.",
    "Hey, are we still meeting at {time} today?",
    "Your order has been shipped and will arrive by {date}.",
    "Reminder: your appointment is on {date} at {time}.",
    "Can you send me the notes from yesterday's class?",
    "Happy birthday {name}! Have a great year ahead.",
    "Your bill of Rs {amt} is due on {date}. Please pay through the official app.",
    "Mom said dinner is at {time}, come home early.",
    "Assignment submission deadline has been extended to {date}.",
    "Thanks for your payment of Rs {amt}. Your receipt is available in the app.",
    "{name}, the lab session is moved to {time}. Bring your laptop.",
]
LEGIT_WITH_LINK = [
    "Your order has been shipped. Track it here {link}",
    "Join the class meeting at {time}: {link}",
    "Your invoice for Rs {amt} is ready. View it here {link}",
    "Notes from today's lecture are uploaded: {link}",
]

PREFIXES = ["", "", "", "Alert: ", "Hi, ", "Notice: ", "Dear customer, "]
SUFFIXES = ["", "", "", " Thanks", " Regards", " Please ignore if done"]


def fill(template: str, rng: random.Random) -> str:
    chars = "abcdefghijklmnopqrstuvwxyz0123456789"
    return template.format(
        link=rng.choice(["bit.ly/", "tinyurl.com/", "secure-check.example/", "verify-now.example/"])
        + "".join(rng.choices(chars, k=6)),
        amt=rng.choice([500, 1000, 2500, 5000, 10000, 25000, 50000, 100000]),
        small=rng.choice([5, 10, 25, 49]),
        phone="9" + "".join(rng.choices("0123456789", k=9)),
        otp="".join(rng.choices("0123456789", k=6)),
        last4="".join(rng.choices("0123456789", k=4)),
        time=rng.choice(["9 am", "11:30 am", "2 pm", "4:15 pm", "6 pm"]),
        date=rng.choice(["Monday", "Friday", "12 Nov", "20 Nov", "1 Dec"]),
        name=rng.choice(["Priya", "Rahul", "Anil", "Sneha", "Kiran", "Divya"]),
    )


def perturb(text: str, rng: random.Random) -> str:
    text = rng.choice(PREFIXES) + text + rng.choice(SUFFIXES)
    r = rng.random()
    if r < 0.15:
        text = text.lower()
    elif r < 0.25:
        text = text.upper()
    return text


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-per-class", type=int, default=300)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "data" / "sample_messages.csv"))
    args = ap.parse_args()

    rng = random.Random(args.seed)
    rows = []
    for _ in range(args.n_per_class):
        pool = SMISHING_WITH_LINK if rng.random() < 0.7 else SMISHING_NO_LINK
        rows.append((perturb(fill(rng.choice(pool), rng), rng), 1))
    for _ in range(args.n_per_class):
        pool = LEGIT if rng.random() < 0.75 else LEGIT_WITH_LINK
        rows.append((perturb(fill(rng.choice(pool), rng), rng), 0))
    rng.shuffle(rows)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["text", "label"])
        w.writerows(rows)
    print(f"Wrote {len(rows)} synthetic rows to {out} (label 1 = smishing/phishing, 0 = legitimate)")


if __name__ == "__main__":
    main()
