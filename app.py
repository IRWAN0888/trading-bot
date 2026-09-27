
import os
from flask import Flask, jsonify, render_template_string, request
import google.generativeai as genai
from openai import OpenAI

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

gemini_model = None
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-3.8-flash')

openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

@app.route('/')
def home():
    return "XAUUSD MCDX PRIME+ Multi-AI Copilot by IRWAN (irwan0888) is Live!"

@app.route('/ask', methods=['POST'])
def ask_ai():
    data = request.get_json()
    user_prompt = data.get('prompt', '')
    ai_engine = data.get('engine', 'gemini')
    
    system_context = (
        "Anda ialah AI Copilot peribadi untuk trader bernama IRWAN (irwan0888). "
        "Pakar analisis pasaran XAUUSD merentas semua timeframe menggunakan SOP indikator MCDX PRIME+ "
        "(garis Banker, Hot Money, Retailer, serta silangan G1-G3 untuk Buy dan DC1-DC3 untuk Sell). "
        "Berikan jawapan teknikal yang tajam dan profesional dalam Bahasa Melayu."
    )
    
    reply_text = ""
    try:
        if ai_engine == 'chatgpt':
            if not openai_client:
                return jsonify({"reply": "Ralat: Kunci API OpenAI (ChatGPT) belum ditetapkan di Render."}), 400
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_context},
                    {"role": "user", "content": user_prompt}
                ]
            )
            reply_text = response.choices[0].message.content
        else:
            if not gemini_model:
                return jsonify({"reply": "Ralat: Kunci API Gemini belum ditetapkan di Render."}), 400
            response = gemini_model.generate_content(f"{system_context}\n\nSoalan Trader: {user_prompt}")
            reply_text = response.text
            
        return jsonify({"reply": reply_text})
    except Exception as e:
        return jsonify({"reply": f"Ralat sambungan API: {str(e)}"}), 500

@app.route('/capture')
def capture():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>XAUUSD MCDX PRIME+ Multi-AI Copilot - IRWAN (irwan0888)</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { background-color: #131722; color: #d1d4dc; font-family: Arial, sans-serif; margin: 0; padding: 10px; }
            h1 { color: #f2a900; font-size: 14px; text-align: center; }
            .container { display: flex; flex-direction: column; gap: 10px; }
            .chart-box { background: #1e222d; padding: 6px; border-radius: 8px; }
            .chat-box { background: #1e222d; padding: 10px; border-radius: 8px; height: 340px; display: flex; flex-direction: column; }
            .chat-messages { flex: 1; overflow-y: auto; background: #131722; padding: 10px; border-radius: 5px; margin-bottom: 8px; font-size: 12px; text-align: left; line-height: 1.5; word-break: break-word; }
            .chat-input-area { display: flex; gap: 6px; flex-direction: column; }
            .input-row { display: flex; gap: 6px; }
            input[type="text"] { flex: 1; padding: 8px; border-radius: 5px; border: 1px solid #2a2e39; background: #131722; color: #fff; font-size: 12px; }
            button { padding: 8px 12px; background: #f2a900; border: none; border-radius: 5px; font-weight: bold; cursor: pointer; color: #000; font-size: 12px; }
            .engine-select { background: #2a2e39; color: #fff; padding: 6px; border-radius: 5px; border: 1px solid #363c4e; font-size: 12px; }
            .tf-buttons { display: flex; gap: 4px; justify-content: center; flex-wrap: wrap; }
            .tf-btn { padding: 4px 8px; background: #2a2e39; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 11px; }
            .tf-btn.active { background: #f2a900; color: #000; font-weight: bold; }
        </style>
    </head>
    <body>
        <h1>XAUUSD MCDX PRIME+ Copilot — IRWAN (irwan0888)</h1>
        
        <div class="container">
            <div class="tf-buttons">
                <button class="tf-btn" onclick="changeTf('1')">1m</button>
                <button class="tf-btn" onclick="changeTf('5')">5m</button>
                <button class="tf-btn" onclick="changeTf('15')">15m</button>
                <button class="tf-btn" onclick="changeTf('60')">1h</button>
                <button class="tf-btn" onclick="changeTf('240')">4h</button>
                <button class="tf-btn active" onclick="changeTf('D')">Daily</button>
            </div>

            <div class="chart-box">
                <div id="tradingview_chart" style="height: 300px; width: 100%;"></div>
            </div>

            <div class="chat-box">
                <div class="chat-messages" id="chatMessages">
                    <div><b>Multi-AI Copilot (IRWAN irwan0888):</b> Salam! Sila pilih enjin AI di bawah dan mula bertanya tentang analisis XAUUSD.</div>
                </div>
                <div class="chat-input-area">
                    <div style="display: flex; gap: 8px; align-items: center;">
                        <span style="font-size: 12px;">Pilih AI:</span>
                        <select id="aiEngine" class="engine-select">
                            <option value="gemini">Gemini AI</option>
                            <option value="chatgpt">ChatGPT (OpenAI)</option>
                        </select>
                    </div>
                    <div class="input-row">
                        <input type="text" id="userInput" placeholder="Tanya analisis XAUUSD..." onkeypress="handleKeyPress(event)">
                        <button onclick="sendMessage()">Hantar</button>
                    </div>
                </div>
            </div>
        </div>

        <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
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
                    "STD;MACD",
                    "STD;Bollinger_Bands"
                ]
            });

            function changeTf(tf) {
                document.querySelectorAll('.tf-btn').forEach(btn => btn.classList.remove('active'));
                event.target.classList.add('active');
                tvWidget.chart().setResolution(tf, function() {});
            }

            function sendMessage() {
                var input = document.getElementById('userInput');
                var engineSelect = document.getElementById('aiEngine');
                var text = input.value.trim();
                var engine = engineSelect.value;
                if (!text) return;

                var messages = document.getElementById('chatMessages');
                messages.innerHTML += '<div style="margin-top:8px;"><b>Anda:</b> ' + text.replace(/</g, "&lt;").replace(/>/g, "&gt;") + '</div>';
                input.value = '';
                messages.scrollTop = messages.scrollHeight;

                fetch('/ask', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt: text, engine: engine })
                })
                .then(response => response.json())
                .then(data => {
                    var engineName = engine === 'chatgpt' ? 'ChatGPT AI' : 'Gemini AI';
                    var formattedReply = data.reply.replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/\\n/g, '<br>');
                    messages.innerHTML += '<div style="margin-top:8px; color:#f2a900;"><b>' + engineName + ':</b><br>' + formattedReply + '</div>';
                    messages.scrollTop = messages.scrollHeight;
                })
                .catch(error => {
                    messages.innerHTML += '<div style="margin-top:8px; color:red;"><b>Ralat:</b> Gagal berhubung dengan pelayan AI.</div>';
                    messages.scrollTop = messages.scrollHeight;
                });
            }

            function handleKeyPress(e) {
                if (e.key === 'Enter') { sendMessage(); }
            }
        </script>
    </body>
    </html>
    """
    return render_template_string(html_content)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
