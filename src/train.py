#!/usr/bin/env python3
"""Train and compare phishing/smishing text classifiers.

Design choices worth explaining in interviews:
  * Train / validation / test split (60/20/20, stratified). The model is
    CHOSEN on validation and REPORTED on test, so the test set is never used
    for selection (avoids optimistic bias).
  * Duplicates are removed BEFORE splitting so identical messages cannot
    appear in both train and test (data leakage).
  * A trivial keyword-rule baseline is included to show the ML adds value.
  * Metrics are precision, recall, F1 and false-positive rate, not accuracy
    alone, because security data is imbalanced and false alarms cost analyst time.

Usage:
    python src/train.py --data data/sample_messages.csv
"""
import argparse
import json
import re
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parent.parent

KEYWORDS = [
    "kyc", "blocked", "suspend", "verify", "urgent", "prize", "lucky", "claim",
    "refund", "deactivat", "disconnect", "expire", "immediately",
]

URL_RE = re.compile(r"(https?://\S+|www\.\S+|\b[\w-]+\.(?:com|in|net|org|ly|example)\S*)", re.I)


def normalize(text: str) -> str:
    text = URL_RE.sub("<url>", text.lower())
    text = re.sub(r"\d+", "0", text)
    return re.sub(r"\s+", " ", text).strip()


def keyword_baseline(texts) -> np.ndarray:
    return np.array([int(any(k in t.lower() for k in KEYWORDS)) for t in texts])


def metrics(y_true, y_pred) -> dict:
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "false_positive_rate": round(float(fp / (fp + tn)) if (fp + tn) else 0.0, 4),
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
    }


def build_models(seed: int) -> dict:
    lr = lambda: LogisticRegression(max_iter=1000, class_weight="balanced", random_state=seed)
    return {
        "naive_bayes_word": Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), lowercase=True)),
            ("clf", MultinomialNB()),
        ]),
        "logreg_word": Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), lowercase=True)),
            ("clf", lr()),
        ]),
        "logreg_char": Pipeline([
            ("tfidf", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), lowercase=True)),
            ("clf", lr()),
        ]),
    }


def plot_confusion(cm: np.ndarray, title: str, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(4, 3.6))
    ax.imshow(cm, cmap="Blues")
    ax.set_xticks([0, 1], ["legitimate", "phishing"])
    ax.set_yticks([0, 1], ["legitimate", "phishing"])
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    ax.set_title(title, fontsize=10)
    for i in range(2):
        for j in range(2):
            ax.text(j, i, int(cm[i, j]), ha="center", va="center",
                    color="white" if cm[i, j] > cm.max() / 2 else "black")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "data" / "sample_messages.csv"))
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--dedupe-normalized", action="store_true",
                    help="Also drop near-duplicates (URLs and digits masked). Recommended for real datasets.")
    args = ap.parse_args()

    df = pd.read_csv(args.data).dropna(subset=["text", "label"])
    df["label"] = df["label"].astype(int)
    n_raw = len(df)

    key = df["text"].map(normalize) if args.dedupe_normalized else df["text"].str.lower().str.strip()
    df = df.loc[~key.duplicated()].reset_index(drop=True)
    print(f"Rows: {n_raw} raw -> {len(df)} after de-duplication")
    print("Class counts:", df["label"].value_counts().to_dict())

    train_val, test = train_test_split(df, test_size=0.2, stratify=df["label"], random_state=args.seed)
    train, val = train_test_split(train_val, test_size=0.25, stratify=train_val["label"], random_state=args.seed)
    print(f"Split sizes: train={len(train)} val={len(val)} test={len(test)}")

    results = {"keyword_baseline": {
        "val": metrics(val["label"], keyword_baseline(val["text"])),
        "test": metrics(test["label"], keyword_baseline(test["text"])),
    }}

    fitted, best_name, best_f1 = {}, None, -1.0
    for name, pipe in build_models(args.seed).items():
        pipe.fit(train["text"], train["label"])
        fitted[name] = pipe
        v = metrics(val["label"], pipe.predict(val["text"]))
        t = metrics(test["label"], pipe.predict(test["text"]))
        results[name] = {"val": v, "test": t}
        if v["f1"] > best_f1:  # selection uses VALIDATION only
            best_name, best_f1 = name, v["f1"]

    best = fitted[best_name]
    print(f"Selected model (by validation F1): {best_name}")

    (ROOT / "models").mkdir(exist_ok=True)
    (ROOT / "reports").mkdir(exist_ok=True)
    joblib.dump(best, ROOT / "models" / "model.joblib")

    summary = {
        "data_file": str(args.data),
        "rows_raw": n_raw,
        "rows_after_dedup": int(len(df)),
        "split": {"train": len(train), "val": len(val), "test": len(test)},
        "selected_model": best_name,
        "results": results,
    }
    (ROOT / "reports" / "metrics.json").write_text(json.dumps(summary, indent=2))

    lines = ["| Model | Precision | Recall | F1 | False-positive rate |", "|---|---|---|---|---|"]
    for name, r in results.items():
        t = r["test"]
        star = " (selected)" if name == best_name else ""
        lines.append(f"| {name}{star} | {t['precision']} | {t['recall']} | {t['f1']} | {t['false_positive_rate']} |")
    (ROOT / "reports" / "metrics.md").write_text("Test-set results\n\n" + "\n".join(lines) + "\n")

    cm = confusion_matrix(test["label"], best.predict(test["text"]), labels=[0, 1])
    plot_confusion(cm, f"{best_name} (test)", ROOT / "reports" / "confusion_matrix.png")

    print("\n" + "\n".join(lines))
    print("\nSaved: models/model.joblib, reports/metrics.json, reports/metrics.md, reports/confusion_matrix.png")


if __name__ == "__main__":
    main()
