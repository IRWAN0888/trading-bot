
    
import os
from flask import Flask, jsonify, render_template_string

app = Flask(__name__)

@app.route('/')
def home():
    return "XAUUSD Trading Bot Copilot is Live! Access /capture for chart view."

@app.route('/capture')
def capture():
    try:
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>XAUUSD Live Chart Dashboard</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body { background-color: #131722; color: #d1d4dc; font-family: Arial, sans-serif; text-align: center; margin: 0; padding: 20px; }
                h1 { color: #f2a900; font-size: 20px; }
                .card { background: #1e222d; padding: 15px; border-radius: 8px; margin-top: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
                .tradingview-widget-container { height: 500px; width: 100%; }
            </style>
        </head>
        <body>
            <h1>XAUUSD Autonomous Copilot - Live View</h1>
            <div class="card">
                <div class="tradingview-widget-container">
                    <div class="tradingview-widget-container__widget" style="height:100%;width:100%"></div>
                    <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
                    {
                      "width": "100%",
                      "height": "500",
                      "symbol": "OANDA:XAUUSD",
                      "interval": "D",
                      "timezone": "Etc/UTC",
                      "theme": "dark",
                      "style": "1",
                      "locale": "en",
                      "enable_publishing": false,
                      "allow_symbol_change": true,
                      "calendar": false,
                      "support_host": "https://www.tradingview.com"
                    }
                    </script>
                </div>
            </div>
        </body>
        </html>
        """
        return render_template_string(html_content)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
