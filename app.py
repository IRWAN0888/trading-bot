import os
from flask import Flask, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

app = Flask(__name__)

@app.route('/capture', methods=['GET'])
def capture_chart():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        driver.get("https://www.tradingview.com/")
        driver.save_screenshot("current_chart.png")
        return jsonify({"status": "success", "message": "Tangkapan skrin carta berjaya diambil!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    finally:
        driver.quit()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
