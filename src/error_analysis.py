#!/usr/bin/env python3
"""List the messages the saved model gets wrong on the TEST split.

Run it with the SAME data file and flags you used for train.py, so it
rebuilds the same test set:

    python src/error_analysis.py --data data/uci_sms.csv --dedupe-normalized

Output: printed examples plus reports/errors.csv (all errors with scores).
"""
import argparse

import pandas as pd
from sklearn.model_selection import train_test_split

from detector import ROOT, load_model
from train import normalize


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "data" / "uci_sms.csv"))
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--dedupe-normalized", action="store_true")
    ap.add_argument("--show", type=int, default=15, help="examples to print per error type")
    args = ap.parse_args()

    df = pd.read_csv(args.data).dropna(subset=["text", "label"])
    df["label"] = df["label"].astype(int)
    key = df["text"].map(normalize) if args.dedupe_normalized else df["text"].str.lower().str.strip()
    df = df.loc[~key.duplicated()].reset_index(drop=True)

    # Same first split as train.py, so this is the same held-out test set.
    _, test = train_test_split(df, test_size=0.2, stratify=df["label"], random_state=args.seed)
    test = test.copy()

    model = load_model()
    test["score"] = model.predict_proba(test["text"])[:, 1]
    test["pred"] = (test["score"] >= args.threshold).astype(int)

    missed = test[(test["label"] == 1) & (test["pred"] == 0)].sort_values("score")
    false_alarms = test[(test["label"] == 0) & (test["pred"] == 1)].sort_values("score", ascending=False)

    print(f"Test messages: {len(test)} | spam: {int(test['label'].sum())} | threshold: {args.threshold}")
    print(f"Missed spam (false negatives): {len(missed)}")
    print(f"False alarms (false positives): {len(false_alarms)}")

    for title, frame in [("MISSED SPAM (lowest score first)", missed),
                         ("FALSE ALARMS (highest score first)", false_alarms)]:
        print(f"\n=== {title} ===")
        if frame.empty:
            print("(none)")
        for _, row in frame.head(args.show).iterrows():
            print(f"[{row['score']:.2f}] {str(row['text'])[:220]}")

    out = ROOT / "reports" / "errors.csv"
    out.parent.mkdir(exist_ok=True)
    pd.concat([missed.assign(error="missed_spam"), false_alarms.assign(error="false_alarm")]).to_csv(out, index=False)
    print(f"\nSaved all errors to {out}")


if __name__ == "__main__":
    main()