# app.py
import os
from flask import Flask, request, jsonify
import requests

TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TOKEN:
    raise Exception("Missing TELEGRAM_TOKEN environment variable")

API_URL = f"https://api.telegram.org/bot{TOKEN}"

app = Flask(__name__)

def send_message(chat_id, text):
    url = f"{API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, json=payload)

@app.route("/")
def home():
    return "Bot Telegram đang chạy trên Render!"

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()

    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"]["text"]

        if text == "/start":
            send_message(chat_id, "Xin chào! bot bịp rõ \U0001F4E2 :0")
        else:
            send_message(chat_id, f"Bạn gửi: {text}")

    return jsonify(success=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
