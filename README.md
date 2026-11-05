# Phishing and Smishing Detector

A machine learning tool that classifies SMS and email text as phishing/smishing or legitimate, built with an India-relevant focus (fake KYC, UPI, courier and bill-disconnection scams).

> **Status: Phase 1 (baseline pipeline complete).** The code runs end to end on a small synthetic sample. Real-dataset results are still to be added (see Roadmap). Metrics from the synthetic sample are not meaningful and are not reported as results.

## What it does

- Trains and compares three text classifiers (Naive Bayes, Logistic Regression on words, Logistic Regression on characters) plus a keyword-rule baseline.
- Reports precision, recall, F1 and false-positive rate, not accuracy alone.
- Explains each prediction by showing the terms that pushed the score.
- Serves predictions through a command-line tool, a small web page and a JSON API.

## Quick start

```bash
pip install -r requirements.txt

python scripts/make_sample_data.py      # synthetic data, for testing the code only
python src/train.py                     # trains, selects, saves model and reports
python src/predict.py "Your KYC has expired, update now: bit.ly/abc123"
python src/app.py                       # web UI at http://127.0.0.1:5000
```

JSON API:

```bash
curl -X POST http://127.0.0.1:5000/api/predict \
     -H "Content-Type: application/json" \
     -d '{"text": "You have won Rs 50000, claim now"}'
```

## Project structure

```
data/        dataset notes and sample CSV
scripts/     synthetic sample data generator
src/         train.py, predict.py, app.py, detector.py
models/      saved model (created by train.py)
reports/     metrics.json, metrics.md, confusion_matrix.png
```

## Method notes

- **Split:** 60/20/20 train/validation/test, stratified. The model is chosen on validation and reported on test, so the test set never influences selection.
- **Leakage control:** duplicates are removed before splitting. Use `--dedupe-normalized` on real data to also remove near-duplicates that differ only by link or number.
- **Baseline:** a keyword rule shows what a simple approach achieves, so the ML gain can be measured.
- **Metrics:** false-positive rate is tracked because false alarms cost analyst time and erode trust in a detector.
- **Threshold:** `predict.py --threshold` trades recall against false alarms.

## Security considerations

The web app binds to localhost only, runs with debug off, caps input length, and auto-escapes user text. It is a demo, not a production service.

## Limitations

- The bundled sample is template-generated, so it is far easier than real traffic.
- A text-only model can be evaded by rewording and does not inspect link reputation.
- Mixed-language messages (Hindi, Telugu written in English letters) are not yet handled specially.

## Roadmap

- [ ] **Phase 2: real data.** Train on a public SMS phishing dataset and report real metrics here (table below).
- [ ] Add a character-level model comparison on the real data and discuss the errors.
- [ ] Add SHAP explanations.
- [ ] Fine-tune DistilBERT (or a multilingual model) and compare it with the baselines.
- [ ] Add URL features (length, domain age, suspicious tokens) as a second signal.
- [ ] Add a small evaluation of Hinglish / Telugu-English messages.

## Results (fill in after Phase 2)

| Model | Dataset | Precision | Recall | F1 | False-positive rate |
|---|---|---|---|---|---|
| keyword baseline | | | | | |
| Naive Bayes | | | | | |
| Logistic Regression (word) | | | | | |
| Logistic Regression (char) | | | | | |
| DistilBERT | | | | | |

## Author

Cybersecurity student project. Built for learning and portfolio use.
