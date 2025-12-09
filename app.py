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
        
USERS_FILE = "users.json"

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return {}
def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=4, ensure_ascii=False)

# Tạo menu lệnh hiển thị khi nhấn nút 4 ô vuông
def set_commands():
    url = f"{API_URL}/setMyCommands"
    commands = {
        "commands": [
            {"command": "invite", "description": "Mời bạn bè"},
            {"command": "account", "description": "Thông tin tài khoản"},
            {"command": "withdraw", "description": "Rút code"},
            {"command": "stats", "description": "Thống kê (admin)"}
        ]
    }
    try:
        requests.post(url, json=commands)
    except Exception as e:
        print("set_commands error:", e)

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
            chat_id = cq["message"]["chat"]["id"]      # dùng để gửi tin nhắn
            user_id = cq["from"]["id"]                 # dùng để kiểm tra join nhóm
            groups = load_groups()["groups"]
            not_joined = []
            for g in groups:
                check = requests.get(f"{API_URL}/getChatMember", params={"chat_id": g,"user_id": user_id}).json()
                try:
                    status = check["result"]["status"]
                    if status not in ["member", "administrator", "creator"]:
                        not_joined.append(g)
                except:
                    not_joined.append(g)

            if not_joined:
                missing = "\n".join(not_joined)
                send_message(chat_id, f"❌ Bạn chưa tham gia đủ nhóm:\n{missing}")
                return jsonify(success=True)
            menu = {
                "inline_keyboard": [
                    [
                        {"text": "👤 Thông tin tài khoản", "callback_data": "account"},
                        {"text": "👥 Mời bạn bè", "callback_data": "invite"}
                    ],
                    [
                        {"text": "💳 Rút code", "callback_data": "withdraw"},
                        {"text": "📊 Thống kê", "callback_data": "stats"}
                    ]
                ]
            }

            send_message(
                chat_id,
                "🎉 Bạn đã xác minh thành công!\n\n🔽 Chọn một chức năng bên dưới:",
                reply_markup=menu
            )

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
            if text == "/checkbot":
                data = load_groups()
                groups = data["groups"]
                if not groups:
                    send_message(chat_id, "❗ Danh sách nhóm trống, không có nhóm nào để kiểm tra.")
                    return jsonify(success=True)
                result = "📌 Kết quả kiểm tra bot trong các nhóm:\n\n"
                bot_id = TOKEN.split(':')[0]
                for g in groups:
                    check = requests.get(f"{API_URL}/getChatMember", params={
                        "chat_id": g,
                        "user_id": bot_id
                    }).json()
                    try:
                        status = check["result"]["status"]
                        if status in ["administrator", "creator"]:
                            result += f"✅ Bot là admin của: {g}\n"
                        else:
                            result += f"❌ Bot KHÔNG phải admin của: {g}\n"
                    except:
                        result += f"⚠️ Không thể kiểm tra nhóm: {g}\n"
                send_message(chat_id, result)
                return jsonify(success=True)
                
        if text.startswith("/start"):
            parts = text.split(" ")
            referrer = None
            if len(parts) > 1:
                try:
                    referrer = int(parts[1])
                except:
                    referrer = None
            users = load_users()
            user_id = str(chat_id)
            if user_id not in users["users"]:
                if referrer is not None and str(referrer) == user_id:
                    referrer = None
                users["users"][user_id] = {
                    "ref": referrer,
                    "points": 0,
                    "verified": False
                }
                save_users(users)
            groups = load_groups()["groups"]
            if not groups:
                send_message(chat_id, "⚠️ Hiện chưa có nhóm nào để tham gia.")
                return jsonify(success=True)

            group_list = "\n".join(groups)
            reply_markup = {
                "inline_keyboard": [[{"text": "✅ Xác Minh", "callback_data": "verify"}]]
            }

            send_message(
                chat_id,f"📢 Vui lòng tham gia các nhóm sau:\n{group_list}",
                reply_markup=reply_markup
            )

            return jsonify(success=True)

        else:
            send_message(chat_id, f"Bạn gửi: {text}")

    return jsonify(success=True)
if __name__ == "__main__":
    set_commands()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
