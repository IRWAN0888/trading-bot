import os
from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)

@app.route('/')
def home():
    return "XAUUSD MCDX PRIME+ AI Copilot is Live!"

@app.route('/capture')
def capture():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>XAUUSD MCDX PRIME+ AI Copilot</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { background-color: #131722; color: #d1d4dc; font-family: Arial, sans-serif; margin: 0; padding: 10px; }
            h1 { color: #f2a900; font-size: 16px; text-align: center; }
            .container { display: flex; flex-direction: column; gap: 12px; }
            .chart-box { background: #1e222d; padding: 8px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
            .chat-box { background: #1e222d; padding: 12px; border-radius: 8px; height: 260px; display: flex; flex-direction: column; }
            .chat-messages { flex: 1; overflow-y: auto; background: #131722; padding: 10px; border-radius: 5px; margin-bottom: 8px; font-size: 13px; text-align: left; }
            .chat-input-area { display: flex; gap: 8px; }
            input[type="text"] { flex: 1; padding: 8px; border-radius: 5px; border: 1px solid #2a2e39; background: #131722; color: #fff; font-size: 13px; }
            button { padding: 8px 12px; background: #f2a900; border: none; border-radius: 5px; font-weight: bold; cursor: pointer; color: #000; font-size: 13px; }
            .tf-buttons { display: flex; gap: 4px; justify-content: center; flex-wrap: wrap; }
            .tf-btn { padding: 4px 8px; background: #2a2e39; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 11px; }
            .tf-btn.active { background: #f2a900; color: #000; font-weight: bold; }
        </style>
    </head>
    <body>
        <h1>XAUUSD MCDX PRIME+ Multi-Timeframe Copilot</h1>
        
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
                <div id="tradingview_chart" style="height: 380px; width: 100%;"></div>
            </div>

            <div class="chat-box">
                <div class="chat-messages" id="chatMessages">
                    <div><b>Gemini Copilot:</b> Salam, Trader! Sedia membantu analisis SOP MCDX PRIME+ (G1/G2/G3 & DC1/DC2/DC3) merentas semua timeframe untuk XAUUSD.</div>
                </div>
                <div class="chat-input-area">
                    <input type="text" id="userInput" placeholder="Tanya analisis (cth: Status G2 H4 & M15)..." onkeypress="handleKeyPress(event)">
                    <button onclick="sendMessage()">Hantar</button>
                </div>
            </div>
        </div>

        <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
        <script type="text/javascript">
            var tvWidget = new TradingView.widget({
                "width": "100%",
                "height": "380",
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
                messages.innerHTML += '<div style="margin-top:6px;"><b>Anda:</b> ' + text + '</div>';
                
                var query = text.toLowerCase();
                var reply = "Analisis MCDX PRIME+: Sila semak silangan Banker, Hot Money, dan Retailer pada carta mengikut SOP tertib G1, G2, G3 untuk Buy atau DC1, DC2, DC3 untuk Sell.";
                if(query.includes("g2") || query.includes("buy")) {
                    reply = "SOP Buy (G2/G3): Pastikan Banker menolak harga naik dengan dominasi kukuh melepasi garisan rujukan untuk mengesahkan penyertaan posisi Buy yang berkualiti.";
                } else if(query.includes("dc2") || query.includes("sell")) {
                    reply = "SOP Sell (DC2/DC3): Perhatikan persilangan Dead Cross dan penolakan Retailer/Hot Money yang menunjukkan momentum penurunan harga aktif.";
                }

                setTimeout(function() {
                    messages.innerHTML += '<div style="margin-top:6px; color:#f2a900;"><b>Gemini Copilot:</b> ' + reply + '</div>';
                    messages.scrollTop = messages.scrollHeight;
                }, 400);

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
