# app.py
import os
from flask import Flask, request, jsonify
import requests

TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TOKEN:
    raise Exception("Missing TELEGRAM_TOKEN environment variable")

API_URL = f"https://api.telegram.org/bot{TOKEN}"
import json

ADMIN_ID = 8252036966
GROUPS_FILE = "groups.json"

def load_groups():
    if not os.path.exists(GROUPS_FILE):
        return {"groups": []}
    with open(GROUPS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return {"groups": []}

def save_groups(data):
    with open(GROUPS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


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
            requests.post(f"{API_URL}/answerCallbackQuery", json={"callback_query_id": cq["id"]})
            send_message(chat_id, "✅ Xác minh thành công!")
        return jsonify(success=True)

    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"]["text"]
        if chat_id == ADMIN_ID:
            if text.startswith("/addgroup"):
                try:
                    group = text.split(" ", 1)[1].strip()
                    data = load_groups()
                    if group not in data["groups"]:
                        data["groups"].append(group)
                        save_groups(data)
                        send_message(chat_id, f"Đã thêm nhóm: {group}")
                    else:
                        send_message(chat_id, "Nhóm này đã có trong danh sách.")
                except:
                    send_message(chat_id, "Sai cú pháp. Dùng: /addgroup @tennhom")
                return jsonify(success=True)

            if text.startswith("/delgroup"):
                try:
                    group = text.split(" ", 1)[1].strip()
                    data = load_groups()
                    if group in data["groups"]:
                        data["groups"].remove(group)
                        save_groups(data)
                        send_message(chat_id, f"Đã xóa nhóm: {group}")
                    else:
                        send_message(chat_id, "Nhóm này không tồn tại trong danh sách.")
                except:
                    send_message(chat_id, "Sai cú pháp. Dùng: /delgroup @tennhom")
                return jsonify(success=True)

            if text == "/listgroups":
                data = load_groups()
                if not data["groups"]:
                    send_message(chat_id, "Danh sách nhóm đang trống.")
                else:
                    groups_msg = "\n".join(data["groups"])
                    send_message(chat_id, f"Danh sách nhóm:\n{groups_msg}")
                return jsonify(success=True)

       
        if text == "/start":
            reply_markup = {"inline_keyboard": [[{"text": "✅ Xác Minh", "callback_data": "verify"}]]}
            send_message(chat_id, "\U0001F4E2 Vui lòng tham gia các nhóm sau: \n @freekm12h", reply_markup=reply_markup)

        else:
            send_message(chat_id, f"Bạn gửi: {text}")

    return jsonify(success=True)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
