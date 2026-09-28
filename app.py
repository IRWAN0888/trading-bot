import os
import json
from datetime import datetime, timezone
from flask import Flask, jsonify, render_template_string, request

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

try:
    import google.generativeai as genai
except Exception:
    genai = None

app = Flask(__name__)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
WEBHOOK_SECRET = os.environ.get("TREND_PLUS_WEBHOOK_SECRET", "").strip()

latest_trend_data = {}
latest_received_at = None

openai_client = None
if OPENAI_API_KEY and OpenAI is not None:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception:
        openai_client = None

gemini_model = None
if GEMINI_API_KEY and genai is not None:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel(
            os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        )
    except Exception:
        gemini_model = None


def build_system_prompt():
    return """
Anda ialah AI Copilot trading peribadi IRWAN.

Gunakan DATA TERKINI TREND PLUS yang dihantar daripada TradingView.
Jangan reka data indikator yang tidak diberikan.

Tugas utama:
1. Terangkan trend semasa berdasarkan data TREND PLUS.
2. Bezakan BUY, SELL dan SIDEWAY berdasarkan data sebenar.
3. Gunakan Market Structure, Purple Core, M-Structure,
   Order Block, Supply/Demand, Breakout, REMPIT dan MTF
   jika data tersebut tersedia.
4. Jika data tidak cukup, nyatakan dengan jelas data apa yang tiada.
5. Jangan mendakwa melihat carta secara langsung jika data carta
   belum diterima oleh Render.
6. Jawapan dalam Bahasa Melayu.
7. Jangan beri jaminan keuntungan.

Format ringkas:
- TREND
- MARKET STRUCTURE
- PURPLE CORE
- M-STRUCTURE
- ORDER BLOCK / SUPPLY DEMAND
- BREAKOUT / SIGNAL
- MTF
- RUMUSAN
"""


def trend_snapshot():
    if not latest_trend_data:
        return {
            "status": "NO_DATA",
            "message": "Belum menerima data TREND PLUS daripada TradingView."
        }
    return {
        "status": "OK",
        "received_at": latest_received_at,
        "data": latest_trend_data
    }


def trend_context():
    if not latest_trend_data:
        return "TREND PLUS belum menghantar data. Jangan reka nilai indikator."
    return json.dumps(latest_trend_data, ensure_ascii=False, separators=(",", ":"))


@app.route("/")
def home():
    return "TREND PLUS AI COPILOT by IRWAN is LIVE. TradingView -> Render connection ready."


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "TREND PLUS AI COPILOT",
        "tradingview_data": bool(latest_trend_data),
        "openai_configured": bool(openai_client),
        "gemini_configured": bool(gemini_model),
        "webhook_secret_enabled": bool(WEBHOOK_SECRET)
    })


@app.route("/webhook/trend-plus", methods=["POST"])
def trend_plus_webhook():
    global latest_trend_data, latest_received_at

    if WEBHOOK_SECRET:
        received_secret = request.headers.get("X-TREND-PLUS-SECRET", "").strip()
        if received_secret != WEBHOOK_SECRET:
            return jsonify({"status": "error", "message": "Invalid webhook secret."}), 401

    try:
        payload = request.get_json(silent=True)
        if payload is None:
            raw = request.get_data(as_text=True).strip()
            if not raw:
                return jsonify({"status": "error", "message": "Empty webhook body."}), 400
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                return jsonify({"status": "error", "message": "Webhook body is not valid JSON."}), 400

        if not isinstance(payload, dict):
            return jsonify({"status": "error", "message": "Payload must be a JSON object."}), 400

        latest_trend_data = payload
        latest_received_at = datetime.now(timezone.utc).isoformat()

        print("TREND PLUS DATA RECEIVED:")
        print(json.dumps(payload, ensure_ascii=False))

        return jsonify({
            "status": "received",
            "source": payload.get("source", "TREND PLUS"),
            "symbol": payload.get("symbol"),
            "timeframe": payload.get("timeframe"),
            "event": payload.get("event"),
            "received_at": latest_received_at
        }), 200

    except Exception as exc:
        print(f"Webhook error: {exc}")
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/trend-plus")
def trend_plus():
    return jsonify(trend_snapshot())


@app.route("/trend-plus/raw")
def trend_plus_raw():
    return jsonify(latest_trend_data)


@app.route("/ask", methods=["POST"])
def ask_ai():
    try:
        data = request.get_json(silent=True) or {}
        user_prompt = str(data.get("prompt", "")).strip()
        ai_engine = str(data.get("engine", "gemini")).lower().strip()

        if not user_prompt:
            return jsonify({"reply": "Sila masukkan soalan."}), 400

        context = trend_context()

        if ai_engine == "chatgpt":
            if openai_client is None:
                return jsonify({
                    "reply": "OpenAI belum dikonfigurasi di Render. Tambahkan OPENAI_API_KEY."
                }), 400

            response = openai_client.chat.completions.create(
                model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": build_system_prompt()},
                    {"role": "user", "content": "DATA TREND PLUS:\n" + context + "\n\nSOALAN:\n" + user_prompt}
                ]
            )
            return jsonify({
                "engine": "chatgpt",
                "reply": response.choices[0].message.content or ""
            })

        if gemini_model is None:
            return jsonify({
                "reply": "Gemini belum dikonfigurasi di Render. Tambahkan GEMINI_API_KEY."
            }), 400

        response = gemini_model.generate_content(
            build_system_prompt() +
            "\n\nDATA TREND PLUS:\n" + context +
            "\n\nSOALAN:\n" + user_prompt
        )
        return jsonify({
            "engine": "gemini",
            "reply": getattr(response, "text", "") or ""
        })

    except Exception as exc:
        print(f"AI error: {exc}")
        return jsonify({"reply": f"Ralat sambungan AI: {str(exc)}"}), 500


HTML_PAGE = r'''<!DOCTYPE html>
<html lang="ms">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TREND PLUS AI Copilot</title>
<style>
*{box-sizing:border-box}body{margin:0;padding:10px;background:#131722;color:#d1d4dc;font-family:Arial,sans-serif}
h1{text-align:center;font-size:16px;color:#f2a900;margin:4px 0 10px}
.status,.trend-box,.chat-box{background:#1e222d;border-radius:8px;padding:10px;margin-bottom:10px}
.trend-title{color:#f2a900;font-weight:bold;margin-bottom:6px}
pre{white-space:pre-wrap;word-break:break-word;font-size:11px;margin:0;color:#ddd}
.chat-box{height:420px;display:flex;flex-direction:column}.messages{flex:1;overflow-y:auto;background:#131722;border-radius:6px;padding:10px;font-size:12px;line-height:1.5;margin-bottom:8px}
.row{display:flex;gap:6px}input,select,button{border-radius:5px;border:1px solid #363c4e;padding:9px;font-size:12px}
input{flex:1;background:#131722;color:#fff}select{background:#2a2e39;color:#fff}button{background:#f2a900;color:#000;border:0;font-weight:bold}.ai{color:#f2a900;margin-top:8px}
</style></head>
<body>
<h1>TREND PLUS AI COPILOT — IRWAN</h1>
<div class="status" id="status">Memeriksa sambungan Render...</div>
<div class="trend-box"><div class="trend-title">DATA TREND PLUS TERKINI</div><pre id="trendData">Belum menerima data TradingView.</pre></div>
<div class="chat-box">
<div class="messages" id="messages"><div><b>AI Copilot:</b> Tunggu data TREND PLUS daripada TradingView, kemudian boleh tanya analisis.</div></div>
<div class="row">
<select id="engine"><option value="gemini">Gemini AI</option><option value="chatgpt">ChatGPT</option></select>
<input id="prompt" type="text" placeholder="Contoh: Apakah trend sekarang?" onkeypress="handleKey(event)">
<button onclick="askAI()">Hantar</button>
</div></div>
<script>
async function refreshTrendStatus(){try{const r=await fetch('/trend-plus');const d=await r.json();if(d.status==='OK'){document.getElementById('status').innerText='✅ TradingView → Render OK | '+d.received_at;document.getElementById('trendData').innerText=JSON.stringify(d.data,null,2)}else{document.getElementById('status').innerText='🟡 Render hidup — belum menerima data TradingView.';document.getElementById('trendData').innerText=d.message||'Tiada data.'}}catch(e){document.getElementById('status').innerText='❌ Gagal membaca data TREND PLUS.'}}
async function askAI(){const input=document.getElementById('prompt'),engine=document.getElementById('engine'),messages=document.getElementById('messages'),text=input.value.trim();if(!text)return;messages.innerHTML+='<div style="margin-top:8px"><b>Anda:</b> '+escapeHtml(text)+'</div>';input.value='';try{const r=await fetch('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:text,engine:engine.value})});const d=await r.json();messages.innerHTML+='<div class="ai"><b>'+escapeHtml(engine.value)+':</b><br>'+escapeHtml(d.reply||'Tiada jawapan.').replace(/\n/g,'<br>')+'</div>'}catch(e){messages.innerHTML+='<div style="color:red;margin-top:8px"><b>Ralat:</b> Gagal berhubung dengan AI.</div>'}messages.scrollTop=messages.scrollHeight}
function handleKey(e){if(e.key==='Enter')askAI()}function escapeHtml(t){return String(t).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#039;')}
refreshTrendStatus();setInterval(refreshTrendStatus,5000);
</script></body></html>'''


@app.route("/capture")
def capture():
    return render_template_string(HTML_PAGE)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
