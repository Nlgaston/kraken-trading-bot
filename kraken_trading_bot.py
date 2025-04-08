# kraken_trading_bot.py

from flask import Flask, request, jsonify
import krakenex
import logging
import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

# === LOAD ENVIRONMENT VARIABLES ===
load_dotenv()
API_KEY = os.getenv("KRAKEN_API_KEY")
API_SECRET = os.getenv("KRAKEN_API_SECRET")
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_TO = os.getenv("EMAIL_TO")

TRADING_PAIR = 'SOLUSD'
POSITION_SIZE = 2.22  # Equivalent to your fixed multiplier

# === LOGGING SETUP ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# === INIT KRAKEN CLIENT ===
k = krakenex.API()
k.key = API_KEY
k.secret = API_SECRET

# === FLASK APP ===
app = Flask(__name__)

# === EMAIL ALERT FUNCTION ===
def send_email_alert(subject, body):
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = EMAIL_TO

        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)

        logging.info("Email alert sent.")
    except Exception as e:
        logging.error(f"Failed to send email alert: {e}")

# === ORDER FUNCTION ===
def place_order(order_type, size):
    logging.info(f"Placing {order_type} order for {size} {TRADING_PAIR}")
    try:
        response = k.query_private('AddOrder', {
            'pair': TRADING_PAIR,
            'type': 'buy' if order_type in ['LONG_ENTRY', 'LONG_ADD'] else 'sell',
            'ordertype': 'market',
            'volume': str(size),
        })
        logging.info(f"Kraken response: {response}")
        send_email_alert(f"{order_type} Executed", f"{order_type} executed on Kraken for {TRADING_PAIR}\nResponse: {response}")
        return response
    except Exception as e:
        logging.error(f"Order error: {str(e)}")
        send_email_alert(f"{order_type} Failed", f"Failed to execute {order_type} on Kraken: {e}")
        return None

# === ROUTE FOR WEBHOOK ===
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    signal = data.get('alert_message', '')
    logging.info(f"Received signal: {signal}")

    if signal in ['LONG_ENTRY', 'LONG_ADD', 'SHORT_ENTRY', 'SHORT_ADD']:
        result = place_order(signal, POSITION_SIZE)
        return jsonify({'status': 'success', 'response': result})
    else:
        return jsonify({'status': 'ignored', 'message': 'Unknown signal'})

# === RUN FLASK APP ===
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5001))
    app.run(host='0.0.0.0', port=port)
