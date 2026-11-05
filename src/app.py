#!/usr/bin/env python3
"""Minimal local web UI + JSON API for the detector.

Run:  python src/app.py   then open http://127.0.0.1:5000

Basic hardening (mention this in your README, it shows security thinking):
  * binds to localhost only, debug mode off
  * input length capped
  * templates auto-escape user text (no reflected XSS)
"""
from flask import Flask, jsonify, render_template_string, request

from detector import explain, load_model, predict

MAX_LEN = 2000
app = Flask(__name__)
_model = None


def get_model():
    global _model
    if _model is None:
        _model = load_model()
    return _model


PAGE = """<!doctype html>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Phishing / Smishing Detector</title>
<style>
  body{font-family:system-ui,sans-serif;max-width:640px;margin:2rem auto;padding:0 1rem;color:#1a1a1a}
  textarea{width:100%;height:120px;padding:.6rem;font:inherit;box-sizing:border-box}
  button{margin-top:.6rem;padding:.5rem 1.2rem;font:inherit;cursor:pointer}
  .res{margin-top:1.2rem;padding:1rem;border-radius:8px;border:1px solid #ccc}
  .bad{background:#fdecea;border-color:#e57373}.ok{background:#e8f5e9;border-color:#81c784}
  small{color:#555}
</style>
<h1>Phishing / Smishing Detector</h1>
<form method="post">
  <textarea name="text" maxlength="2000" placeholder="Paste an SMS or email text here">{{ text }}</textarea>
  <button type="submit">Check message</button>
</form>
{% if result %}
<div class="res {{ 'bad' if result.label != 'legitimate' else 'ok' }}">
  <strong>{{ result.label }}</strong> (score {{ result.score }}, threshold {{ result.threshold }})
  {% if result.terms %}<p>Terms that influenced this result:</p><ul>
    {% for t in result.terms %}<li>{{ t.term }}: {{ t.contribution }}</li>{% endfor %}
  </ul>{% endif %}
</div>
{% endif %}
<p><small>Educational project. Do not rely on it as your only defence.</small></p>
"""


@app.route("/", methods=["GET", "POST"])
def index():
    text, result = "", None
    if request.method == "POST":
        text = request.form.get("text", "")[:MAX_LEN]
        if text.strip():
            m = get_model()
            result = {**predict(m, text), "terms": explain(m, text)}
    return render_template_string(PAGE, text=text, result=result)


@app.post("/api/predict")
def api_predict():
    payload = request.get_json(silent=True) or {}
    text = str(payload.get("text", ""))[:MAX_LEN]
    if not text.strip():
        return jsonify({"error": "field 'text' is required"}), 400
    m = get_model()
    return jsonify({**predict(m, text), "top_terms": explain(m, text)})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
