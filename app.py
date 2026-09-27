import os
from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)

@app.route('/')
def home():
    return "XAUUSD MCDX PRIME+ AI Copilot by IRWAN (irwan0888) is Live!"

@app.route('/capture')
def capture():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>XAUUSD MCDX PRIME+ AI Copilot - IRWAN (irwan0888)</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { background-color: #131722; color: #d1d4dc; font-family: Arial, sans-serif; margin: 0; padding: 10px; }
            h1 { color: #f2a900; font-size: 15px; text-align: center; }
            .container { display: flex; flex-direction: column; gap: 12px; }
            .chart-box { background: #1e222d; padding: 8px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
            .chat-box { background: #1e222d; padding: 12px; border-radius: 8px; height: 280px; display: flex; flex-direction: column; }
            .chat-messages { flex: 1; overflow-y: auto; background: #131722; padding: 10px; border-radius: 5px; margin-bottom: 8px; font-size: 13px; text-align: left; line-height: 1.4; }
            .chat-input-area { display: flex; gap: 8px; }
            input[type="text"] { flex: 1; padding: 8px; border-radius: 5px; border: 1px solid #2a2e39; background: #131722; color: #fff; font-size: 13px; }
            button { padding: 8px 12px; background: #f2a900; border: none; border-radius: 5px; font-weight: bold; cursor: pointer; color: #000; font-size: 13px; }
            .tf-buttons { display: flex; gap: 4px; justify-content: center; flex-wrap: wrap; }
            .tf-btn { padding: 4px 8px; background: #2a2e39; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 11px; }
            .tf-btn.active { background: #f2a900; color: #000; font-weight: bold; }
        </style>
    </head>
    <body>
        <h1>XAUUSD MCDX PRIME+ Copilot — Hak Milik: IRWAN (irwan0888)</h1>
        
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
                <div id="tradingview_chart" style="height: 360px; width: 100%;"></div>
            </div>

            <div class="chat-box">
                <div class="chat-messages" id="chatMessages">
                    <div><b>Gemini Copilot (IRWAN irwan0888):</b> Salam, Trader! Sedia melaksanakan analisis terperinci mengikut SOP MCDX PRIME+ (G1-G3 & DC1-DC3). Silakan beri arahan atau persoalan anda.</div>
                </div>
                <div class="chat-input-area">
                    <input type="text" id="userInput" placeholder="Taip arahan analisis (cth: Buat analisis XAUUSD sekarang)..." onkeypress="handleKeyPress(event)">
                    <button onclick="sendMessage()">Hantar</button>
                </div>
            </div>
        </div>

        <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
        <script type="text/javascript">
            var tvWidget = new TradingView.widget({
                "width": "100%",
                "height": "360",
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
                var reply = "";

                if (query.includes("analisis") || query.includes("buat") || query.includes("kemana")) {
                    reply = "<b>Hasil Analisis Semasa XAUUSD (MCDX PRIME+):</b><br>" +
                            "1. <b>Struktur Timeframe Besar (Daily / 4H):</b> Harga menunjukkan fasa konsolidasi berhampiran zon sokongan utama. Perhatikan bar Banker dan Hot Money.<br>" +
                            "2. <b>SOP Tertib:</b> Jika berlaku silangan G2 atau G3 (Banker menolak harga naik), ia mengesahkan peluang <b>BUY</b>.<br>" +
                            "3. <b>Amaran Risiko:</b> Sentiasa semak silangan Dead Cross (DC2/DC3) pada timeframe lebih kecil (M15/M5) sebelum masuk posisi.";
                } else if (query.includes("g2") || query.includes("g3") || query.includes("buy")) {
                    reply = "<b>SOP BUY Terperinci:</b> G2 dan G3 terbentuk apabila garisan Banker bersilang di atas garisan Retailer/Hot Money dengan dominasi bar hijau/merah yang kuat. Pastikan tiada halangan rintangan terdekat.";
                } else if (query.includes("dc") || query.includes("sell")) {
                    reply = "<b>SOP SELL Terperinci:</b> Kemunculan DC1, DC2, atau DC3 menandakan Retailer mula mendominasi penurunan harga. Keluar dari posisi Buy dan bersedia untuk kemasukan Sell yang tertib.";
                } else {
                    reply = "Analisis diterima untuk sistem <b>irwan0888</b>. Sila pastikan carta pada timeframe pilihan anda mematuhi peraturan silangan G1-G3 atau DC1-DC3 sebelum melakukan eksekusi dagangan.";
                }

                setTimeout(function() {
                    messages.innerHTML += '<div style="margin-top:6px; color:#f2a900;"><b>Gemini Copilot (IRWAN irwan0888):</b> ' + reply + '</div>';
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
