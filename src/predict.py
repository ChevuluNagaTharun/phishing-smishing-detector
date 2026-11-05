#!/usr/bin/env python3
"""Classify one message from the command line.

Usage:
    python src/predict.py "Your KYC has expired, update now: bit.ly/abc123"
"""
import argparse
import json

from detector import explain, load_model, predict


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("text", help="Message text to classify")
    ap.add_argument("--threshold", type=float, default=0.5,
                    help="Lower = catch more phishing but more false alarms")
    args = ap.parse_args()

    model = load_model()
    result = predict(model, args.text, args.threshold)
    result["top_terms"] = explain(model, args.text)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
