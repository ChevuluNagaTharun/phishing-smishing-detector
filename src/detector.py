"""Shared inference helpers used by predict.py and app.py."""
from pathlib import Path

import joblib

ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = ROOT / "models" / "model.joblib"


def load_model(path: Path = MODEL_PATH):
    if not Path(path).exists():
        raise FileNotFoundError(f"No trained model at {path}. Run: python src/train.py")
    return joblib.load(path)


def predict(model, text: str, threshold: float = 0.5) -> dict:
    score = float(model.predict_proba([text])[0][1])
    return {
        "label": "phishing/smishing" if score >= threshold else "legitimate",
        "score": round(score, 4),
        "threshold": threshold,
    }


def explain(model, text: str, top_k: int = 5) -> list:
    """Top terms pushing the prediction, from the model's own weights.

    Works for word-level linear / Naive Bayes models. (SHAP is the Phase 2
    upgrade; it was not installed in the build environment.)
    """
    vec = model.named_steps["tfidf"]
    clf = model.named_steps["clf"]
    if getattr(vec, "analyzer", "word") != "word":
        return []
    if hasattr(clf, "coef_"):
        weights = clf.coef_[0]
    elif hasattr(clf, "feature_log_prob_"):
        weights = clf.feature_log_prob_[1] - clf.feature_log_prob_[0]
    else:
        return []
    names = vec.get_feature_names_out()
    x = vec.transform([text]).tocoo()
    contrib = [(names[j], float(v * weights[j])) for j, v in zip(x.col, x.data)]
    contrib.sort(key=lambda t: abs(t[1]), reverse=True)
    return [{"term": t, "contribution": round(c, 4)} for t, c in contrib[:top_k]]
