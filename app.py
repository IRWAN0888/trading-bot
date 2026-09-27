
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

# ------------------------------------------------------------
# API KEYS
# Set these in Render Environment Variables.
# Do NOT put real API keys inside this file.
# ------------------------------------------------------------
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()

# Optional webhook secret.
# Leave empty for the first TradingView -> Render test.
# If you use it, the Pine webhook payload must contain:
# {"secret":"YOUR_VALUE", ...}
WEBHOOK_SECRET = os.environ.get("TREND_PLUS_WEBHOOK_SECRET", "").strip()


# ------------------------------------------------------------
# AI CLIENTS
# ------------------------------------------------------------
gemini_model = None

if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel("gemini-3.8-flash")
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
#
# TradingView sends the latest confirmed TREND PLUS snapshot
# to /webhook/trend-plus.
#
# This is intentionally stored in RAM for the first version.
# Render restart will clear this value.
# ------------------------------------------------------------
LATEST_TREND_PLUS = {
    "status": "waiting",
    "source": "TREND PLUS",
    "message": "Belum menerima data daripada TradingView."
}


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def build_trend_context():
    """
    Convert the latest TradingView TREND PLUS snapshot into
    readable context for Gemini / ChatGPT.
    """
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

        # Optional secret verification.
        # If TREND_PLUS_WEBHOOK_SECRET is empty in Render,
        # no secret check is performed.
        if WEBHOOK_SECRET:
            incoming_secret = str(data.get("secret", "")).strip()

            if incoming_secret != WEBHOOK_SECRET:
                return jsonify({
                    "status": "error",
                    "message": "Invalid webhook secret."
                }), 401

        # Add server receive timestamp.
        data["_render_received_utc"] = utc_now_iso()

        # Store the exact TREND PLUS snapshot.
        LATEST_TREND_PLUS = data

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

        # ----------------------------------------------------
        # CORE SOP
        # ----------------------------------------------------
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

        # ----------------------------------------------------
        # CHATGPT
        # ----------------------------------------------------
        if ai_engine == "chatgpt":
            if not openai_client:
                return jsonify({
                    "reply": (
                        "Ralat: OPENAI_API_KEY belum ditetapkan "
                        "di Render."
                    )
                }), 400

            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
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

        # ----------------------------------------------------
        # GEMINI
        # ----------------------------------------------------
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
            * {
                box-sizing: border-box;
            }

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

            .status-ok {
                color: #00c853;
            }

            .status-wait {
                color: #f2a900;
            }

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

            button:hover {
                opacity: 0.9;
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
                body {
                    padding: 6px;
                }

                .chat-box {
                    height: 420px;
                }

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
                <button
                    class="tf-btn"
                    onclick="changeTf('1', this)"
                >1m</button>

                <button
                    class="tf-btn"
                    onclick="changeTf('5', this)"
                >5m</button>

                <button
                    class="tf-btn"
                    onclick="changeTf('15', this)"
                >15m</button>

                <button
                    class="tf-btn"
                    onclick="changeTf('60', this)"
                >1h</button>

                <button
                    class="tf-btn"
                    onclick="changeTf('240', this)"
                >4h</button>

                <button
                    class="tf-btn active"
                    onclick="changeTf('D', this)"
                >Daily</button>
            </div>

            <div class="status-box" id="trendStatus">
                Memeriksa data TREND PLUS...
            </div>

            <div class="chart-box">
                <div
                    id="tradingview_chart"
                    style="height: 300px; width: 100%;"
                ></div>
            </div>

            <div class="chat-box">

                <div
                    class="chat-messages"
                    id="chatMessages"
                >
                    <div>
                        <b>Multi-AI Copilot:</b>
                        Salam IRWAN. TREND PLUS akan menjadi sumber
                        data utama selepas TradingView menghantar
                        webhook ke Render.
                    </div>
                </div>

                <div class="chat-input-area">

                    <div
                        style="
                            display:flex;
                            gap:8px;
                            align-items:center;
                        "
                    >
                        <span style="font-size:12px;">
                            Pilih AI:
                        </span>

                        <select
                            id="aiEngine"
                            class="engine-select"
                        >
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


        <script
            type="text/javascript"
            src="https://s3.tradingview.com/tv.js"
        ></script>

        <script type="text/javascript">

            var tvWidget = new TradingView.widget({
                "width": "100%",
                "height": "300",
                "symbol": "OANDA:XAUUSD",
                "interval": "D",
                "timezone": "Etc/UTC",
                "theme": "dark",
                "style": "1",
                "locale": "en",
                "toolbar_bg": "#f1f3f6",
                "enable_publishing": true,
                "allow_symbol_change": true,
                "hide_side_toolbar": false,
                "container_id": "tradingview_chart",
                "studies": [
                    "MACD@tv-basicstudies",
                    "RSI@tv-basicstudies"
                ]
            });


            function changeTf(tf, button) {

                document
                    .querySelectorAll(".tf-btn")
                    .forEach(function(btn) {
                        btn.classList.remove("active");
                    });

                button.classList.add("active");

                try {
                    tvWidget
                        .chart()
                        .setResolution(tf, function() {});
                } catch (e) {
                    console.log(e);
                }
            }


            function escapeHtml(text) {

                return String(text)
                    .replace(/&/g, "&amp;")
                    .replace(/</g, "&lt;")
                    .replace(/>/g, "&gt;")
                    .replace(/"/g, "&quot;")
                    .replace(/'/g, "&#039;");
            }


            function sendMessage() {

                var input =
                    document.getElementById("userInput");

                var engineSelect =
                    document.getElementById("aiEngine");

                var text = input.value.trim();
                var engine = engineSelect.value;

                if (!text) {
                    return;
                }

                var messages =
                    document.getElementById("chatMessages");

                messages.innerHTML +=
                    '<div style="margin-top:8px;">' +
                    '<b>Anda:</b> ' +
                    escapeHtml(text) +
                    '</div>';

                input.value = "";

                messages.scrollTop =
                    messages.scrollHeight;

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
                            .replace(/\n/g, "<br>");

                    messages.innerHTML +=
                        '<div style="' +
                        'margin-top:8px;' +
                        'color:#f2a900;' +
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
                        'margin-top:8px;' +
                        'color:red;' +
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

                fetch("/trend-plus")
                    .then(function(response) {
                        return response.json();
                    })
                    .then(function(result) {

                        var box =
                            document.getElementById(
                                "trendStatus"
                            );

                        var data = result.data || {};

                        if (data.status === "waiting") {

                            box.className =
                                "status-box status-wait";

                            box.innerHTML =
                                "TREND PLUS: Menunggu " +
                                "data TradingView...";
                            return;
                        }

                        box.className =
                            "status-box status-ok";

                        var symbol =
                            data.symbol || "-";

                        var tf =
                            data.timeframe || "-";

                        var event =
                            data.event || "NONE";

                        var trend =
                            data.external_trend || "-";

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
                    .catch(function() {

                        var box =
                            document.getElementById(
                                "trendStatus"
                            );

                        box.className =
                            "status-box status-wait";

                        box.innerHTML =
                            "TREND PLUS: Gagal membaca " +
                            "data Render.";
                    });
            }


            refreshTrendStatus();

            setInterval(
                refreshTrendStatus,
                5000
            );

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

// This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at https://mozilla.org/MPL/2.0/
// © TFlab & Customized

//@version=5
indicator('TREND PLUS', overlay = true, max_bars_back = 5000, max_boxes_count = 500, max_labels_count = 500, max_lines_count = 500)

// --- INPUT TFLAB MARKET STRUCTURE ---
PP = input.int(5, 'Pivot Period of Order Blocks Detector', group = 'Logic Parameter', minval = 1)

ShZ = input.bool(true, 'Show Zig Zag Line', group = 'Zig Zag Line')
ZLS = input.string(line.style_solid, 'Zig Zag Line Style', options = [line.style_solid, line.style_dotted, line.style_dashed], group = 'Zig Zag Line')
ZLC = input.color(#2484bb, 'Zig Zag Line Color', group = 'Zig Zag Line')
ZLW = input.int(1, 'Zig Zag Line Width', group = 'Zig Zag Line')

ShL = input.bool(false, 'Show Label', group = 'Zig Zag Label')
LC = input.color(#0a378a, 'Label Color', group = 'Zig Zag Label')

MajorBuBoSLine_Show = input.string('On', 'Show Major Bullish BoS Lines', ['On', 'Off'], group = 'Major Bullish "BoS" Lines')
MajorBuBoSLine_Style = input.string(line.style_solid, 'Style Major Bullish BoS Lines', [line.style_solid, line.style_dashed, line.style_dotted], group = 'Major Bullish "BoS" Lines')
MajorBuBoSLine_Color = input.color(color.rgb(11, 95, 204), 'Color Major Bullish BoS Lines', group = 'Major Bullish "BoS" Lines')

MajorBeBoSLine_Show = input.string('On', 'Show Major Bearish BoS Lines', ['On', 'Off'], group = 'Major Bearish "BoS" Lines')
MajorBeBoSLine_Style = input.string(line.style_solid, 'Style Major Bearish BoS Lines', [line.style_solid, line.style_dashed, line.style_dotted], group = 'Major Bearish "BoS" Lines')
MajorBeBoSLine_Color = input.color(color.rgb(192, 123, 5), 'Color Major Bearish BoS Lines', group = 'Major Bearish "BoS" Lines')

MinorBuBoSLine_Show = input.string('Off', 'Show Minor Bullish BoS Lines', ['On', 'Off'], group = 'Minor Bullish "BoS" Lines')
MinorBuBoSLine_Style = input.string(line.style_dashed, 'Style Minor Bullish BoS Lines', [line.style_solid, line.style_dashed, line.style_dotted], group = 'Minor Bullish "BoS" Lines')
MinorBuBoSLine_Color = input.color(color.black, 'Color Minor Bullish BoS Lines', group = 'Minor Bullish "BoS" Lines')

MinorBeBoSLine_Show = input.string('Off', 'Show Minor Bearish BoS Lines', ['On', 'Off'], group = 'Minor Bearish "BoS" Lines')
MinorBeBoSLine_Style = input.string(line.style_dashed, 'Style Minor Bearish ChoCh Lines', [line.style_solid, line.style_dashed, line.style_dotted], group = 'Minor Bearish "BoS" Lines')
MinorBeBoSLine_Color = input.color(color.black, 'Color Minor Bearish "BoS" Lines', group = 'Minor Bearish "BoS" Lines')

MajorBuChoChLine_Show = input.string('On', 'Show Major Bullish ChoCh Lines', ['On', 'Off'], group = 'Major Bullish "ChoCh" Lines')
MajorBuChoChLine_Style = input.string(line.style_solid, 'Style Major Bullish ChoCh Lines', [line.style_solid, line.style_dashed, line.style_dotted], group = 'Major Bullish "ChoCh" Lines')
MajorBuChoChLine_Color = input.color(color.rgb(5, 119, 24), 'Color Major Bullish ChoCh Lines', group = 'Major Bullish "ChoCh" Lines')

MajorBeChoChLine_Show = input.string('On', 'Show Major Bearish ChoCh Lines', ['On', 'Off'], group = 'Major Bearish "ChoCh" Lines')
MajorBeChoChLine_Style = input.string(line.style_solid, 'Style Major Bearish ChoCh Lines', [line.style_solid, line.style_dashed, line.style_dotted], group = 'Major Bearish "ChoCh" Lines')
MajorBeChoChLine_Color = input.color(color.rgb(134, 23, 58), 'Color Major Bearish ChoCh Lines', group = 'Major Bearish "ChoCh" Lines')

MinorBuChoChLine_Show = input.string('Off', 'Show Minor Bullish ChoCh Lines', ['On', 'Off'], group = 'Minor Bullish "ChoCh" Lines')
MinorBuChoChLine_Style = input.string(line.style_dashed, 'Style Minor Bullish ChoCh Lines', [line.style_solid, line.style_dashed, line.style_dotted], group = 'Minor Bullish "ChoCh" Lines')
MinorBuChoChLine_Color = input.color(color.black, 'Color Minor Bullish ChoCh Lines', group = 'Minor Bullish "ChoCh" Lines')

MinorBeChoChLine_Show = input.string('Off', 'Show Minor Bearish ChoCh Lines', ['On', 'Off'], group = 'Minor Bearish "ChoCh" Lines')
MinorBeChoChLine_Style = input.string(line.style_dashed, 'Style Minor Bearish ChoCh Lines', [line.style_solid, line.style_dashed, line.style_dotted], group = 'Minor Bearish "ChoCh" Lines')
MinorBeChoChLine_Color = input.color(color.black, 'Color Minor Bearish ChoCh Lines', group = 'Minor Bearish "ChoCh" Lines')

// --- PEMBOLEHUBAH TFLAB ---
Open = open
High = high
Low = low
Close = close
Bar_Index = bar_index
ATR = ta.atr(55)

var ArrayType = array.new_string()
var ArrayValue = array.new_float()
var ArrayIndex = array.new_int()
var ArrayTypeAdv = array.new_string()
var ArrayValueAdv = array.new_float()
var ArrayIndexAdv = array.new_int()

var line ZZLine = na
var label Label = na

PASS = 0
HighPivot = ta.pivothigh(PP, PP)
LowPivot = ta.pivotlow(PP, PP)
HighValue = ta.valuewhen(HighPivot, High[PP], 0)
LowValue = ta.valuewhen(LowPivot, Low[PP], 0)
HighIndex = ta.valuewhen(HighPivot, Bar_Index[PP], 0)
LowIndex = ta.valuewhen(LowPivot, Bar_Index[PP], 0)
Correct_HighPivot = 0.0
Correct_LowPivot = 0.0

var float Major_HighLevel = na
var float Major_LowLevel = na
var int Major_HighIndex = na
var int Major_LowIndex = na
var string Major_HighType = na
var string Major_LowType = na

var float Minor_HighLevel = na
var float Minor_LowLevel = na
var int Minor_HighIndex = na
var int Minor_LowIndex = na
var string Minor_HighType = na
var string Minor_LowType = na
var int LockDetecteM_MinorLvL = 0

var bool Lock0 = true
var bool Lock1 = true

var int LastMHH = 0
var int Last02MHH = 0
var int LastMLH = 0
var int LastMLL = 0
var int Last02MLL = 0
var int LastMHL = 0
var int LastmHH = 0
var int Last02mHH = 0
var int LastmLH = 0
var int LastmLL = 0
var int Last02mLL = 0
var int LastmHL = 0

var string LastPivotType = na
var int LastPivotIndex = 0
var string LastPivotType02 = na
var int LastPivotIndex02 = 0

var float MajorHighValue01 = na
var int MajorHighIndex01 = na
var string MajorHighType01 = ''
var float MajorLowValue01 = na
var int MajorLowIndex01 = na
var string MajorLowType01 = ''

var float MinorHighValue01 = na
var int MinorHighIndex01 = na
var string MinorHighType01 = ''
var float MinorLowValue01 = na
var int MinorLowIndex01 = na
var string MinorLowType01 = ''

var float MajorHighValue02 = na
var int MajorHighIndex02 = na
var string MajorHighType02 = ''
var float MajorLowValue02 = na
var int MajorLowIndex02 = na
var string MajorLowType02 = ''

var float MinorHighValue02 = na
var int MinorHighIndex02 = na
var string MinorHighType02 = ''
var float MinorLowValue02 = na
var int MinorLowIndex02 = na
var string MinorLowType02 = ''

var line MajorLine_ChoChBull = na
var label MajorLabel_ChoChBull = na
var line MajorLine_ChoChBear = na
var label MajorLabel_ChoChBear = na
var line MajorLine_BoSBull = na
var label MajorLabel_BoSBull = na
var line MajorLine_BoSBear = na
var label MajorLabel_BoSBear = na

var line MinorLine_ChoChBull = na
var label MinorLabel_ChoChBull = na
var line MinorLine_ChoChBear = na
var label MinorLabel_ChoChBear = na
var line MinorLine_BoSBull = na
var label MinorLabel_BoSBull = na
var line MinorLine_BoSBear = na
var label MinorLabel_BoSBear = na

var bool Bullish_Major_ChoCh = false
var bool Bullish_Major_BoS = false
var bool Bearish_Major_ChoCh = false
var bool Bearish_Major_BoS = false
var BoS_MajorType = array.new_string()
var BoS_MajorIndex = array.new_int()
var ChoCh_MajorType = array.new_string()
var ChoCh_MajorIndex = array.new_int()
var int LockBreak_M = 0

var bool Bullish_Minor_ChoCh = false
var bool Bullish_Minor_BoS = false
var bool Bearish_Minor_ChoCh = false
var bool Bearish_Minor_BoS = false
var BoS_MinorType = array.new_string()
var BoS_MinorIndex = array.new_int()
var ChoCh_MinorType = array.new_string()
var ChoCh_MinorIndex = array.new_int()
var int LockBreak_m = 0

var string ExternalTrend = 'No Trend'
var string InternalTrend = 'No Trend'

// --- TFLAB ZIGZAG & MARKET STRUCTURE ---
if not na(HighPivot) and not na(LowPivot)
    if ArrayType.size() == 0
        PASS := 1
    else if ArrayType.size() >= 1
        if ArrayType.get(ArrayType.size() - 1) == "L" or ArrayType.get(ArrayType.size() - 1) == "LL"
            if LowPivot < ArrayValue.get(ArrayType.size() - 1)
                array.remove(ArrayType, ArrayType.size() - 1)
                array.remove(ArrayValue, ArrayValue.size() - 1)
                array.remove(ArrayIndex, ArrayIndex.size() - 1)
                array.push(ArrayType, ArrayType.size() > 2 ? ArrayValue.get(ArrayValue.size() - 2) < LowValue ? "HL" : "LL" : "L")
                array.push(ArrayValue, LowValue)
                array.push(ArrayIndex, LowIndex)
                Correct_LowPivot := LowValue
            else
                array.push(ArrayType, ArrayType.size() > 2 ? ArrayValue.get(ArrayValue.size() - 2) < HighValue ? "HH" : "LH" : "H")
                array.push(ArrayValue, HighValue)
                array.push(ArrayIndex, HighIndex)
            Correct_HighPivot := HighValue
        else if (ArrayType.get(ArrayType.size() - 1)) == "H" or (ArrayType.get(ArrayType.size() - 1)) == "HH"
            if HighPivot > ArrayValue.get(ArrayType.size() - 1)
                array.remove(ArrayType, ArrayType.size() - 1)
                array.remove(ArrayValue, ArrayValue.size() - 1)
                array.remove(ArrayIndex, ArrayValue.size() - 1)
                array.push(ArrayType, ArrayType.size() > 2 ? ArrayValue.get(ArrayValue.size() - 2) < HighValue ? "HH" : "LH" : "H")
                array.push(ArrayValue, HighValue)
                array.push(ArrayIndex, HighIndex)
                Correct_HighPivot := HighValue
            else
                array.push(ArrayType, ArrayType.size() > 2 ? ArrayValue.get(ArrayValue.size() - 2) < LowValue ? "HL" : "LL" : "L")
                array.push(ArrayValue, LowValue)
                array.push(ArrayIndex, LowIndex)
            Correct_LowPivot := LowValue
        else if (ArrayType.get(ArrayType.size() - 1)) == "LH"
            if HighPivot < ArrayValue.get(ArrayType.size() - 1)
                array.push(ArrayType, ArrayType.size() > 2 ? ArrayValue.get(ArrayValue.size() - 2) < LowValue ? "HL" : "LL" : "L")
                array.push(ArrayValue, LowValue)
                array.push(ArrayIndex, LowIndex)
                Correct_LowPivot := LowValue
            else if HighPivot > ArrayValue.get(ArrayType.size() - 1)
                if close < ArrayValue.get(ArrayType.size() - 1)
                    array.remove(ArrayType, ArrayType.size() - 1)
                    array.remove(ArrayValue, ArrayValue.size() - 1)
                    array.remove(ArrayIndex, ArrayValue.size() - 1)
                    array.push(ArrayType, ArrayType.size() > 2 ? ArrayValue.get(ArrayValue.size() - 2) < HighValue ? "HH" : "LH" : "H")
                    array.push(ArrayValue, HighValue)
                    array.push(ArrayIndex, HighIndex)
                    Correct_HighPivot := HighValue
                else if close > ArrayValue.get(ArrayType.size() - 1)
                    array.push(ArrayType, ArrayType.size() > 2 ? ArrayValue.get(ArrayValue.size() - 2) < LowValue ? "HL" : "LL" : "L")
                    array.push(ArrayValue, LowValue)
                    array.push(ArrayIndex, LowIndex)
                    Correct_LowPivot := LowValue
        else if (ArrayType.get(ArrayType.size() - 1)) == "HL"
            if LowPivot > ArrayValue.get(ArrayType.size() - 1)
                array.push(ArrayType, ArrayType.size() > 2 ? ArrayValue.get(ArrayValue.size() - 2) < HighValue ? "HH" : "LH" : "H")
                array.push(ArrayValue, HighValue)
                array.push(ArrayIndex, HighIndex)
                Correct_HighPivot := HighValue
            else if LowPivot < ArrayValue.get(ArrayType.size() - 1)
                if close > ArrayValue.get(ArrayType.size() - 1)
                    array.remove(ArrayType, ArrayType.size() - 1)
                    array.remove(ArrayValue, ArrayValue.size() - 1)
                    array.remove(ArrayIndex, ArrayValue.size() - 1)
                    array.push(ArrayType, ArrayType.size() > 2 ? ArrayValue.get(ArrayValue.size() - 2) < LowValue ? "HL" : "LL" : "L")
                    array.push(ArrayValue, LowValue)
                    array.push(ArrayIndex, LowIndex)
                    Correct_LowPivot := LowValue
                else if close < ArrayValue.get(ArrayType.size() - 1)
                    array.push(ArrayType, ArrayType.size() > 2 ? ArrayValue.get(ArrayValue.size() - 2) < HighValue ? "HH" : "LH" : "H")
                    array.push(ArrayValue, HighValue)
                    array.push(ArrayIndex, HighIndex)
                    Correct_HighPivot := HighValue
else if not na(HighPivot)
    if ArrayType.size() == 0
        array.insert(ArrayType, 0, "H")
        array.insert(ArrayValue, 0, HighValue)
        array.insert(ArrayIndex, 0, HighIndex)
        Correct_HighPivot := HighValue
    else if ArrayType.size() >= 1
        if ArrayType.get(ArrayType.size() - 1) == "L" or ArrayType.get(ArrayType.size() - 1) == "HL" or ArrayType.get(ArrayType.size() - 1) == "LL"
            if HighPivot > ArrayValue.get(ArrayType.size() - 1)
                array.push(ArrayType, ArrayType.size() > 2 ? ArrayValue.get(ArrayValue.size() - 2) < HighValue ? "HH" : "LH" : "H")
                array.push(ArrayValue, HighValue)
                array.push(ArrayIndex, HighIndex)
                Correct_HighPivot := HighValue
            else if HighPivot < ArrayValue.get(ArrayType.size() - 1)
                array.remove(ArrayType, ArrayType.size() - 1)
                array.remove(ArrayValue, ArrayValue.size() - 1)
                array.remove(ArrayIndex, ArrayValue.size() - 1)
                array.push(ArrayType, ArrayType.size() > 2 ? ArrayValue.get(ArrayValue.size() - 2) < LowValue ? "HL" : "LL" : "L")
                array.push(ArrayValue, LowValue)
                array.push(ArrayIndex, LowIndex)
                Correct_LowPivot := LowValue
        else if (ArrayType.get(ArrayType.size() - 1)) == "H" or (ArrayType.get(ArrayType.size() - 1)) == "HH" or (ArrayType.get(ArrayType.size() - 1)) == "LH"
            if ArrayValue.get(ArrayValue.size() - 1) < HighValue
                array.remove(ArrayType, ArrayType.size() - 1)
                array.remove(ArrayValue, ArrayValue.size() - 1)
                array.remove(ArrayIndex, ArrayValue.size() - 1)
                array.push(ArrayType, ArrayType.size() > 2 ? ArrayValue.get(ArrayValue.size() - 2) < HighValue ? "HH" : "LH" : "H")
                array.push(ArrayValue, HighValue)
                array.push(ArrayIndex, HighIndex)
                Correct_HighPivot := HighValue
else if not na(LowPivot)
    if ArrayType.size() == 0
        array.insert(ArrayType, 0, "L")
        array.insert(ArrayValue, 0, LowValue)
        array.insert(ArrayIndex, 0, LowIndex)
        Correct_LowPivot := LowValue
    else if ArrayType.size() >= 1
        if (ArrayType.get(ArrayType.size() - 1)) == "H" or (ArrayType.get(ArrayType.size() - 1)) == "HH" or (ArrayType.get(ArrayType.size() - 1)) == "LH"
            if LowPivot < ArrayValue.get(ArrayType.size() - 1)
                array.push(ArrayType, ArrayType.size() > 2 ? ArrayValue.get(ArrayValue.size() - 2) < LowValue ? "HL" : "LL" : "L")
                array.push(ArrayValue, LowValue)
                array.push(ArrayIndex, LowIndex)
                Correct_LowPivot := LowValue
            else if LowPivot > ArrayValue.get(ArrayType.size() - 1)
                array.remove(ArrayType, ArrayType.size() - 1)
                array.remove(ArrayValue, ArrayValue.size() - 1)
                array.remove(ArrayIndex, ArrayValue.size() - 1)
                array.push(ArrayType, ArrayType.size() > 2 ? ArrayValue.get(ArrayValue.size() - 2) < HighValue ? "HH" : "LH" : "H")
                array.push(ArrayValue, HighValue)
                array.push(ArrayIndex, HighIndex)
                Correct_HighPivot := HighValue
        else if (ArrayType.get(ArrayType.size() - 1)) == "L" or (ArrayType.get(ArrayType.size() - 1)) == "HL" or (ArrayType.get(ArrayType.size() - 1)) == "LL"
            if ArrayValue.get(ArrayValue.size() - 1) > LowValue
                array.remove(ArrayType, ArrayType.size() - 1)
                array.remove(ArrayValue, ArrayValue.size() - 1)
                array.remove(ArrayIndex, ArrayValue.size() - 1)
                array.push(ArrayType, ArrayType.size() > 2 ? ArrayValue.get(ArrayValue.size() - 2) < LowValue ? "HL" : "LL" : "L")
                array.push(ArrayValue, LowValue)
                array.push(ArrayIndex, LowIndex)
                Correct_LowPivot := LowValue

if ArrayType.size() == 2
    if ArrayType.get(0) == 'H'
        Major_HighLevel := ArrayValue.get(0)
        Major_LowLevel := ArrayValue.get(1)
        Major_HighIndex := ArrayIndex.get(0)
        Major_LowIndex := ArrayIndex.get(1)
        Major_HighType := ArrayType.get(0)
        Major_LowType := ArrayType.get(1)
    else if ArrayType.get(0) == 'L'
        Major_HighLevel := ArrayValue.get(1)
        Major_LowLevel := ArrayValue.get(0)
        Major_HighIndex := ArrayIndex.get(1)
        Major_LowIndex := ArrayIndex.get(0)
        Major_HighType := ArrayType.get(1)
        Major_LowType := ArrayType.get(0)

if ArrayValue.size() == 1
    if Lock0
        array.insert(ArrayTypeAdv, 0, 'M' + ArrayType.get(0))
        array.insert(ArrayValueAdv, 0, ArrayValue.get(0))
        array.insert(ArrayIndexAdv, 0, ArrayIndex.get(0))
        Lock0 := false

if ArrayValue.size() == 2
    if Lock1
        array.insert(ArrayTypeAdv, 1, 'M' + ArrayType.get(1))
        array.insert(ArrayValueAdv, 1, ArrayValue.get(1))
        array.insert(ArrayIndexAdv, 1, ArrayIndex.get(1))
        Lock1 := false

if ArrayValue.size() > 1
    if ArrayValue.get(ArrayValue.size() - 1)[1] != ArrayValue.get(ArrayValue.size() - 1)
        if str.substring(ArrayType.get(ArrayType.size() - 1)[1], str.length(ArrayType.get(ArrayType.size() - 1)) - 1) != str.substring(ArrayType.get(ArrayType.size() - 1), str.length(ArrayType.get(ArrayType.size() - 1)) - 1)
            array.push(ArrayTypeAdv, 'm' + ArrayType.get(ArrayType.size() - 1))
            array.push(ArrayValueAdv, ArrayValue.get(ArrayValue.size() - 1))
            array.push(ArrayIndexAdv, ArrayIndex.get(ArrayIndex.size() - 1))
        else if str.substring(ArrayType.get(ArrayType.size() - 1)[1], str.length(ArrayType.get(ArrayType.size() - 1)) - 1) == str.substring(ArrayType.get(ArrayType.size() - 1), str.length(ArrayType.get(ArrayType.size() - 1)) - 1)
            if ArrayValueAdv.size() > 0
                array.remove(ArrayValueAdv, ArrayValueAdv.size() - 1)
            if ArrayIndexAdv.size() > 0
                array.remove(ArrayIndexAdv, ArrayIndexAdv.size() - 1)
            array.push(ArrayValueAdv, ArrayValue.get(ArrayValue.size() - 1))
            array.push(ArrayIndexAdv, ArrayIndex.get(ArrayIndex.size() - 1))

if ArrayValueAdv.size() > 1
    if close > Major_HighLevel
        if ArrayTypeAdv.get(ArrayTypeAdv.size() - 1) == 'mL'
            ArrayTypeAdv.remove(ArrayTypeAdv.size() - 1)
            ArrayTypeAdv.push('ML')
            Major_LowLevel := ArrayValueAdv.get(ArrayValueAdv.size() - 1)
            Major_LowIndex := ArrayIndexAdv.get(ArrayValueAdv.size() - 1)
            Major_LowType := ArrayTypeAdv.get(ArrayTypeAdv.size() - 1)
        else if ArrayTypeAdv.get(ArrayTypeAdv.size() - 1) == 'mHL'
            ArrayTypeAdv.remove(ArrayTypeAdv.size() - 1)
            ArrayTypeAdv.push('M' + ArrayType.get(ArrayType.size() - 1))
            Major_LowLevel := ArrayValueAdv.get(ArrayValueAdv.size() - 1)
            Major_LowIndex := ArrayIndexAdv.get(ArrayValueAdv.size() - 1)
            Major_LowType := ArrayTypeAdv.get(ArrayTypeAdv.size() - 1)
        else if ArrayTypeAdv.get(ArrayTypeAdv.size() - 1) == 'mLL'
            ArrayTypeAdv.remove(ArrayTypeAdv.size() - 1)
            ArrayTypeAdv.push('M' + ArrayType.get(ArrayType.size() - 1))
            Major_LowLevel := ArrayValueAdv.get(ArrayValueAdv.size() - 1)
            Major_LowIndex := ArrayIndexAdv.get(ArrayValueAdv.size() - 1)
            Major_LowType := ArrayTypeAdv.get(ArrayTypeAdv.size() - 1)
        else if ArrayTypeAdv.get(ArrayTypeAdv.size() - 1) == 'mLH' or ArrayTypeAdv.get(ArrayTypeAdv.size() - 1) == 'mHH' or ArrayTypeAdv.get(ArrayTypeAdv.size() - 1) == 'MLH' or ArrayTypeAdv.get(ArrayTypeAdv.size() - 1) == 'MHH'
            if ArrayTypeAdv.size() >= 2
                if ArrayTypeAdv.get(ArrayTypeAdv.size() - 2) == 'mHL'
                    ArrayTypeAdv.remove(ArrayTypeAdv.size() - 2)
                    ArrayTypeAdv.insert(ArrayValueAdv.size() - 2, 'M' + ArrayType.get(ArrayType.size() - 2))
                    Major_LowLevel := ArrayValueAdv.get(ArrayValueAdv.size() - 2)
                    Major_LowIndex := ArrayIndexAdv.get(ArrayValueAdv.size() - 2)
                    Major_LowType := ArrayTypeAdv.get(ArrayTypeAdv.size() - 2)
                else if ArrayTypeAdv.get(ArrayTypeAdv.size() - 2) == 'mLL'
                    ArrayTypeAdv.remove(ArrayTypeAdv.size() - 2)
                    ArrayTypeAdv.insert(ArrayValueAdv.size() - 2, 'M' + ArrayType.get(ArrayType.size() - 2))
                    Major_LowLevel := ArrayValueAdv.get(ArrayValueAdv.size() - 2)
                    Major_LowIndex := ArrayIndexAdv.get(ArrayValueAdv.size() - 2)
                    Major_LowType := ArrayTypeAdv.get(ArrayTypeAdv.size() - 2)

    if ArrayValueAdv.get(ArrayValueAdv.size() - 1) > Major_HighLevel
        if ArrayTypeAdv.get(ArrayTypeAdv.size() - 1) == 'mH'
            ArrayTypeAdv.remove(ArrayTypeAdv.size() - 1)
            ArrayTypeAdv.push('MH')
            Major_HighLevel := ArrayValueAdv.get(ArrayValueAdv.size() - 1)
            Major_HighIndex := ArrayIndexAdv.get(ArrayValueAdv.size() - 1)
            Major_HighType := ArrayTypeAdv.get(ArrayTypeAdv.size() - 1)
        else if ArrayTypeAdv.get(ArrayTypeAdv.size() - 1) == 'mLH'
            ArrayTypeAdv.remove(ArrayTypeAdv.size() - 1)
            ArrayTypeAdv.push('M' + ArrayType.get(ArrayType.size() - 1))
            Major_HighLevel := ArrayValueAdv.get(ArrayValueAdv.size() - 1)
            Major_HighIndex := ArrayIndexAdv.get(ArrayValueAdv.size() - 1)
            Major_HighType := ArrayTypeAdv.get(ArrayTypeAdv.size() - 1)
        else if ArrayTypeAdv.get(ArrayTypeAdv.size() - 1) == 'mHH' or ArrayTypeAdv.get(ArrayTypeAdv.size() - 1) == 'MHH'
            ArrayTypeAdv.remove(ArrayTypeAdv.size() - 1)
            ArrayTypeAdv.push('M' + ArrayType.get(ArrayType.size() - 1))
            Major_HighLevel := ArrayValueAdv.get(ArrayValueAdv.size() - 1)
            Major_HighIndex := ArrayIndexAdv.get(ArrayValueAdv.size() - 1)
            Major_HighType := ArrayTypeAdv.get(ArrayTypeAdv.size() - 1)

    if close < Major_LowLevel
        if ArrayTypeAdv.get(ArrayTypeAdv.size() - 1) == 'mH'
            ArrayTypeAdv.remove(ArrayTypeAdv.size() - 1)
            ArrayTypeAdv.push('MH')
            Major_HighLevel := ArrayValueAdv.get(ArrayValueAdv.size() - 1)
            Major_HighIndex := ArrayIndexAdv.get(ArrayValueAdv.size() - 1)
            Major_HighType := ArrayTypeAdv.get(ArrayTypeAdv.size() - 1)
        else if ArrayTypeAdv.get(ArrayTypeAdv.size() - 1) == 'mLH'
            ArrayTypeAdv.remove(ArrayTypeAdv.size() - 1)
            ArrayTypeAdv.push('M' + ArrayType.get(ArrayType.size() - 1))
            Major_HighLevel := ArrayValueAdv.get(ArrayValueAdv.size() - 1)
            Major_HighIndex := ArrayIndexAdv.get(ArrayValueAdv.size() - 1)
            Major_HighType := ArrayTypeAdv.get(ArrayTypeAdv.size() - 1)
        else if ArrayTypeAdv.get(ArrayTypeAdv.size() - 1) == 'mHH'
            ArrayTypeAdv.remove(ArrayTypeAdv.size() - 1)
            ArrayTypeAdv.push('M' + ArrayType.get(ArrayType.size() - 1))
            Major_HighLevel := ArrayValueAdv.get(ArrayValueAdv.size() - 1)
            Major_HighIndex := ArrayIndexAdv.get(ArrayValueAdv.size() - 1)
            Major_HighType := ArrayTypeAdv.get(ArrayTypeAdv.size() - 1)
        else if ArrayTypeAdv.get(ArrayTypeAdv.size() - 1) == 'mHL' or ArrayTypeAdv.get(ArrayTypeAdv.size() - 1) == 'mLL' or ArrayTypeAdv.get(ArrayTypeAdv.size() - 1) == 'MHL' or ArrayTypeAdv.get(ArrayTypeAdv.size() - 1) == 'MLL'
            if ArrayTypeAdv.size() >= 2
                if ArrayTypeAdv.get(ArrayTypeAdv.size() - 2) == 'mLH'
                    ArrayTypeAdv.remove(ArrayTypeAdv.size() - 2)
                    ArrayTypeAdv.insert(ArrayValueAdv.size() - 2, 'M' + ArrayType.get(ArrayType.size() - 2))
                    Major_HighLevel := ArrayValueAdv.get(ArrayValueAdv.size() - 2)
                    Major_HighIndex := ArrayIndexAdv.get(ArrayValueAdv.size() - 2)
                    Major_HighType := ArrayTypeAdv.get(ArrayTypeAdv.size() - 2)
                else if ArrayTypeAdv.get(ArrayTypeAdv.size() - 2) == 'mHH'
                    ArrayTypeAdv.remove(ArrayTypeAdv.size() - 2)
                    ArrayTypeAdv.insert(ArrayValueAdv.size() - 2, 'M' + ArrayType.get(ArrayType.size() - 2))
                    Major_HighLevel := ArrayValueAdv.get(ArrayValueAdv.size() - 2)
                    Major_HighIndex := ArrayIndexAdv.get(ArrayValueAdv.size() - 2)
                    Major_HighType := ArrayTypeAdv.get(ArrayTypeAdv.size() - 2)

    if ArrayValueAdv.get(ArrayValueAdv.size() - 1) < Major_LowLevel
        if ArrayTypeAdv.get(ArrayTypeAdv.size() - 1) == 'mL'
            ArrayTypeAdv.remove(ArrayTypeAdv.size() - 1)
            ArrayTypeAdv.push('ML')
            Major_LowLevel := ArrayValueAdv.get(ArrayValueAdv.size() - 1)
            Major_LowIndex := ArrayIndexAdv.get(ArrayValueAdv.size() - 1)
            Major_LowType := ArrayTypeAdv.get(ArrayTypeAdv.size() - 1)
        else if ArrayTypeAdv.get(ArrayTypeAdv.size() - 1) == 'mHL'
            ArrayTypeAdv.remove(ArrayTypeAdv.size() - 1)
            ArrayTypeAdv.push('M' + ArrayType.get(ArrayType.size() - 1))
            Major_LowLevel := ArrayValueAdv.get(ArrayValueAdv.size() - 1)
            Major_LowIndex := ArrayIndexAdv.get(ArrayValueAdv.size() - 1)
            Major_LowType := ArrayTypeAdv.get(ArrayTypeAdv.size() - 1)
        else if ArrayTypeAdv.get(ArrayTypeAdv.size() - 1) == 'mLL' or ArrayTypeAdv.get(ArrayTypeAdv.size() - 1) == 'MLL'
            ArrayTypeAdv.remove(ArrayTypeAdv.size() - 1)
            ArrayTypeAdv.push('M' + ArrayType.get(ArrayType.size() - 1))
            Major_LowLevel := ArrayValueAdv.get(ArrayValueAdv.size() - 1)
            Major_LowIndex := ArrayIndexAdv.get(ArrayValueAdv.size() - 1)
            Major_LowType := ArrayTypeAdv.get(ArrayTypeAdv.size() - 1)

// Safe major/minor pivot drawing
if ArrayTypeAdv.size() >= 2
    int X1 = ArrayIndexAdv.get(ArrayIndexAdv.size() - 2)
    float Y1 = ArrayValueAdv.get(ArrayValueAdv.size() - 2)
    int X2 = ArrayIndexAdv.get(ArrayIndexAdv.size() - 1)
    float Y2 = ArrayValueAdv.get(ArrayValueAdv.size() - 1)
    string T1 = ArrayTypeAdv.get(ArrayTypeAdv.size() - 1)
    string T1_Display = T1 == "MHH" ? "HH" : T1 == "MLH" ? "LH" : T1 == "MHL" ? "HL" : T1 == "MLL" ? "LL" : T1

    ZZLine := line.new(X1, Y1, X2, Y2, color = ShZ ? ZLC : #ffffff00, style = ZLS, width = ZLW)

    if ShL
        Label := label.new(x = X2, y = Y2, text = T1_Display, color = color.rgb(255,255,255,100), style = T1 == "L" or T1 == "LL" or T1 == "HL" or T1 == "mL" or T1 == "mLL" or T1 == "mHL" or T1 == "ML" or T1 == "MLL" or T1 == "MHL" ? label.style_label_up : label.style_label_down, textcolor = LC, size = size.small)

    if not na(ZZLine[1])
        if line.get_x1(ZZLine) == line.get_x1(ZZLine[1])
            if not na(Label[1])
                label.delete(Label[1])
            line.delete(ZZLine[1])

if ArrayTypeAdv.size() > 0
    if str.pos(ArrayTypeAdv.get(ArrayTypeAdv.size() - 1), 'M') == 0
        LockDetecteM_MinorLvL := 0
        Minor_HighLevel := na
        Minor_LowLevel := na
        Minor_HighIndex := na
        Minor_LowIndex := na
        Minor_HighType := na
        Minor_LowType := na
        InternalTrend := 'No Trend'

if not na(Major_HighLevel) and not na(Major_HighIndex)
    if ta.crossover(close, Major_HighLevel) and LockBreak_M != Major_HighIndex
        if ExternalTrend == 'No Trend' or ExternalTrend == 'Up Trend'
            Bullish_Major_BoS := true
            array.push(BoS_MajorType, 'Bull Major BoS')
            array.push(BoS_MajorIndex, bar_index)
            LockBreak_M := Major_HighIndex
            ExternalTrend := 'Up Trend'
            if MajorBuBoSLine_Show == 'On'
                MajorLine_BoSBull := line.new(Major_HighIndex, Major_HighLevel, bar_index, Major_HighLevel, style = MajorBuBoSLine_Style, color = MajorBuBoSLine_Color)
                MajorLabel_BoSBull := label.new((Major_HighIndex + bar_index) / 2, Major_HighLevel, text = 'Major BoS', color = color.rgb(0,0,0,100), textcolor = MajorBuBoSLine_Color, size = size.normal)
        else if ExternalTrend == 'Down Trend'
            Bullish_Major_ChoCh := true
            array.push(ChoCh_MajorType, 'Bull Major ChoCh')
            array.push(ChoCh_MajorIndex, bar_index)
            LockBreak_M := Major_HighIndex
            ExternalTrend := 'Up Trend'
            if MajorBuChoChLine_Show == 'On'
                MajorLine_ChoChBull := line.new(Major_HighIndex, Major_HighLevel, bar_index, Major_HighLevel, style = MajorBuChoChLine_Style, color = MajorBuChoChLine_Color)
                MajorLabel_ChoChBull := label.new((Major_HighIndex + bar_index) / 2, Major_HighLevel, text = 'Major ChoCh', color = color.rgb(0,0,0,100), textcolor = MajorBuChoChLine_Color, size = size.normal)
    else
        Bullish_Major_ChoCh := false
        Bullish_Major_BoS := false
else
    Bullish_Major_ChoCh := false
    Bullish_Major_BoS := false

if not na(Major_LowLevel) and not na(Major_LowIndex)
    if ta.crossunder(close, Major_LowLevel) and LockBreak_M != Major_LowIndex
        if ExternalTrend == 'No Trend' or ExternalTrend == 'Down Trend'
            Bearish_Major_BoS := true
            array.push(BoS_MajorType, 'Bear Major BoS')
            array.push(BoS_MajorIndex, bar_index)
            LockBreak_M := Major_LowIndex
            ExternalTrend := 'Down Trend'
            if MajorBeBoSLine_Show == 'On'
                MajorLine_BoSBear := line.new(Major_LowIndex, Major_LowLevel, bar_index, Major_LowLevel, style = MajorBeBoSLine_Style, color = MajorBeBoSLine_Color)
                MajorLabel_BoSBear := label.new((Major_LowIndex + bar_index) / 2, Major_LowLevel, text = 'Major BoS', color = color.rgb(0,0,0,100), textcolor = MajorBeBoSLine_Color, style = label.style_label_up, size = size.normal)
        else if ExternalTrend == 'Up Trend'
            Bearish_Major_ChoCh := true
            array.push(ChoCh_MajorType, 'Bear Major ChoCh')
            array.push(ChoCh_MajorIndex, bar_index)
            LockBreak_M := Major_LowIndex
            ExternalTrend := 'Down Trend'
            if MajorBeChoChLine_Show == 'On'
                MajorLine_ChoChBear := line.new(Major_LowIndex, Major_LowLevel, bar_index, Major_LowLevel, style = MajorBeChoChLine_Style, color = MajorBeChoChLine_Color)
                MajorLabel_ChoChBear := label.new((Major_LowIndex + bar_index) / 2, Major_LowLevel, text = 'Major ChoCh', color = color.rgb(0,0,0,100), textcolor = MajorBeChoChLine_Color, style = label.style_label_up, size = size.normal)
    else
        Bearish_Major_ChoCh := false
        Bearish_Major_BoS := false
else
    Bearish_Major_ChoCh := false
    Bearish_Major_BoS := false

// --- MODUL 6: PULLBACK SAH & MOMENTUM COLOR ---
grp_pb = "MODUL CONFIRMED PULLBACK CANDLE"
enable_pb_mod = input.bool(true, "ON/OFF Modul Pullback Sah", group=grp_pb)
col_buy_pb = input.color(color.yellow, "Warna BUY Pullback Sah (KUNING)", group=grp_pb)
col_sell_pb = input.color(color.blue, "Warna SELL Pullback Sah (BIRU)", group=grp_pb)

bool is_bullish_engulf = close > open and close[1] < open[1] and close >= open[1]
bool is_bearish_engulf = close < open and close[1] > open[1] and close <= open[1]

bool valid_buy_pullback = enable_pb_mod and is_bullish_engulf and (close > high[1])
bool valid_sell_pullback = enable_pb_mod and is_bearish_engulf and (close < low[1])

color final_candle_color = na
if valid_buy_pullback
    final_candle_color := col_buy_pb
else if valid_sell_pullback
    final_candle_color := col_sell_pb

barcolor(final_candle_color)

// --- PURPLE CORE ---
grp_core = "TETAPAN PURPLE CORE (PRO)"
show_core = input.bool(true, title="Papar Purple Core", group=grp_core)
core_len = input.int(50, title="Tempoh MA (Period)", group=grp_core, minval=1)
core_type = input.string("SMMA", title="Jenis MA Core", options=["SMMA", "EMA", "SMA", "WMA", "VWMA", "RMA", "T3"], group=grp_core)
core_mult = input.float(1.0, title="Faktor Kembang Line", group=grp_core, step=0.1)
t3_factor = input.float(0.7, title="T3 Constant (Smoothing)", group=grp_core, minval=0.0, maxval=1.0, step=0.1)
core_color = input.color(#b300ff, title="Warna Purple Core", group=grp_core)

f_smma(src, len) =>
    var float smma_val = na
    if na(smma_val[1])
        smma_val := ta.sma(src, len)
    else
        smma_val := (smma_val[1] * (len - 1) + src) / len
    smma_val

f_t3(src, len, f) =>
    xe1 = ta.ema(src, len)
    xe2 = ta.ema(xe1, len)
    xe3 = ta.ema(xe2, len)
    xe4 = ta.ema(xe3, len)
    xe5 = ta.ema(xe4, len)
    xe6 = ta.ema(xe5, len)
    c1 = -f * f * f
    c2 = 3 * f * f + 3 * f * f * f
    c3 = -6 * f * f - 3 * f - 3 * f * f * f
    c4 = 1 + 3 * f + f * f * f + 3 * f * f
    c1 * xe6 + c2 * xe5 + c3 * xe4 + c4 * xe3

float base_ma = switch core_type
    "SMMA" => f_smma(close, core_len)
    "EMA" => ta.ema(close, core_len)
    "SMA" => ta.sma(close, core_len)
    "WMA" => ta.wma(close, core_len)
    "VWMA" => ta.vwma(close, core_len)
    "RMA" => ta.rma(close, core_len)
    "T3" => f_t3(close, core_len, t3_factor)
    => f_smma(close, core_len)

float core_line = base_ma * core_mult
plot(show_core ? core_line : na, title="Purple Core Outer Glow", color=color.new(core_color, 85), linewidth=8)
plot(show_core ? core_line : na, title="Purple Core Inner Glow", color=color.new(core_color, 60), linewidth=5)
plot(show_core ? core_line : na, title="Purple Core Line", color=core_color, linewidth=2)

// --- M-STRUCTURE & ZIGZAG RIDETREND ---
length = input.int(10, title="Swing High/Low Length (Ridetrend)", group="M-Structure Settings", minval=1)
showLabels = input.bool(true, title="Show Price Action Labels", group="M-Structure Settings")
showZigZagR = input.bool(true, title="Show Ridetrend Zig Zag", group="M-Structure Settings")
zzColorR = input.color(color.white, title="Ridetrend Zig Zag Color", group="M-Structure Settings")

grp_swing_r = "=== STRUKTUR AKAR / PUCUK (KANAN) ==="
show_swing_hl = input.bool(true, "Show Swing H / Swing L", group=grp_swing_r)
swing_len = input.int(15, "Pivot Length (Untuk Swing Label)", group=grp_swing_r)

grp_sig = "TETAPAN SIGNAL REMPIT & ATR"
show_banner = input.bool(true, "Show Signal REMPIT", group=grp_sig)
cci_len = input.int(20, "CCI Period", group=grp_sig)
atr_per = input.int(5, "ATR Period", group=grp_sig)
sl_atr = input.float(2.0, "Stop Loss ATR", group=grp_sig)
tp1_atr = input.float(1.0, "Take Profit 1 ATR", group=grp_sig)
tp2_atr = input.float(2.0, "Take Profit 2 ATR", group=grp_sig)
tp3_atr = input.float(3.0, "Take Profit 3 ATR", group=grp_sig)

phR = ta.pivothigh(high, length, length)
plR = ta.pivotlow(low, length, length)

var int ms_type = 0
var float ms_price = na
var int ms_bar = na
var float ms_open = na
var float ms_close = na
var float prev_struct_pucuk = na
var float prev_struct_akar = na

var label ms_pucuk_label = na
var label ms_akar_label = na
var line last_leg_line = na

if not na(phR)
    int ph_bar = bar_index - length
    float ph_open = open[length]
    float ph_close = close[length]

    if ms_type == 1
        if na(ms_price) or phR > ms_price
            ms_price := phR
            ms_bar := ph_bar
            ms_open := ph_open
            ms_close := ph_close

            if showZigZagR and not na(last_leg_line)
                line.set_x2(last_leg_line, ms_bar)
                line.set_y2(last_leg_line, ms_price)

            string pucuk_sfx = na(prev_struct_pucuk) ? "HH" : (phR > prev_struct_pucuk ? "HH" : "LH")
            if showLabels
                if na(ms_pucuk_label)
                    ms_pucuk_label := label.new(ms_bar, ms_price, "PUCUK " + str.tostring(ms_price, "#.##") + " " + pucuk_sfx, color=color.purple, textcolor=color.white, style=label.style_label_down, size=size.small)
                else
                    label.set_xy(ms_pucuk_label, ms_bar, ms_price)
                    label.set_text(ms_pucuk_label, "PUCUK " + str.tostring(ms_price, "#.##") + " " + pucuk_sfx)

    else
        if not na(ms_price)
            if showZigZagR and not na(ms_bar)
                last_leg_line := line.new(ms_bar, ms_price, ph_bar, phR, color=zzColorR, width=1)

        string pucuk_sfx = na(prev_struct_pucuk) ? "HH" : (phR > prev_struct_pucuk ? "HH" : "LH")
        prev_struct_pucuk := phR
        ms_type := 1
        ms_price := phR
        ms_bar := ph_bar
        ms_open := ph_open
        ms_close := ph_close

        if showLabels
            ms_pucuk_label := label.new(ph_bar, phR, "PUCUK " + str.tostring(phR, "#.##") + " " + pucuk_sfx, color=color.purple, textcolor=color.white, style=label.style_label_down, size=size.small)

if not na(plR)
    int pl_bar = bar_index - length
    float pl_open = open[length]
    float pl_close = close[length]

    if ms_type == -1
        if na(ms_price) or plR < ms_price
            ms_price := plR
            ms_bar := pl_bar
            ms_open := pl_open
            ms_close := pl_close

            if showZigZagR and not na(last_leg_line)
                line.set_x2(last_leg_line, ms_bar)
                line.set_y2(last_leg_line, ms_price)

            string akar_sfx = na(prev_struct_akar) ? "LL" : (plR > prev_struct_akar ? "HL" : "LL")
            if showLabels
                if na(ms_akar_label)
                    ms_akar_label := label.new(ms_bar, ms_price, "AKAR " + str.tostring(ms_price, "#.##") + " " + akar_sfx, color=color.aqua, textcolor=color.white, style=label.style_label_up, size=size.small)
                else
                    label.set_xy(ms_akar_label, ms_bar, ms_price)
                    label.set_text(ms_akar_label, "AKAR " + str.tostring(ms_price, "#.##") + " " + akar_sfx)

    else
        if not na(ms_price)
            if showZigZagR and not na(ms_bar)
                last_leg_line := line.new(ms_bar, ms_price, pl_bar, plR, color=zzColorR, width=1)

        string akar_sfx = na(prev_struct_akar) ? "LL" : (plR > prev_struct_akar ? "HL" : "LL")
        prev_struct_akar := plR
        ms_type := -1
        ms_price := plR
        ms_bar := pl_bar
        ms_open := pl_open
        ms_close := pl_close

        if showLabels
            ms_akar_label := label.new(pl_bar, plR, "AKAR " + str.tostring(plR, "#.##") + " " + akar_sfx, color=color.aqua, textcolor=color.white, style=label.style_label_up, size=size.small)

// --- STRUKTUR AKAR / PUCUK (KANAN) ---
ph_swing = ta.pivothigh(high, swing_len, swing_len)
pl_swing = ta.pivotlow(low, swing_len, swing_len)

var float last_swing_h = na
var int last_swing_h_bar = na
var float last_swing_l = na
var int last_swing_l_bar = na

if not na(ph_swing)
    last_swing_h := ph_swing
    last_swing_h_bar := bar_index - swing_len
if not na(pl_swing)
    last_swing_l := pl_swing
    last_swing_l_bar := bar_index - swing_len

var line line_sh = na
var label lbl_sh = na
var line line_sl = na
var label lbl_sl = na

if show_swing_hl and barstate.islast
    if not na(line_sh)
        line.delete(line_sh)
    if not na(lbl_sh)
        label.delete(lbl_sh)
    if not na(line_sl)
        line.delete(line_sl)
    if not na(lbl_sl)
        label.delete(lbl_sl)

    int swing_offset = 30
    if not na(last_swing_h)
        line_sh := line.new(last_swing_h_bar, last_swing_h, bar_index + swing_offset, last_swing_h, color=color.purple, style=line.style_dashed, width=1)
        lbl_sh := label.new(bar_index + swing_offset, last_swing_h, "Swing H " + str.tostring(last_swing_h, format.mintick), color=color.purple, textcolor=color.white, style=label.style_label_left, size=size.small)
    if not na(last_swing_l)
        line_sl := line.new(last_swing_l_bar, last_swing_l, bar_index + swing_offset, last_swing_l, color=color.aqua, style=line.style_dashed, width=1)
        lbl_sl := label.new(bar_index + swing_offset, last_swing_l, "Swing L " + str.tostring(last_swing_l, format.mintick), color=color.aqua, textcolor=color.white, style=label.style_label_left, size=size.small)

// --- SIGNAL REMPIT & ATR (DENGAN PENJEJAK TP RINGKAS) ---
cci_val = ta.cci(close, cci_len)
signal_atr = ta.atr(atr_per)
global_vol_sma = ta.sma(volume, 20)

bool smart_buy = ta.crossover(cci_val, -100) or (close > open and volume > global_vol_sma)
bool smart_sell = ta.crossunder(cci_val, 100) or (close < open and volume > global_vol_sma)

var label active_sig_lbl = na
var line active_sl_line = na
var line active_tp1_line = na
var line active_tp2_line = na
var line active_tp3_line = na
var label active_sl_lbl = na
var label active_tp1_lbl = na
var label active_tp2_lbl = na
var label active_tp3_lbl = na

int line_length_atr = 12

var int active_trade_dir = 0
var float active_trade_sl = na
var float active_trade_tp1 = na
var float active_trade_tp2 = na
var float active_trade_tp3 = na
var bool active_tp1_hit = false
var bool active_tp2_hit = false
var bool active_tp3_hit = false

if show_banner and smart_buy
    if not na(active_sig_lbl)
        label.delete(active_sig_lbl)
    if not na(active_sl_line)
        line.delete(active_sl_line)
    if not na(active_tp1_line)
        line.delete(active_tp1_line)
    if not na(active_tp2_line)
        line.delete(active_tp2_line)
    if not na(active_tp3_line)
        line.delete(active_tp3_line)
    if not na(active_sl_lbl)
        label.delete(active_sl_lbl)
    if not na(active_tp1_lbl)
        label.delete(active_tp1_lbl)
    if not na(active_tp2_lbl)
        label.delete(active_tp2_lbl)
    if not na(active_tp3_lbl)
        label.delete(active_tp3_lbl)

    float entry_price = low
    float sl_val  = entry_price - (signal_atr * sl_atr)
    float tp1_val = entry_price + (signal_atr * tp1_atr)
    float tp2_val = entry_price + (signal_atr * tp2_atr)
    float tp3_val = entry_price + (signal_atr * tp3_atr)

    active_trade_dir := 1
    active_trade_sl := sl_val
    active_trade_tp1 := tp1_val
    active_trade_tp2 := tp2_val
    active_trade_tp3 := tp3_val
    active_tp1_hit := false
    active_tp2_hit := false
    active_tp3_hit := false

    active_sig_lbl := label.new(bar_index, low, "BUY\n" + str.tostring(entry_price, "#.##"), color=color.yellow, textcolor=color.black, style=label.style_label_up)

    int line_end = bar_index + line_length_atr
    
    active_sl_line  := line.new(bar_index, sl_val, line_end, sl_val, color=color.red, width=1, style=line.style_dashed)
    active_tp1_line := line.new(bar_index, tp1_val, line_end, tp1_val, color=color.yellow, width=1, style=line.style_dashed)
    active_tp2_line := line.new(bar_index, tp2_val, line_end, tp2_val, color=color.orange, width=1, style=line.style_dashed)
    active_tp3_line := line.new(bar_index, tp3_val, line_end, tp3_val, color=color.blue, width=1, style=line.style_dashed)

    active_sl_lbl  := label.new(line_end, sl_val, "SL: " + str.tostring(sl_val, "#.##"), color=color.red, textcolor=color.white, style=label.style_label_left, size=size.tiny)
    active_tp1_lbl := label.new(line_end, tp1_val, "TP1: " + str.tostring(tp1_val, "#.##"), color=color.yellow, textcolor=color.black, style=label.style_label_left, size=size.tiny)
    active_tp2_lbl := label.new(line_end, tp2_val, "TP2: " + str.tostring(tp2_val, "#.##"), color=color.orange, textcolor=color.white, style=label.style_label_left, size=size.tiny)
    active_tp3_lbl := label.new(line_end, tp3_val, "TP3: " + str.tostring(tp3_val, "#.##"), color=color.blue, textcolor=color.white, style=label.style_label_left, size=size.tiny)

if show_banner and smart_sell
    if not na(active_sig_lbl)
        label.delete(active_sig_lbl)
    if not na(active_sl_line)
        line.delete(active_sl_line)
    if not na(active_tp1_line)
        line.delete(active_tp1_line)
    if not na(active_tp2_line)
        line.delete(active_tp2_line)
    if not na(active_tp3_line)
        line.delete(active_tp3_line)
    if not na(active_sl_lbl)
        label.delete(active_sl_lbl)
    if not na(active_tp1_lbl)
        label.delete(active_tp1_lbl)
    if not na(active_tp2_lbl)
        label.delete(active_tp2_lbl)
    if not na(active_tp3_lbl)
        label.delete(active_tp3_lbl)

    float entry_price = high
    float sl_val  = entry_price + (signal_atr * sl_atr)
    float tp1_val = entry_price - (signal_atr * tp1_atr)
    float tp2_val = entry_price - (signal_atr * tp2_atr)
    float tp3_val = entry_price - (signal_atr * tp3_atr)

    active_trade_dir := -1
    active_trade_sl := sl_val
    active_trade_tp1 := tp1_val
    active_trade_tp2 := tp2_val
    active_trade_tp3 := tp3_val
    active_tp1_hit := false
    active_tp2_hit := false
    active_tp3_hit := false

    active_sig_lbl := label.new(bar_index, high, "SELL\n" + str.tostring(entry_price, "#.##"), color=color.blue, textcolor=color.white, style=label.style_label_down)

    int line_end = bar_index + line_length_atr
    
    active_sl_line  := line.new(bar_index, sl_val, line_end, sl_val, color=color.red, width=1, style=line.style_dashed)
    active_tp1_line := line.new(bar_index, tp1_val, line_end, tp1_val, color=color.yellow, width=1, style=line.style_dashed)
    active_tp2_line := line.new(bar_index, tp2_val, line_end, tp2_val, color=color.orange, width=1, style=line.style_dashed)
    active_tp3_line := line.new(bar_index, tp3_val, line_end, tp3_val, color=color.blue, width=1, style=line.style_dashed)

    active_sl_lbl  := label.new(line_end, sl_val, "SL: " + str.tostring(sl_val, "#.##"), color=color.red, textcolor=color.white, style=label.style_label_left, size=size.tiny)
    active_tp1_lbl := label.new(line_end, tp1_val, "TP1: " + str.tostring(tp1_val, "#.##"), color=color.yellow, textcolor=color.black, style=label.style_label_left, size=size.tiny)
    active_tp2_lbl := label.new(line_end, tp2_val, "TP2: " + str.tostring(tp2_val, "#.##"), color=color.orange, textcolor=color.white, style=label.style_label_left, size=size.tiny)
    active_tp3_lbl := label.new(line_end, tp3_val, "TP3: " + str.tostring(tp3_val, "#.##"), color=color.blue, textcolor=color.white, style=label.style_label_left, size=size.tiny)

// --- LOGIK PENJEJAK (TRACKER) TP DICAPAI ✅ (RINGKAS) ---
if active_trade_dir == 1
    if not active_tp1_hit and high >= active_trade_tp1
        active_tp1_hit := true
        if not na(active_tp1_lbl)
            label.set_text(active_tp1_lbl, "TP1 ✅: " + str.tostring(active_trade_tp1, "#.##"))
    if not active_tp2_hit and high >= active_trade_tp2
        active_tp2_hit := true
        if not na(active_tp2_lbl)
            label.set_text(active_tp2_lbl, "TP2 ✅: " + str.tostring(active_trade_tp2, "#.##"))
    if not active_tp3_hit and high >= active_trade_tp3
        active_tp3_hit := true
        if not na(active_tp3_lbl)
            label.set_text(active_tp3_lbl, "TP3 ✅: " + str.tostring(active_trade_tp3, "#.##"))
        active_trade_dir := 0 
    if low <= active_trade_sl
        active_trade_dir := 0 

if active_trade_dir == -1
    if not active_tp1_hit and low <= active_trade_tp1
        active_tp1_hit := true
        if not na(active_tp1_lbl)
            label.set_text(active_tp1_lbl, "TP1 ✅: " + str.tostring(active_trade_tp1, "#.##"))
    if not active_tp2_hit and low <= active_trade_tp2
        active_tp2_hit := true
        if not na(active_tp2_lbl)
            label.set_text(active_tp2_lbl, "TP2 ✅: " + str.tostring(active_trade_tp2, "#.##"))
    if not active_tp3_hit and low <= active_trade_tp3
        active_tp3_hit := true
        if not na(active_tp3_lbl)
            label.set_text(active_tp3_lbl, "TP3 ✅: " + str.tostring(active_trade_tp3, "#.##"))
        active_trade_dir := 0
    if high >= active_trade_sl
        active_trade_dir := 0

// ============================================================================
// ELLIOTT WAVE SYSTEM
// ============================================================================
grp_ew = "ELLIOTT WAVE"
show_ew = input.bool(true, "ON/OFF Elliott Wave", group=grp_ew)
ew_tf = input.timeframe("", "Timeframe Elliott Wave (Kosong =ikut Chart)", group=grp_ew)
ew_length = input.int(10, "Elliott Pivot Length", minval=1, group=grp_ew)
ew_show_lines = input.bool(true, "Show Elliott Lines", group=grp_ew)
ew_line_color = input.color(color.yellow, "Elliott Line Color", group=grp_ew)
ew_label_size = input.string("Small", "Elliott Label Size", options=["Tiny", "Small", "Normal"], group=grp_ew)
ew_offset_mult = input.float(0.5, "Jarak Label EW (Gandaan ATR)", minval=0.0, step=0.1, group=grp_ew)

f_ew_calc(len) =>
    [ta.pivothigh(high, len, len), ta.pivotlow(low, len, len)]

[r_ph, r_pl] = request.security(syminfo.tickerid, ew_tf, f_ew_calc(ew_length))

var int[] ew_times = array.new_int()
var float[] ew_prices = array.new_float()
var int[] ew_types = array.new_int()
var label[] ew_labels = array.new_label()
var line[] ew_lines = array.new_line()

f_ew_size(sz) => sz == "Tiny" ? size.tiny : sz == "Normal" ? size.normal : size.small
f_ew_name(n) => 
    string name_val = "0"
    int mod_val = n % 9
    if mod_val == 0
        name_val := "0"
    else if mod_val == 1
        name_val := "1"
    else if mod_val == 2
        name_val := "2"
    else if mod_val == 3
        name_val := "3"
    else if mod_val == 4
        name_val := "4"
    else if mod_val == 5
        name_val := "5"
    else if mod_val == 6
        name_val := "A"
    else if mod_val == 7
        name_val := "B"
    else if mod_val == 8
        name_val := "C"
    name_val

f_ew_clear_drawings() =>
    if array.size(ew_labels) > 0
        for j = array.size(ew_labels) - 1 to 0
            label.delete(array.get(ew_labels, j))
    if array.size(ew_lines) > 0
        for j = array.size(ew_lines) - 1 to 0
            line.delete(array.get(ew_lines, j))
    array.clear(ew_labels)
    array.clear(ew_lines)

f_ew_add(_time, _price, _type) =>
    bool changed = false
    int sz = array.size(ew_types)
    if sz == 0
        array.push(ew_times, _time)
        array.push(ew_prices, _price)
        array.push(ew_types, _type)
        changed := true
    else
        int last_type = array.get(ew_types, sz - 1)
        if _type != last_type
            array.push(ew_times, _time)
            array.push(ew_prices, _price)
            array.push(ew_types, _type)
            changed := true
        else
            int last_idx = sz - 1
            float last_price = array.get(ew_prices, last_idx)
            bool more_extreme = (_type == 1 and _price > last_price) or (_type == -1 and _price < last_price)
            if more_extreme
                array.set(ew_times, last_idx, _time)
                array.set(ew_prices, last_idx, _price)
                changed := true
    changed

bool ew_changed = false

if show_ew
    if not na(r_ph)
        ew_changed := f_ew_add(time[ew_length], r_ph, 1) or ew_changed
    if not na(r_pl)
        ew_changed := f_ew_add(time[ew_length], r_pl, -1) or ew_changed

    while array.size(ew_times) > 30
        array.shift(ew_times)
        array.shift(ew_prices)
        array.shift(ew_types)
        ew_changed := true

    if ew_changed or barstate.islast
        f_ew_clear_drawings()
        int n = array.size(ew_times)
        if n > 0
            float ew_offset = ta.atr(14) * ew_offset_mult
            for j = 0 to n - 1
                int etime = array.get(ew_times, j)
                float ep = array.get(ew_prices, j)
                int et = array.get(ew_types, j)
                float number_price = et == 1 ? ep + ew_offset : ep - ew_offset
                label el = label.new(x=etime, y=number_price, text=f_ew_name(j), xloc=xloc.bar_time, yloc=yloc.price, color=ew_line_color, textcolor=color.black, style=et == 1 ? label.style_label_down : label.style_label_up, size=f_ew_size(ew_label_size))
                array.push(ew_labels, el)

                if ew_show_lines and j > 0
                    int prev_time = array.get(ew_times, j - 1)
                    float prev_price = array.get(ew_prices, j - 1)
                    line ln = line.new(x1=prev_time, y1=prev_price, x2=etime, y2=ep, xloc=xloc.bar_time, color=ew_line_color, width=1)
                    array.push(ew_lines, ln)
else
    if array.size(ew_labels) > 0 or array.size(ew_lines) > 0
        f_ew_clear_drawings()

// ============================================================================
// MTF DASHBOARD - AUTO 4 TIMEFRAME FIXED + AOV & MCDX LOGIC
// ============================================================================
grp_mtf = "TETAPAN DASHBOARD MTF"

show_mtf_dashboard = input.bool(true, "Tunjuk Dashboard", group=grp_mtf)

mtf_m1_on  = input.bool(true,  "Papar M1",  group=grp_mtf)
mtf_m3_on  = input.bool(false, "Papar M3",  group=grp_mtf)
mtf_m5_on  = input.bool(true,  "Papar M5",  group=grp_mtf)
mtf_m15_on = input.bool(true,  "Papar M15", group=grp_mtf)
mtf_m30_on = input.bool(false, "Papar M30", group=grp_mtf)
mtf_h1_on  = input.bool(true,  "Papar H1",  group=grp_mtf)
mtf_h4_on  = input.bool(true,  "Papar H4",  group=grp_mtf)
mtf_d1_on  = input.bool(false, "Papar D1",  group=grp_mtf)
mtf_w1_on  = input.bool(false, "Papar W1",  group=grp_mtf)

mtf_size = input.string("Tiny", "Saiz Dashboard", options=["Tiny", "Small", "Normal"], group=grp_mtf)
mtf_position = input.string("Bottom Left", "Kedudukan Dashboard", options=["Bottom Left", "Top Left", "Top Right", "Bottom Right"], group=grp_mtf)

mtf_bg = input.color(color.new(color.black, 100), "Background Transparan", group=grp_mtf)
mtf_border = input.color(color.black, "Border", group=grp_mtf)

f_mtf_theme_text() =>
    float _r = color.r(chart.bg_color)
    float _g = color.g(chart.bg_color)
    float _b = color.b(chart.bg_color)
    float _brightness = (_r * 0.299) + (_g * 0.587) + (_b * 0.114)
    _brightness > 128.0 ? color.black : color.white

mtf_text = f_mtf_theme_text()

color mtf_buy = color.yellow
color mtf_sell = color.blue
color mtf_sideway = color.orange

color mtf_up = input.color(color.red, "UP (Banker - Merah)", group=grp_mtf)
color mtf_down = input.color(color.lime, "DOWN (Retailer - Hijau)", group=grp_mtf)

f_mtf_size(_s) =>
    _s == "Small" ? size.small : _s == "Normal" ? size.normal : size.tiny

f_mtf_position(_p) =>
    _p == "Top Left" ? position.top_left : _p == "Top Right" ? position.top_right : _p == "Bottom Right" ? position.bottom_right : position.bottom_left

f_mtf_price(_tf) =>
    request.security(syminfo.tickerid, _tf, close)

f_mtf_signal(_tf) =>
    float _cci = request.security(syminfo.tickerid, _tf, ta.cci(close, 20))
    float _ema = request.security(syminfo.tickerid, _tf, ta.ema(close, 50))
    float _cl = request.security(syminfo.tickerid, _tf, close)
    _cci >= 0 and _cl >= _ema ? 1 : _cci < 0 and _cl < _ema ? -1 : _cl >= _ema ? 1 : -1

f_calc_aov_state() =>
    float _rsi_b = ta.rsi(close, 19)
    float _rsi_r = ta.rsi(close, 19)

    float _b_bar_raw = _rsi_b > 50.5 ? (_rsi_b - 50.5) * 0.9 : 0
    _b_bar_raw := _b_bar_raw > 20 ? 20 : _b_bar_raw
    float _pct_b_mentah = (_b_bar_raw / 20) * 100

    float _r_bar_raw = _rsi_r < 50.5 ? (50.5 - _rsi_r) * 0.9 : 0
    _r_bar_raw := _r_bar_raw > 20 ? 20 : _r_bar_raw
    float _pct_r_mentah = (_r_bar_raw / 20) * 100

    float _pct_b = ta.sma(_pct_b_mentah, 3)
    float _pct_r = ta.sma(_pct_r_mentah, 3)

    if (_pct_b + _pct_r > 100)
        float _total = _pct_b + _pct_r
        _pct_b := (_pct_b / _total) * 100
        _pct_r := (_pct_r / _total) * 100

    float _pct_h = 100 - _pct_b - _pct_r
    _pct_h := _pct_h < 0 ? 0 : _pct_h

    float _line_b_pct = _rsi_b > 50.5 ? (_rsi_b - 50.5) * 1.2 : 0
    _line_b_pct := _line_b_pct > 20 ? 20 : _line_b_pct
    _line_b_pct := (_line_b_pct / 20) * 100

    float _line_r_pct = _rsi_r < 50.5 ? (50.5 - _rsi_r) * 1.2 : 0
    _line_r_pct := _line_r_pct > 20 ? 20 : _line_r_pct
    _line_r_pct := (_line_r_pct / 20) * 100

    float _line_h_pct = 100 - _line_b_pct - _line_r_pct

    float _purple = ta.rma(_line_b_pct, 10) 
    float _cyan   = ta.rma(_line_r_pct, 10) 

    int _state = 0 

    if _purple > _cyan and _pct_b > 20 
        _state := 1
    else if _cyan > _purple and _pct_r > 20 
        _state := -1
    else 
        _state := 0

    _state

f_mtf_trend_aov(_tf) =>
    request.security(syminfo.tickerid, _tf, f_calc_aov_state())

f_mtf_signal_text(_v) =>
    _v > 0 ? "BUY ↑" : "SELL ↓"

f_mtf_trend_text(_v) =>
    _v > 0 ? "UP ↑" : _v < 0 ? "DOWN ↓" : "SIDEWAY ↔"

f_mtf_signal_color(_v) =>
    _v > 0 ? mtf_buy : mtf_sell

float mtf_p_m1  = f_mtf_price("1")
float mtf_p_m3  = f_mtf_price("3")
float mtf_p_m5  = f_mtf_price("5")
float mtf_p_m15 = f_mtf_price("15")
float mtf_p_m30 = f_mtf_price("30")
float mtf_p_h1  = f_mtf_price("60")
float mtf_p_h4  = f_mtf_price("240")
float mtf_p_d1  = f_mtf_price("D")
float mtf_p_w1  = f_mtf_price("W")

int mtf_s_m1  = f_mtf_signal("1")
int mtf_s_m3  = f_mtf_signal("3")
int mtf_s_m5  = f_mtf_signal("5")
int mtf_s_m15 = f_mtf_signal("15")
int mtf_s_m30 = f_mtf_signal("30")
int mtf_s_h1  = f_mtf_signal("60")
int mtf_s_h4  = f_mtf_signal("240")
int mtf_s_d1  = f_mtf_signal("D")
int mtf_s_w1  = f_mtf_signal("W")

int mtf_t_m1  = f_mtf_trend_aov("1")
int mtf_t_m3  = f_mtf_trend_aov("3")
int mtf_t_m5  = f_mtf_trend_aov("5")
int mtf_t_m15 = f_mtf_trend_aov("15")
int mtf_t_m30 = f_mtf_trend_aov("30")
int mtf_t_h1  = f_mtf_trend_aov("60")
int mtf_t_h4  = f_mtf_trend_aov("240")
int mtf_t_d1  = f_mtf_trend_aov("D")
int mtf_t_w1  = f_mtf_trend_aov("W")

var table mtf_table = table.new(position.bottom_left, 4, 5, frame_color=mtf_border, frame_width=1, border_color=color.new(mtf_border, 70), border_width=1)

f_mtf_is_chart_tf(_tf) =>
    float _a = timeframe.in_seconds(_tf)
    float _b = timeframe.in_seconds()
    _a == _b

f_mtf_clear() =>
    for _r = 0 to 4
        for _c = 0 to 3
            table.cell(mtf_table, _c, _r, "", bgcolor=color.new(color.black, 100), text_size=size.tiny)

f_mtf_draw_row(_r, _name, _price, _sig, _trend) =>
    color row_signal_color = f_mtf_signal_color(_sig)
    color trend_text_col = _trend > 0 ? mtf_up : _trend < 0 ? mtf_down : mtf_sideway
    color trend_bg_col = mtf_bg 

    table.cell(mtf_table, 0, _r, _name, text_color=row_signal_color, bgcolor=mtf_bg, text_halign=text.align_center, text_size=f_mtf_size(mtf_size))
    table.cell(mtf_table, 1, _r, str.tostring(_price, format.mintick), text_color=row_signal_color, bgcolor=mtf_bg, text_halign=text.align_center, text_size=f_mtf_size(mtf_size))
    table.cell(mtf_table, 2, _r, f_mtf_signal_text(_sig), text_color=row_signal_color, bgcolor=mtf_bg, text_halign=text.align_center, text_size=f_mtf_size(mtf_size))
    table.cell(mtf_table, 3, _r, f_mtf_trend_text(_trend), text_color=trend_text_col, bgcolor=trend_bg_col, text_halign=text.align_center, text_size=f_mtf_size(mtf_size))

if barstate.islast
    f_mtf_clear()

    if show_mtf_dashboard
        table.cell(mtf_table, 0, 0, "TF", text_color=mtf_text, bgcolor=mtf_bg, text_halign=text.align_center, text_size=f_mtf_size(mtf_size))
        table.cell(mtf_table, 1, 0, "PRICE", text_color=mtf_text, bgcolor=mtf_bg, text_halign=text.align_center, text_size=f_mtf_size(mtf_size))
        table.cell(mtf_table, 2, 0, "SIGNAL", text_color=mtf_text, bgcolor=mtf_bg, text_halign=text.align_center, text_size=f_mtf_size(mtf_size))
        table.cell(mtf_table, 3, 0, "TREND", text_color=mtf_text, bgcolor=mtf_bg, text_halign=text.align_center, text_size=f_mtf_size(mtf_size))

        int row = 1

        if mtf_m1_on and not f_mtf_is_chart_tf("1") and row <= 4
            f_mtf_draw_row(row, "M1", mtf_p_m1, mtf_s_m1, mtf_t_m1)
            row += 1
        if mtf_m3_on and not f_mtf_is_chart_tf("3") and row <= 4
            f_mtf_draw_row(row, "M3", mtf_p_m3, mtf_s_m3, mtf_t_m3)
            row += 1
        if mtf_m5_on and not f_mtf_is_chart_tf("5") and row <= 4
            f_mtf_draw_row(row, "M5", mtf_p_m5, mtf_s_m5, mtf_t_m5)
            row += 1
        if mtf_m15_on and not f_mtf_is_chart_tf("15") and row <= 4
            f_mtf_draw_row(row, "M15", mtf_p_m15, mtf_s_m15, mtf_t_m15)
            row += 1
        if mtf_m30_on and not f_mtf_is_chart_tf("30") and row <= 4
            f_mtf_draw_row(row, "M30", mtf_p_m30, mtf_s_m30, mtf_t_m30)
            row += 1
        if mtf_h1_on and not f_mtf_is_chart_tf("60") and row <= 4
            f_mtf_draw_row(row, "H1", mtf_p_h1, mtf_s_h1, mtf_t_h1)
            row += 1
        if mtf_h4_on and not f_mtf_is_chart_tf("240") and row <= 4
            f_mtf_draw_row(row, "H4", mtf_p_h4, mtf_s_h4, mtf_t_h4)
            row += 1
        if mtf_d1_on and not f_mtf_is_chart_tf("D") and row <= 4
            f_mtf_draw_row(row, "D1", mtf_p_d1, mtf_s_d1, mtf_t_d1)
            row += 1
        if mtf_w1_on and not f_mtf_is_chart_tf("W") and row <= 4
            f_mtf_draw_row(row, "W1", mtf_p_w1, mtf_s_w1, mtf_t_w1)
            row += 1

// ============================================================================
// ORDER BLOCK ENGINE [BIGBELUGA]
// ============================================================================
gp_st = 'Custom Supertrend Settings (Beluga)'
st_len = input.int(50, title = 'Volatility SMA Length', group = gp_st)
st_mult = input.float(3.5, title = 'Multiplier', step = 0.1, group = gp_st)
show_fill = input.bool(true, title = 'Show Trend Cloud Fill', group = gp_st)

gp_cloud = 'Trend Cloud Settings'
cloud_bull_col = input.color(#00ffcc, title = 'Bullish Cloud Color', group = gp_cloud)
cloud_bear_col = input.color(#ff007f, title = 'Bearish Cloud Color', group = gp_cloud)

gp_ob = 'Order Block Settings (Beluga)'
pivot_len = input.int(7, title = 'Pivot Strength', minval = 1, group = gp_ob)
bull_col = input.color(#00ffcc, title = 'Bullish OB Color', group = gp_ob)
bear_col = input.color(#ff007f, title = 'Bearish OB Color', group=gp_ob)
txt_col = input.color(#e0e0e0, title = 'OB Text Label Color', group = gp_ob)
delete_on_break = input.bool(true, title = 'Delete OB on Complete Break', group = gp_ob)

gp_filt = 'Retest Filter Settings (Beluga)'
show_bull_retest = input.bool(true, title = 'Bullish Retest Signals', group = gp_filt, inline = 'bull_ret')
bull_vol_pct    = input.float(50.0, title = 'Min Buy %', minval = 0.0, maxval = 100.0, step = 5.0, group = gp_filt, inline = 'bull_ret')
bull_sig_col    = input.color(#00ffcc, title = 'Color', group = gp_filt, inline = 'bull_ret')

show_bear_retest = input.bool(true, title = 'Bearish Retest Signals', group = gp_filt, inline = 'bear_ret')
bear_vol_pct    = input.float(50.0, title = 'Min Sell %', minval = 0.0, maxval = 100.0, step = 5.0, group = gp_filt, inline = 'bear_ret')
bear_sig_col    = input.color(#ff007f, title = 'Color', group = gp_filt, inline = 'bear_ret')

src_bb = hl2
custom_atr_bb = ta.sma(high - low, st_len)
var float upper_band = na
var float lower_band = na

upper_band := src_bb + st_mult * custom_atr_bb
lower_band := src_bb - st_mult * custom_atr_bb
prevLowerBand = nz(lower_band[1])
prevUpperBand = nz(upper_band[1])

lower_band := lower_band > prevLowerBand or close[1] < prevLowerBand ? lower_band : prevLowerBand
upper_band := upper_band < prevUpperBand or close[1] > prevUpperBand ? upper_band : prevUpperBand
int market_trend = na
float trend_stop = na
prevSuperTrend = nz(trend_stop[1])

if na(custom_atr_bb[1])
    market_trend := 1
else if prevSuperTrend == prevUpperBand
    market_trend := close > upper_band ? 1 : -1
else
    market_trend := close < lower_band ? -1 : 1
trend_stop := market_trend == 1 ? lower_band : upper_band

pivot_low_bb = ta.pivotlow(low, pivot_len, pivot_len)
pivot_high_bb = ta.pivothigh(high, pivot_len, pivot_len)

var box active_top_box = na
var box active_bot_box = na
var float active_top = na
var float active_bot = na
var float active_buy_ratio = na
var int active_ob_trend = 0

is_overlapping(float new_top, float new_bot) =>
    if na(active_top) or na(active_bot)
        false
    else
        not(new_bot > active_top or new_top < active_bot)

p_idx = bar_index - pivot_len

get_window_volume_ratio(int lookback_len) =>
    float buy_vol = 0.0
    float sell_vol = 0.0
    for i = 0 to lookback_len by 1
        if close[i] >= open[i]
            buy_vol := buy_vol + volume[i]
        else
            sell_vol := sell_vol + volume[i]
    total_vol = buy_vol + sell_vol
    float buy_pct = total_vol > 0 ? buy_vol / total_vol : 0.5
    buy_pct

var int ob_start_bar = na

if market_trend == 1 and not na(pivot_low_bb)
    ob_top = math.min(open[pivot_len], close[pivot_len])
    ob_bot = ob_top - custom_atr_bb

    if not is_overlapping(ob_top, ob_bot)
        if not na(active_top_box)
            box.set_right(active_top_box, p_idx)
            box.set_right(active_bot_box, p_idx)
        ob_start_bar := p_idx
        active_top := ob_top
        active_bot := ob_bot
        active_ob_trend := 1

        float buy_ratio = get_window_volume_ratio(pivot_len)
        active_buy_ratio := buy_ratio
        float sell_ratio = 1.0 - buy_ratio
        float split_price = active_bot + (active_top - active_bot) * buy_ratio

        string top_text = 'Sell: ' + str.tostring(math.round(sell_ratio * 100)) + '%'
        string bot_text = 'Buy: ' + str.tostring(math.round(buy_ratio * 100)) + '%'

        active_top_box := box.new(left = ob_start_bar, top = active_top, right = bar_index, bottom = split_price, bgcolor = color.new(bull_col, 85), border_color = color.new(bull_col, 40), text = top_text, text_color = txt_col, text_size = size.small, text_valign = text.align_center, text_halign = text.align_right)
        active_bot_box := box.new(left = ob_start_bar, top = split_price, right = bar_index, bottom = active_bot, bgcolor = color.new(bull_col, 75), border_color = color.new(bull_col, 40), text = bot_text, text_color = txt_col, text_size = size.small, text_valign = text.align_center, text_halign = text.align_right)

if market_trend == -1 and not na(pivot_high_bb)
    ob_bot = math.max(open[pivot_len], close[pivot_len])
    ob_top = ob_bot + custom_atr_bb

    if not is_overlapping(ob_top, ob_bot)
        if not na(active_top_box)
            box.set_right(active_top_box, p_idx)
            box.set_right(active_bot_box, p_idx)

        ob_start_bar := p_idx
        active_top := ob_top
        active_bot := ob_bot
        active_ob_trend := -1

        float buy_ratio = get_window_volume_ratio(pivot_len)
        active_buy_ratio := buy_ratio
        float sell_ratio = 1.0 - buy_ratio
        float split_price = active_bot + (active_top - active_bot) * buy_ratio

        string top_text = 'Sell: ' + str.tostring(math.round(sell_ratio * 100)) + '%'
        string bot_text = 'Buy: ' + str.tostring(math.round(buy_ratio * 100)) + '%'

        active_top_box := box.new(left = ob_start_bar, top = active_top, right = bar_index, bottom = split_price, bgcolor = color.new(bear_col, 75), border_color = color.new(bear_col, 40), text = top_text, text_color = txt_col, text_size = size.small, text_valign = text.align_center, text_halign = text.align_right)
        active_bot_box := box.new(left = ob_start_bar, top = split_price, right = bar_index, bottom = active_bot, bgcolor = color.new(bear_col, 85), border_color = color.new(bear_col, 40), text = bot_text, text_color = txt_col, text_size = size.small, text_valign = text.align_center, text_halign = text.align_right)

if delete_on_break and not na(active_top) and not na(active_bot)
    bool is_broken = (active_ob_trend == 1 and high < active_bot) or (active_ob_trend == -1 and low > active_top)
    if is_broken
        box.delete(active_top_box)
        box.delete(active_bot_box)
        active_top := na
        active_bot := na
        active_ob_trend := 0

if not na(active_top_box) and not na(active_bot_box)
    box.set_right(active_top_box, bar_index)
    box.set_right(active_bot_box, bar_index)

float active_sell_ratio = 1.0 - active_buy_ratio
float bull_threshold   = bull_vol_pct / 100.0
float bear_threshold   = bear_vol_pct / 100.0

marketChange = market_trend != market_trend[1]

bool buy_retest = ta.crossover(low, active_top) and show_bull_retest and na(pivot_low_bb) and not na(active_top) and (active_buy_ratio >= bull_threshold) and not marketChange and barstate.isconfirmed
bool sell_retest = ta.crossunder(high, active_bot) and na(pivot_high_bb) and show_bear_retest and not na(active_bot) and (active_sell_ratio >= bear_threshold) and not marketChange and barstate.isconfirmed

st_plot = plot(market_trend != market_trend[1] ? na : trend_stop, title = 'Trend Stop', color = market_trend == 1 ? cloud_bull_col : cloud_bear_col, linewidth = 1, style = plot.style_linebr)
price_plot = plot(close, title = 'Close Price Reference', display = display.none)

fill_color = show_fill ? (market_trend == 1 ? color.new(cloud_bull_col, 80) : color.new(cloud_bear_col, 80)) : na
fill(price_plot, st_plot, color=fill_color)

plotshape(buy_retest, title = "Bullish OB Retest", style = shape.cross, location = location.belowbar, color = bull_sig_col, size = size.tiny)
plotshape(sell_retest, title = "Bearish OB Retest", style = shape.cross, location = location.abovebar, color = bear_sig_col, size = size.tiny)

// ============================================================================
// SUPPLY / DEMAND + RBS / SBR
// ============================================================================

grp_sd = "TETAPAN SUPPLY & DEMAND"
sd_zoneWidth = input.int(150, title="Zone Width (Legacy - tidak digunakan)", group=grp_sd, minval=1)
sd_historyToKeep = input.int(5, title="History To Keep (Max Zones)", group=grp_sd, minval=1)
sd_showZones = input.bool(true, title="Show Supply & Demand / RBS & SBR Zones", group=grp_sd)
sd_length = input.int(10, title="Swing High/High Length (Pivot Period)", group=grp_sd, minval=1)

sd_phR = ta.pivothigh(high, sd_length, sd_length)
sd_plR = ta.pivotlow(low, sd_length, sd_length)

var int sd_ms_type = 0
var float sd_ms_price = na
var int sd_ms_bar = na

type SDZoneBox
    box b
    label lbl
    float top_p
    float bot_p
    string z_type
    bool is_active

var SDZoneBox[] sd_zone_list = array.new<SDZoneBox>()

f_sd_zone_text_color() =>
    chart.fg_color

f_sd_center_zone_label(SDZoneBox _z, string _txt) =>
    int _left = box.get_left(_z.b)
    int _right = box.get_right(_z.b)
    int _mid = int(math.round((_left + _right) / 2.0))
    float _price_mid = (_z.top_p + _z.bot_p) / 2.0

    if na(_z.lbl)
        _z.lbl := label.new(_mid, _price_mid, _txt, xloc=xloc.bar_index, yloc=yloc.price, style=label.style_none, textcolor=f_sd_zone_text_color(), size=size.small)
    else
        label.set_xy(_z.lbl, _mid, _price_mid)
        label.set_text(_z.lbl, _txt)
        label.set_textcolor(_z.lbl, f_sd_zone_text_color())

    box.set_text(_z.b, "")

f_sd_delete_active_supply() =>
    if array.size(sd_zone_list) > 0
        for i = array.size(sd_zone_list) - 1 to 0
            SDZoneBox z = array.get(sd_zone_list, i)
            if z.z_type == "SUPPLY" and z.is_active
                box.delete(z.b)
                if not na(z.lbl)
                    label.delete(z.lbl)
                array.remove(sd_zone_list, i)

f_sd_delete_active_demand() =>
    if array.size(sd_zone_list) > 0
        for i = array.size(sd_zone_list) - 1 to 0
            SDZoneBox z = array.get(sd_zone_list, i)
            if z.z_type == "DEMAND" and z.is_active
                box.delete(z.b)
                if not na(z.lbl)
                    label.delete(z.lbl)
                array.remove(sd_zone_list, i)

if sd_showZones and array.size(sd_zone_list) > 0
    for i = array.size(sd_zone_list) - 1 to 0
        SDZoneBox z = array.get(sd_zone_list, i)
        box.set_right(z.b, bar_index)
        f_sd_center_zone_label(z, z.z_type)

        if z.is_active
            if z.z_type == "SUPPLY" and close > z.top_p
                z.z_type := "RBS"
                box.set_bgcolor(z.b, color.new(color.aqua, 62))
                box.set_border_color(z.b, color.new(color.aqua, 15))
                f_sd_center_zone_label(z, "RBS")
                z.is_active := false
            else if z.z_type == "DEMAND" and close < z.bot_p
                z.z_type := "SBR"
                box.set_bgcolor(z.b, color.new(color.red, 65))
                box.set_border_color(z.b, color.new(color.red, 20))
                f_sd_center_zone_label(z, "SBR")
                z.is_active := false
        else
            if z.z_type == "RBS" and close < z.bot_p
                box.delete(z.b)
                if not na(z.lbl)
                    label.delete(z.lbl)
                array.remove(sd_zone_list, i)
            else if z.z_type == "SBR" and close > z.top_p
                box.delete(z.b)
                if not na(z.lbl)
                    label.delete(z.lbl)
                array.remove(sd_zone_list, i)

if not na(sd_phR)
    int sd_ph_bar = bar_index - sd_length
    float sd_ph_open = open[sd_length]
    float sd_ph_close = close[sd_length]

    if sd_ms_type == 1
        if na(sd_ms_price) or sd_phR > sd_ms_price
            sd_ms_price := sd_phR
            sd_ms_bar := sd_ph_bar
            if sd_showZones
                f_sd_delete_active_supply()
                float sd_pucuk_body = math.max(sd_ph_open, sd_ph_close)
                box sd_new_supply = box.new(left=sd_ph_bar, top=sd_phR, right=bar_index, bottom=sd_pucuk_body, bgcolor=color.new(color.red, 65), border_color=color.new(color.red, 20), text="")
                array.push(sd_zone_list, SDZoneBox.new(sd_new_supply, na, sd_phR, sd_pucuk_body, "SUPPLY", true))
    else
        sd_ms_type := 1
        sd_ms_price := sd_phR
        sd_ms_bar := sd_ph_bar
        if sd_showZones
            f_sd_delete_active_supply()
            float sd_pucuk_body = math.max(sd_ph_open, sd_ph_close)
            box sd_new_supply = box.new(left=sd_ph_bar, top=sd_phR, right=bar_index, bottom=sd_pucuk_body, bgcolor=color.new(color.red, 65), border_color=color.new(color.red, 20), text="")
            array.push(sd_zone_list, SDZoneBox.new(sd_new_supply, na, sd_phR, sd_pucuk_body, "SUPPLY", true))

if not na(sd_plR)
    int sd_pl_bar = bar_index - sd_length
    float sd_pl_open = open[sd_length]
    float sd_pl_close = close[sd_length]

    if sd_ms_type == -1
        if na(sd_ms_price) or sd_plR < sd_ms_price
            sd_ms_price := sd_plR
            sd_ms_bar := sd_pl_bar
            if sd_showZones
                f_sd_delete_active_demand()
                float sd_akar_body = math.min(sd_pl_open, sd_pl_close)
                box sd_new_demand = box.new(left=sd_pl_bar, top=sd_akar_body, right=bar_index, bottom=sd_plR, bgcolor=color.new(color.aqua, 62), border_color=color.new(color.aqua, 15), text="")
                array.push(sd_zone_list, SDZoneBox.new(sd_new_demand, na, sd_akar_body, sd_plR, "DEMAND", true))
    else
        sd_ms_type := -1
        sd_ms_price := sd_plR
        sd_ms_bar := sd_pl_bar
        if sd_showZones
            f_sd_delete_active_demand()
            float sd_akar_body = math.min(sd_pl_open, sd_pl_close)
            box sd_new_demand = box.new(left=sd_pl_bar, top=sd_akar_body, right=bar_index, bottom=sd_plR, bgcolor=color.new(color.aqua, 62), border_color=color.new(color.aqua, 15), text="")
            array.push(sd_zone_list, SDZoneBox.new(sd_new_demand, na, sd_akar_body, sd_plR, "DEMAND", true))

if sd_showZones and array.size(sd_zone_list) > sd_historyToKeep
    SDZoneBox sd_oldest = array.shift(sd_zone_list)
    box.delete(sd_oldest.b)
    if not na(sd_oldest.lbl)
        label.delete(sd_oldest.lbl)

// ============================================================================
// MODUL MULTI-TIMEFRAME STRONG BREAKOUT (BO) DENGAN PENGESAHAN CLOSE CANDLE
// ============================================================================
grp_brk = "TETAPAN SIGNAL BREAKOUT"
show_breakout = input.bool(true, "Papar Signal Breakout (BO)", group=grp_brk)
bo_tf = input.timeframe("", "Timeframe Breakout (Kosong = ikut carta semasa)", group=grp_brk)
bo_buy_col = input.color(color.lime, "Warna Breakout Buy", group=grp_brk)
bo_sell_col = input.color(color.red, "Warna Breakout Sell", group=grp_brk)

f_in_active_zone_tf(top_val, bot_val) =>
    bool in_zone = false
    if not na(top_val) and not na(bot_val)
        if high >= bot_val and low <= top_val
            in_zone := true
    in_zone

[tf_high, tf_low, tf_open, tf_close, tf_top, tf_bot] = request.security(syminfo.tickerid, bo_tf, [high, low, open, close, active_top, active_bot])

bool tf_has_two_shadows = (tf_high[1] > math.max(tf_open[1], tf_close[1])) and (tf_low[1] < math.min(tf_open[1], tf_close[1]))
bool tf_price_break_upper = (tf_close > tf_high[1]) and (tf_close > tf_open)
bool tf_price_break_lower = (tf_close < tf_low[1]) and (tf_close < tf_open)

var bool tf_signal_locked = false
bool tf_in_zone = f_in_active_zone_tf(tf_top, tf_bot)

if not tf_in_zone
    tf_signal_locked := false

bool valid_tf_bo_buy = show_breakout and tf_in_zone and not tf_signal_locked and tf_has_two_shadows and tf_price_break_upper
bool valid_tf_bo_sell = show_breakout and tf_in_zone and not tf_signal_locked and tf_has_two_shadows and tf_price_break_lower

if valid_tf_bo_buy
    tf_signal_locked := true
    label.new(bar_index, low, "BO", color=bo_buy_col, textcolor=color.black, style=label.style_label_up, size=size.tiny)

if valid_tf_bo_sell
    tf_signal_locked := true
    label.new(bar_index, high, "BO", color=bo_sell_col, textcolor=color.white, style=label.style_label_down, size=size.tiny)
