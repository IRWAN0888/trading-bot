import os
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template_string, request

import google.generativeai as genai
from openai import OpenAI


# ============================================================
# IRWAN TRADING AI COPILOT
# TradingView -> Render -> Gemini / ChatGPT
# ============================================================

app = Flask(__name__)

@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return response

# ------------------------------------------------------------
# API KEYS
# Set these in Render Environment Variables.
# Do NOT put real API keys inside this file.
# ------------------------------------------------------------
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()

# Optional webhook secret.
# Leave empty for the first TradingView -> Render test.
WEBHOOK_SECRET = os.environ.get("TREND_PLUS_WEBHOOK_SECRET", "").strip()


# ------------------------------------------------------------
# AI CLIENTS
# ------------------------------------------------------------
gemini_model = None

if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel(
            os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
        )
    except Exception:
        gemini_model = None


openai_client = None

if OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception:
        openai_client = None


# ------------------------------------------------------------
# LATEST TREND PLUS DATA
# ------------------------------------------------------------
LATEST_TREND_PLUS = {
    "status": "waiting",
    "source": "TREND PLUS",
    "message": "Belum menerima data daripada TradingView."
}


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def build_trend_context():
    if not LATEST_TREND_PLUS:
        return "Belum ada data TREND PLUS daripada TradingView."

    return (
        "\n\n===== DATA LIVE TERKINI TREND PLUS =====\n"
        + str(LATEST_TREND_PLUS)
        + "\n===== TAMAT DATA TREND PLUS =====\n"
    )


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():
    return (
        "XAUUSD TREND PLUS Multi-AI Copilot by IRWAN "
        "(irwan0888) is Live!"
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "IRWAN TREND PLUS AI Copilot",
        "tradingview_webhook": "/webhook/trend-plus",
        "trend_plus_data": "/trend-plus",
        "ask_ai": "/ask",
        "timestamp_utc": utc_now_iso()
    })


# ============================================================
# TRADINGVIEW -> RENDER WEBHOOK
# ============================================================

@app.route("/webhook/trend-plus", methods=["POST"])
def trend_plus_webhook():
    global LATEST_TREND_PLUS

    try:
        data = request.get_json(silent=True)

        if not data:
            return jsonify({
                "status": "error",
                "message": "JSON data tidak diterima."
            }), 400

        if WEBHOOK_SECRET:
            incoming_secret = str(data.get("secret", "")).strip()

            if incoming_secret != WEBHOOK_SECRET:
                return jsonify({
                    "status": "error",
                    "message": "Invalid webhook secret."
                }), 401

        data["_render_received_utc"] = utc_now_iso()
        LATEST_TREND_PLUS = data

        print("TREND PLUS DATA RECEIVED:", data)

        return jsonify({
            "status": "ok",
            "message": "TREND PLUS data diterima oleh Render.",
            "source": data.get("source"),
            "symbol": data.get("symbol"),
            "ticker": data.get("ticker"),
            "timeframe": data.get("timeframe"),
            "event": data.get("event"),
            "received_utc": data["_render_received_utc"]
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Webhook error: {str(e)}"
        }), 500


# ============================================================
# SHOW LATEST TREND PLUS DATA
# ============================================================

@app.route("/trend-plus")
def trend_plus_data():
    return jsonify({
        "status": "ok",
        "data": LATEST_TREND_PLUS
    })


@app.route("/test-webhook")
def test_webhook():
    return jsonify({
        "endpoint": "/webhook/trend-plus",
        "method": "POST",
        "ready": True,
        "current_status": LATEST_TREND_PLUS.get("status")
    })


@app.route("/trend-plus/raw")
def trend_plus_raw():
    return jsonify(LATEST_TREND_PLUS)


# ============================================================
# AI ASK ENDPOINT
# ============================================================

@app.route("/ask", methods=["POST"])
def ask_ai():
    try:
        data = request.get_json(silent=True) or {}

        user_prompt = str(data.get("prompt", "")).strip()
        ai_engine = str(data.get("engine", "gemini")).strip().lower()

        if not user_prompt:
            return jsonify({
                "reply": "Sila masukkan soalan analisis."
            }), 400

        system_context = (
            "Anda ialah AI Copilot peribadi untuk trader bernama "
            "IRWAN (irwan0888). "
            "Anda membantu membaca DATA LIVE TREND PLUS yang dihantar "
            "oleh TradingView ke Render.\n\n"

            "SOP MCDX PRIME+ yang mesti dihormati:\n"
            "1. Jujukan BUY (Bullish): "
            "G1 (Pink silang atas Cyan) -> "
            "G2 (Purple silang atas Cyan) -> "
            "G3 (Purple silang atas Pink). "
            "Makin tinggi makin sah.\n"

            "2. Jujukan SELL (Bearish): "
            "DC3 (Purple silang bawah Pink) -> "
            "DC2 (Purple silang bawah Cyan) -> "
            "DC1 (Pink silang bawah Cyan). "
            "Makin rendah makin sah.\n"

            "3. SIDEWAY: Berlaku apabila silangan berulang bercampur "
            "dan tidak konsisten, tanpa jujukan arah yang jelas. "
            "Dalam keadaan ini nyatakan bahawa setup belum jelas.\n\n"

            "Untuk TREND PLUS, gunakan data yang diterima daripada "
            "TradingView sebagai sumber utama. "
            "Jangan mereka-reka nilai indikator yang tidak dihantar.\n"

            "Jika sesuatu data tiada atau bernilai NONE/NA, nyatakan "
            "bahawa data tersebut belum tersedia.\n\n"

            "Berikan jawapan teknikal, ringkas tetapi tajam, "
            "profesional dan dalam Bahasa Melayu."
        )

        full_prompt = (
            system_context
            + build_trend_context()
            + "\n\nSoalan Trader IRWAN:\n"
            + user_prompt
        )

        if ai_engine == "chatgpt":
            if not openai_client:
                return jsonify({
                    "reply": (
                        "Ralat: OPENAI_API_KEY belum ditetapkan "
                        "di Render."
                    )
                }), 400

            response = openai_client.chat.completions.create(
                model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[
                    {
                        "role": "system",
                        "content": system_context
                    },
                    {
                        "role": "user",
                        "content": (
                            build_trend_context()
                            + "\n\n"
                            + user_prompt
                        )
                    }
                ]
            )

            reply_text = response.choices[0].message.content or ""

        else:
            if not gemini_model:
                return jsonify({
                    "reply": (
                        "Ralat: GEMINI_API_KEY belum ditetapkan "
                        "di Render."
                    )
                }), 400

            response = gemini_model.generate_content(full_prompt)
            reply_text = getattr(response, "text", "") or ""

        return jsonify({
            "reply": reply_text,
            "engine": ai_engine,
            "trend_plus_received": (
                LATEST_TREND_PLUS.get("status") != "waiting"
            )
        }), 200

    except Exception as e:
        print(f"AI error: {e}")
        return jsonify({
            "reply": f"Ralat sambungan API: {str(e)}"
        }), 500


# ============================================================
# WEB UI
# ============================================================

@app.route("/capture")
def capture():
    html_content = """
    <!DOCTYPE html>
    <html lang="ms">
    <head>
        <meta charset="UTF-8">
        <title>TREND PLUS Multi-AI Copilot - IRWAN</title>
        <meta
            name="viewport"
            content="width=device-width, initial-scale=1.0"
        >

        <style>
            * { box-sizing: border-box; }

            body {
                background-color: #131722;
                color: #d1d4dc;
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 10px;
            }

            h1 {
                color: #f2a900;
                font-size: 14px;
                text-align: center;
                margin: 5px 0 10px 0;
            }

            .container {
                display: flex;
                flex-direction: column;
                gap: 10px;
                max-width: 1100px;
                margin: 0 auto;
            }

            .status-box {
                background: #1e222d;
                padding: 8px;
                border-radius: 8px;
                font-size: 11px;
                text-align: center;
            }

            .status-ok { color: #00c853; }
            .status-wait { color: #f2a900; }

            .chart-box {
                background: #1e222d;
                padding: 6px;
                border-radius: 8px;
            }

            .chat-box {
                background: #1e222d;
                padding: 10px;
                border-radius: 8px;
                height: 380px;
                display: flex;
                flex-direction: column;
            }

            .chat-messages {
                flex: 1;
                overflow-y: auto;
                background: #131722;
                padding: 10px;
                border-radius: 5px;
                margin-bottom: 8px;
                font-size: 12px;
                text-align: left;
                line-height: 1.5;
                word-break: break-word;
            }

            .chat-input-area {
                display: flex;
                gap: 6px;
                flex-direction: column;
            }

            .input-row {
                display: flex;
                gap: 6px;
            }

            input[type="text"] {
                flex: 1;
                padding: 9px;
                border-radius: 5px;
                border: 1px solid #2a2e39;
                background: #131722;
                color: #fff;
                font-size: 12px;
                outline: none;
            }

            button {
                padding: 8px 12px;
                background: #f2a900;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                cursor: pointer;
                color: #000;
                font-size: 12px;
            }

            .engine-select {
                background: #2a2e39;
                color: #fff;
                padding: 6px;
                border-radius: 5px;
                border: 1px solid #363c4e;
                font-size: 12px;
            }

            .tf-buttons {
                display: flex;
                gap: 4px;
                justify-content: center;
                flex-wrap: wrap;
            }

            .tf-btn {
                padding: 5px 8px;
                background: #2a2e39;
                color: #fff;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 11px;
            }

            .tf-btn.active {
                background: #f2a900;
                color: #000;
                font-weight: bold;
            }

            .small-note {
                color: #9aa0ad;
                font-size: 10px;
                text-align: center;
            }

            @media (max-width: 600px) {
                body { padding: 6px; }

                .chat-box { height: 420px; }

                .input-row {
                    flex-direction: column;
                }

                input[type="text"] {
                    width: 100%;
                }
            }
        </style>
    </head>

    <body>
        <h1>
            XAUUSD TREND PLUS Multi-AI Copilot —
            IRWAN (irwan0888)
        </h1>

        <div class="container">

            <div class="tf-buttons">
                <button class="tf-btn"
                    onclick="changeTf('1', this)">1m</button>
                <button class="tf-btn"
                    onclick="changeTf('5', this)">5m</button>
                <button class="tf-btn"
                    onclick="changeTf('15', this)">15m</button>
                <button class="tf-btn"
                    onclick="changeTf('60', this)">1h</button>
                <button class="tf-btn"
                    onclick="changeTf('240', this)">4h</button>
                <button class="tf-btn active"
                    onclick="changeTf('D', this)">Daily</button>
            </div>

            <div class="status-box" id="trendStatus">
                Memeriksa data TREND PLUS...
            </div>

            <div class="chart-box">
                <div id="tradingview_chart"
                    style="height:300px;width:100%;">
                </div>
            </div>

            <div class="chat-box">

                <div class="chat-messages" id="chatMessages">
                    <div>
                        <b>Multi-AI Copilot:</b>
                        Salam IRWAN. TREND PLUS akan menjadi sumber
                        data utama selepas TradingView menghantar
                        webhook ke Render.
                    </div>
                </div>

                <div class="chat-input-area">

                    <div style="
                        display:flex;
                        gap:8px;
                        align-items:center;
                    ">
                        <span style="font-size:12px;">
                            Pilih AI:
                        </span>

                        <select id="aiEngine"
                            class="engine-select">
                            <option value="gemini">
                                Gemini AI
                            </option>
                            <option value="chatgpt">
                                ChatGPT (OpenAI)
                            </option>
                        </select>
                    </div>

                    <div class="input-row">

                        <input
                            type="text"
                            id="userInput"
                            placeholder="Contoh: Apakah trend sekarang?"
                            onkeypress="handleKeyPress(event)"
                        >

                        <button onclick="sendMessage()">
                            Hantar
                        </button>

                    </div>

                    <div class="small-note">
                        AI membaca snapshot TREND PLUS terakhir
                        yang diterima oleh Render.
                    </div>

                </div>
            </div>
        </div>

        <script type="text/javascript">
            var tvWidget = null;

            function initTradingView() {
                if (!window.TradingView || !window.TradingView.widget) {
                    console.log("TradingView widget library belum tersedia.");
                    return false;
                }

                try {
                    tvWidget = new TradingView.widget({
                        "width": "100%",
                        "height": "300",
                        "symbol": "OANDA:XAUUSD",
                        "interval": "D",
                        "timezone": "Etc/UTC",
                        "theme": "dark",
                        "style": "1",
                        "locale": "en",
                        "toolbar_bg": "#f1f3f6",
                        "enable_publishing": false,
                        "allow_symbol_change": true,
                        "hide_side_toolbar": false,
                        "container_id": "tradingview_chart"
                    });
                    return true;
                } catch (e) {
                    console.log("TradingView init error:", e);
                    return false;
                }
            }


            function changeTf(tf, button) {

                document
                    .querySelectorAll(".tf-btn")
                    .forEach(function(btn) {
                        btn.classList.remove("active");
                    });

                button.classList.add("active");

                try {
                    if (tvWidget && tvWidget.chart) {
                        tvWidget
                            .chart()
                            .setResolution(tf, function() {});
                    }
                } catch (e) {
                    console.log(e);
                }
            }


            function escapeHtml(text) {
                return String(text)
                    .split("&").join("&amp;")
                    .split("<").join("&lt;")
                    .split(">").join("&gt;")
                    .split('"').join("&quot;")
                    .split("'").join("&#039;");
            }


            function sendMessage() {

                var input =
                    document.getElementById("userInput");

                var engineSelect =
                    document.getElementById("aiEngine");

                var text = input.value.trim();
                var engine = engineSelect.value;

                if (!text) return;

                var messages =
                    document.getElementById("chatMessages");

                messages.innerHTML +=
                    '<div style="margin-top:8px;">' +
                    '<b>Anda:</b> ' +
                    escapeHtml(text) +
                    '</div>';

                input.value = "";
                messages.scrollTop = messages.scrollHeight;

                fetch("/ask", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        prompt: text,
                        engine: engine
                    })
                })
                .then(function(response) {
                    return response.json();
                })
                .then(function(data) {

                    var engineName =
                        engine === "chatgpt"
                            ? "ChatGPT AI"
                            : "Gemini AI";

                    var reply =
                        data.reply || "Tiada jawapan.";

                    var formattedReply =
                        escapeHtml(reply)
                            .replace(/\\n/g, "<br>");

                    messages.innerHTML +=
                        '<div style="' +
                        'margin-top:8px;color:#f2a900;' +
                        '">' +
                        '<b>' +
                        engineName +
                        ':</b><br>' +
                        formattedReply +
                        '</div>';

                    messages.scrollTop =
                        messages.scrollHeight;
                })
                .catch(function(error) {

                    messages.innerHTML +=
                        '<div style="' +
                        'margin-top:8px;color:red;' +
                        '">' +
                        '<b>Ralat:</b> ' +
                        'Gagal berhubung dengan pelayan AI.' +
                        '</div>';

                    messages.scrollTop =
                        messages.scrollHeight;

                    console.log(error);
                });
            }


            function handleKeyPress(e) {

                if (e.key === "Enter") {
                    sendMessage();
                }
            }


            function refreshTrendStatus() {

                var box = document.getElementById("trendStatus");

                var controller = new AbortController();

                var timeoutId = setTimeout(function() {
                    controller.abort();
                }, 4000);

                fetch("/trend-plus?_=" + Date.now(), {
                    method: "GET",
                    cache: "no-store",
                    signal: controller.signal
                })
                .then(function(response) {

                    clearTimeout(timeoutId);

                    if (!response.ok) {
                        throw new Error("HTTP " + response.status);
                    }

                    return response.json();
                })
                .then(function(result) {

                    var data = result.data || {};

                    if (data.status === "waiting") {
                        box.className = "status-box status-wait";
                        box.innerHTML =
                            "TREND PLUS: Menunggu data TradingView...";
                        return;
                    }

                    box.className = "status-box status-ok";

                    var symbol = data.symbol || "-";
                    var tf = data.timeframe || "-";
                    var event = data.event || "NONE";
                    var trend = data.external_trend || "NONE";

                    box.innerHTML =
                        "TREND PLUS LIVE — " +
                        escapeHtml(symbol) +
                        " | TF: " +
                        escapeHtml(tf) +
                        " | EVENT: " +
                        escapeHtml(event) +
                        " | TREND: " +
                        escapeHtml(trend);
                })
                .catch(function(error) {

                    clearTimeout(timeoutId);

                    box.className = "status-box status-wait";
                    box.innerHTML =
                        "TREND PLUS: Render aktif — " +
                        "menunggu TradingView.";

                    console.log("TREND PLUS status:", error);
                });
            }



            // Poll Render independently of TradingView embed.
            refreshTrendStatus();

            setInterval(
                refreshTrendStatus,
                5000
            );

            // IMPORTANT: load TradingView asynchronously so tv.js can NEVER
            // block the Render status polling or AI chat JavaScript.
            function loadTradingViewAsync() {
                var script = document.createElement("script");
                script.type = "text/javascript";
                script.src = "https://s3.tradingview.com/tv.js";
                script.async = true;

                script.onload = function() {
                    console.log("TradingView library loaded.");
                    initTradingView();
                };

                script.onerror = function() {
                    console.log("TradingView library gagal dimuat. Render/AI tetap berjalan.");
                };

                document.head.appendChild(script);
            }

            // Start external TradingView loading only AFTER all local JS
            // functions above are active.
            loadTradingViewAsync();

        </script>

    </body>
    </html>
    """

    return render_template_string(html_content)


# ============================================================
# LOCAL / RENDER START
# ============================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port
    )
