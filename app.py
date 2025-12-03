# app.py
import os
from flask import Flask, request, jsonify
import requests

TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TOKEN:
    raise Exception("Missing TELEGRAM_TOKEN environment variable")

API_URL = f"https://api.telegram.org/bot{TOKEN}"

app = Flask(__name__)

def send_message(chat_id, text, reply_markup=None):
    url = f"{API_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }

    if reply_markup:
        payload["reply_markup"] = reply_markup

    requests.post(url, json=payload)

@app.route("/")
def home():
    return "Bot Telegram đang chạy trên Render!"

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()
if "callback_query" in update:
    cq = update["callback_query"]
    chat_id = cq["message"]["chat"]["id"]
    data = cq["data"]

    if data == "verify":
        # Telegram yêu cầu phải trả lời callback_query để tránh lỗi
        requests.post(f"{API_URL}/answerCallbackQuery", json={
            "callback_query_id": cq["id"]
        })

        # Gửi tin nhắn xác minh
        send_message(chat_id, "✅ Xác minh thành công!")

    return jsonify(success=True)

    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"]["text"]

if text == "/start":
    reply_markup = {"inline_keyboard": [[{"text": "✅ Xác Minh", "callback_data": "verify"}]]}
    send_message(chat_id, "\U0001F4E2 Vui lòng tham gia các nhóm sau: \n @freekm12h", reply_markup=reply_markup)

        else:
            send_message(chat_id, f"Bạn gửi: {text}")

    return jsonify(success=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
