#!/usr/bin/env python3
"""Local web UI (hacker/terminal theme) + JSON API for the detector.

Run:  python src/app.py   then open http://127.0.0.1:5000

Basic hardening (mention this in your README, it shows security thinking):
  * binds to localhost only, debug mode off
  * input length capped
  * templates auto-escape user text (no reflected XSS)
  * no external scripts, fonts or CDNs (everything is inline, works offline)
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


PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PHISH//SCAN</title>
{% raw %}
<style>
  :root{
    --bg:#050a07; --panel:#08130d; --line:#14492c; --text:#3dff8f; --dim:#2fb36b;
    --muted:#6fae8c; --bad:#ff4d5e; --badbg:#1a070a; --ok:#3dff8f; --okbg:#06170d;
    --mono: "Cascadia Mono","Cascadia Code",Consolas,"SF Mono",Menlo,"Courier New",monospace;
  }
  *{box-sizing:border-box}
  html,body{margin:0;min-height:100%}
  body{background:var(--bg);color:var(--text);font-family:var(--mono);font-size:15px;line-height:1.55;
       padding:24px 16px 48px;position:relative;overflow-x:hidden}
  #rain{position:fixed;inset:0;z-index:0;opacity:.28;pointer-events:none}
  body::after{content:"";position:fixed;inset:0;z-index:2;pointer-events:none;
       background:repeating-linear-gradient(to bottom,rgba(0,0,0,0) 0,rgba(0,0,0,0) 2px,rgba(0,0,0,.18) 3px)}
  main{position:relative;z-index:1;max-width:760px;margin:0 auto}
  .brand{font-size:clamp(26px,6vw,40px);font-weight:700;letter-spacing:.08em;margin:6px 0 2px;
         text-shadow:0 0 12px rgba(61,255,143,.55)}
  .brand span{color:var(--bad);text-shadow:0 0 12px rgba(255,77,94,.5)}
  .sub{color:var(--muted);margin:0 0 20px}
  .panel{background:var(--panel);border:1px solid var(--line);border-radius:6px;
         box-shadow:0 0 0 1px rgba(61,255,143,.05),0 0 24px rgba(61,255,143,.08);margin-bottom:18px}
  .bar{display:flex;align-items:center;gap:8px;padding:8px 12px;border-bottom:1px solid var(--line);
       color:var(--muted);font-size:13px}
  .dot{width:10px;height:10px;border-radius:50%;background:#1d3d2b}
  .dot:nth-child(1){background:#ff5f56}.dot:nth-child(2){background:#ffbd2e}.dot:nth-child(3){background:#27c93f}
  .bar b{margin-left:6px;font-weight:400}
  form{padding:14px 14px 16px}
  label{display:block;color:var(--dim);margin-bottom:6px}
  textarea{width:100%;height:130px;resize:vertical;background:#030806;color:var(--text);
           border:1px solid var(--line);border-radius:4px;padding:10px;font:inherit;caret-color:var(--text)}
  textarea::placeholder{color:#2d6b4a}
  textarea:focus{outline:2px solid var(--text);outline-offset:1px}
  button{margin-top:12px;background:transparent;color:var(--text);border:1px solid var(--text);
         border-radius:4px;padding:9px 18px;font:inherit;font-weight:700;letter-spacing:.06em;cursor:pointer}
  button:hover,button:focus-visible{background:var(--text);color:#03140a;outline:none;
         box-shadow:0 0 16px rgba(61,255,143,.5)}
  .verdict{padding:14px 16px 16px}
  .verdict.bad{border-color:var(--bad);background:var(--badbg);box-shadow:0 0 24px rgba(255,77,94,.18)}
  .verdict.ok{border-color:var(--ok);background:var(--okbg)}
  .v-title{font-size:19px;font-weight:700;letter-spacing:.05em}
  .verdict.bad .v-title{color:var(--bad);text-shadow:0 0 10px rgba(255,77,94,.5)}
  .verdict.ok .v-title{color:var(--ok);text-shadow:0 0 10px rgba(61,255,143,.4)}
  .meter{position:relative;height:14px;margin:12px 0 6px;border:1px solid var(--line);background:#030806;border-radius:3px}
  .fill{height:100%;border-radius:2px}
  .verdict.bad .fill{background:linear-gradient(90deg,#8a2330,var(--bad))}
  .verdict.ok .fill{background:linear-gradient(90deg,#14492c,var(--ok))}
  .thr{position:absolute;top:-4px;bottom:-4px;width:2px;background:#e8fff1}
  .v-meta{color:var(--muted);font-size:13px;word-break:break-word}
  .ind-title{margin-top:14px;color:var(--dim)}
  ul.ind{list-style:none;margin:6px 0 0;padding:0}
  ul.ind li{display:flex;justify-content:space-between;gap:12px;padding:3px 8px;border-left:3px solid;margin-bottom:3px;background:rgba(0,0,0,.25)}
  ul.ind li.up{border-color:var(--bad);color:#ff8a96}
  ul.ind li.down{border-color:var(--ok);color:var(--ok)}
  .legend{color:var(--muted);font-size:12px;margin:8px 0 0}
  footer{color:var(--muted);font-size:12px}
  .cursor{display:inline-block;width:.6em;height:1.05em;background:var(--text);vertical-align:-2px;
          animation:blink 1s steps(1) infinite}
  @keyframes blink{50%{opacity:0}}
  @media (prefers-reduced-motion:reduce){.cursor{animation:none}}
</style>
{% endraw %}
</head>
<body>
<canvas id="rain" aria-hidden="true"></canvas>
<main>
  <h1 class="brand">PHISH<span>//</span>SCAN</h1>
  <p class="sub">SMS &amp; phishing text classifier &middot; local node 127.0.0.1 &middot; model online<span class="cursor" aria-hidden="true"></span></p>

  <section class="panel">
    <div class="bar"><span class="dot"></span><span class="dot"></span><span class="dot"></span><b>analyst@soc:~$ scan --message</b></div>
    <form method="post">
      <label for="text">&gt; paste suspicious message</label>
      <textarea id="text" name="text" maxlength="2000" placeholder="e.g. You have won a free prize, call now to claim..." autofocus>{{ text }}</textarea>
      <button type="submit">[ RUN SCAN ]</button>
    </form>
  </section>

  {% if result %}
  {% set bad = result.label != 'legitimate' %}
  <section class="panel verdict {{ 'bad' if bad else 'ok' }}" aria-live="polite">
    <div class="v-title">&gt; VERDICT: {{ 'THREAT DETECTED' if bad else 'CLEAN' }}</div>
    <div class="meter" role="img" aria-label="Threat score {{ result.pct }} percent">
      <div class="fill" style="width: {{ result.pct }}%"></div>
      <div class="thr" style="left: {{ result.thr_pct }}%"></div>
    </div>
    <div class="v-meta">threat_score={{ result.score }} | threshold={{ result.threshold }} | class={{ result.label }}</div>
    {% if result.terms %}
    <div class="ind-title">&gt; INDICATORS</div>
    <ul class="ind">
      {% for t in result.terms %}
      <li class="{{ 'up' if t.contribution > 0 else 'down' }}"><span>{{ t.term }}</span><span>{{ '%+.3f'|format(t.contribution) }}</span></li>
      {% endfor %}
    </ul>
    <p class="legend">red = pushes toward phishing &middot; green = pushes toward legitimate &middot; white line = decision threshold</p>
    {% endif %}
  </section>
  {% endif %}

  <footer>Educational project. Do not rely on it as your only defence.</footer>
</main>

{% raw %}
<script>
(function () {
  if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  var c = document.getElementById('rain'), x = c.getContext('2d');
  var chars = '01ABCDEF<>/[]#$%'.split(''), fs = 16, drops = [];
  function size() {
    c.width = window.innerWidth; c.height = window.innerHeight;
    var cols = Math.floor(c.width / fs); drops = [];
    for (var i = 0; i < cols; i++) drops.push(Math.random() * c.height / fs);
  }
  size(); window.addEventListener('resize', size);
  setInterval(function () {
    x.fillStyle = 'rgba(5,10,7,0.12)'; x.fillRect(0, 0, c.width, c.height);
    x.fillStyle = '#2fb36b'; x.font = fs + 'px monospace';
    for (var i = 0; i < drops.length; i++) {
      x.fillText(chars[Math.floor(Math.random() * chars.length)], i * fs, drops[i] * fs);
      if (drops[i] * fs > c.height && Math.random() > 0.975) drops[i] = 0;
      drops[i]++;
    }
  }, 60);
})();
</script>
{% endraw %}
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def index():
    text, result = "", None
    if request.method == "POST":
        text = request.form.get("text", "")[:MAX_LEN]
        if text.strip():
            m = get_model()
            r = predict(m, text)
            result = {
                **r,
                "terms": explain(m, text),
                "pct": round(r["score"] * 100, 1),
                "thr_pct": round(r["threshold"] * 100, 1),
            }
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