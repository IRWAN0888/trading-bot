
import os
from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)

@app.route('/')
def home():
    return "XAUUSD Autonomous AI Copilot is Live!"

@app.route('/capture')
def capture():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>XAUUSD Multi-Timeframe AI Copilot</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { background-color: #131722; color: #d1d4dc; font-family: Arial, sans-serif; margin: 0; padding: 10px; }
            h1 { color: #f2a900; font-size: 18px; text-align: center; }
            .container { display: flex; flex-direction: column; gap: 15px; }
            .chart-box { background: #1e222d; padding: 10px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
            .chat-box { background: #1e222d; padding: 15px; border-radius: 8px; height: 300px; display: flex; flex-direction: column; }
            .chat-messages { flex: 1; overflow-y: auto; background: #131722; padding: 10px; border-radius: 5px; margin-bottom: 10px; font-size: 14px; text-align: left; }
            .chat-input-area { display: flex; gap: 10px; }
            input[type="text"] { flex: 1; padding: 10px; border-radius: 5px; border: 1px solid #2a2e39; background: #131722; color: #fff; }
            button { padding: 10px 15px; background: #f2a900; border: none; border-radius: 5px; font-weight: bold; cursor: pointer; color: #000; }
            .tf-buttons { display: flex; gap: 5px; justify-content: center; margin-bottom: 10px; }
            .tf-btn { padding: 5px 10px; background: #2a2e39; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 12px; }
            .tf-btn.active { background: #f2a900; color: #000; font-weight: bold; }
        </style>
    </head>
    <body>
        <h1>XAUUSD AI Copilot (Multi-Timeframe & Analysis)</h1>
        
        <div class="container">
            <div class="tf-buttons">
                <button class="tf-btn active" onclick="changeTf('1')">1m</button>
                <button class="tf-btn" onclick="changeTf('15')">15m</button>
                <button class="tf-btn" onclick="changeTf('60')">1h</button>
                <button class="tf-btn" onclick="changeTf('240')">4h</button>
                <button class="tf-btn" onclick="changeTf('D')">Daily</button>
            </div>

            <div class="chart-box">
                <div id="tradingview_chart" style="height: 400px; width: 100%;"></div>
            </div>

            <div class="chat-box">
                <div class="chat-messages" id="chatMessages">
                    <div><b>Gemini Copilot:</b> Salam, Trader! Saya AI Copilot anda untuk XAUUSD. Sila tanya apa sahaja analisis multi-timeframe atau struktur pasaran (Smart Money Concepts / Supply Demand).</div>
                </div>
                <div class="chat-input-area">
                    <input type="text" id="userInput" placeholder="Tanya analisis XAUUSD (cth: Analisis trend H4 & M15)..." onkeypress="handleKeyPress(event)">
                    <button onclick="sendMessage()">Hantar</button>
                </div>
            </div>
        </div>

        <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
        <script type="text/javascript">
            var tvWidget = new TradingView.widget({
                "width": "100%",
                "height": "400",
                "symbol": "OANDA:XAUUSD",
                "interval": "D",
                "timezone": "Etc/UTC",
                "theme": "dark",
                "style": "1",
                "locale": "en",
                "toolbar_bg": "#f1f3f6",
                "enable_publishing": false,
                "allow_symbol_change": true,
                "container_id": "tradingview_chart"
            });

            function changeTf(tf) {
                document.querySelectorAll('.tf-btn').forEach(btn => btn.classList.remove('active'));
                event.target.classList.add('active');
                tvWidget.chart().setResolution(tf, function() {});
            }

            function sendMessage() {
                var input = document.getElementById('userInput');
                var text = input.value.trim();
                if (!text) return;

                var messages = document.getElementById('chatMessages');
                messages.innerHTML += '<div style="margin-top:8px;"><b>Anda:</b> ' + text + '</div>';
                
                var query = text.toLowerCase();
                var reply = "Menganalisis XAUUSD merentas pelbagai timeframe... Struktur pasaran menunjukkan zon Supply/Demand kukuh pada H1 dan D1. Sila rujuk perubahan harga pada carta di atas untuk pengesahan Price Action.";
                if(query.includes("h4") || query.includes("timeframe")) {
                    reply = "Analisis Multi-Timeframe XAUUSD: Daily cenderung kepada struktur Bullish, H4 membentuk zon Pullback/Order Block berhampiran sokongan utama, manakala M15/M1 menunjukkan momentum breakout penentuan arah semasa.";
                }

                setTimeout(function() {
                    messages.innerHTML += '<div style="margin-top:8px; color:#f2a900;"><b>Gemini Copilot:</b> ' + reply + '</div>';
                    messages.scrollTop = messages.scrollHeight;
                }, 500);

                input.value = '';
                messages.scrollTop = messages.scrollHeight;
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
