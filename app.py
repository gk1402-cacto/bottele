import os
import json
import requests
from flask import Flask, request, jsonify

TOKEN = os.environ.get("TELEGRAM_TOKEN")
API_URL = f"https://api.telegram.org/bot{TOKEN}"

ADMIN_ID = 8252036966
GROUPS_FILE = "groups.json"
USERS_FILE = "users.json"

app = Flask(__name__)

def load_groups():
    if not os.path.exists(GROUPS_FILE):
        return {"groups": []}
    with open(GROUPS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_groups(data):
    with open(GROUPS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def load_users():
    if not os.path.exists(USERS_FILE):
        return {"users": {}}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_users(data):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def send_message(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(f"{API_URL}/sendMessage", json=payload)

def set_commands():
    requests.post(
        f"{API_URL}/setMyCommands",
        json={
            "commands": [
                {"command": "invite", "description": "Mời bạn bè"},
                {"command": "account", "description": "Thông tin tài khoản"},
                {"command": "withdraw", "description": "Rút code"},
                {"command": "stats", "description": "Thống kê"}
            ]
        }
    )

@app.route("/")
def home():
    return "Bot running"

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()

    if "callback_query" in update:
        cq = update["callback_query"]
        data = cq["data"]
        chat_id = cq["message"]["chat"]["id"]
        user_id = str(cq["from"]["id"])

        requests.post(f"{API_URL}/answerCallbackQuery", json={"callback_query_id": cq["id"]})

        users = load_users()
        if "users" not in users:
            users["users"] = {}

        if data == "verify":
            groups = load_groups()["groups"]
            not_joined = []
            for g in groups:
                r = requests.get(f"{API_URL}/getChatMember", params={"chat_id": g, "user_id": user_id}).json()
                try:
                    if r["result"]["status"] not in ["member", "administrator", "creator"]:
                        not_joined.append(g)
                except:
                    not_joined.append(g)

            if not_joined:
                send_message(chat_id, "❌ Bạn chưa tham gia đủ nhóm:\n" + "\n".join(not_joined))
                return jsonify(success=True)

            if not users["users"][user_id]["verified"]:
                users["users"][user_id]["verified"] = True
                ref = users["users"][user_id]["ref"]
                if ref and str(ref) in users["users"]:
                    users["users"][str(ref)]["points"] += 3000
                save_users(users)

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

            send_message(chat_id, "🎉 Xác minh thành công", reply_markup=menu)
            return jsonify(success=True)

        elif data == "invite":
            bot = requests.get(f"{API_URL}/getMe").json()
            link = f"https://t.me/{bot['result']['username']}?start={user_id}"
            send_message(
                chat_id,
                f"👥 <b>LINK MỜI BẠN BÈ</b>\n{link}\n\n"
                "📌 Mỗi lượt xác minh +3000 điểm\n"
                "💰 Rút tối thiểu 10000 điểm"
            )
            return jsonify(success=True)

        elif data == "account":
            p = users["users"][user_id]["points"]
            send_message(chat_id, f"👤 ID: {user_id}\n💰 Điểm: {p}")
            return jsonify(success=True)

        elif data == "withdraw":
            send_message(chat_id, "💳 Chức năng rút code sẽ mở sớm")
            return jsonify(success=True)

        elif data == "stats":
            if int(user_id) != ADMIN_ID:
                send_message(chat_id, "❌ Bạn không có quyền")
                return jsonify(success=True)
            total = len(users["users"])
            send_message(chat_id, f"📊 Tổng user: {total}")
            return jsonify(success=True)

    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"].get("text", "")

        if chat_id == ADMIN_ID:
            if text.startswith("/addgroup"):
                g = text.split(" ", 1)[1]
                data = load_groups()
                if g not in data["groups"]:
                    data["groups"].append(g)
                    save_groups(data)
                send_message(chat_id, "Đã thêm nhóm")
                return jsonify(success=True)

            if text.startswith("/delgroup"):
                g = text.split(" ", 1)[1]
                data = load_groups()
                if g in data["groups"]:
                    data["groups"].remove(g)
                    save_groups(data)
                send_message(chat_id, "Đã xóa nhóm")
                return jsonify(success=True)

            if text == "/listgroups":
                data = load_groups()
                send_message(chat_id, "\n".join(data["groups"]))
                return jsonify(success=True)

        if text.startswith("/start"):
            parts = text.split(" ")
            ref = None
            if len(parts) > 1:
                try:
                    ref = int(parts[1])
                except:
                    pass

            users = load_users()
            if "users" not in users:
                users["users"] = {}

            if str(chat_id) not in users["users"]:
                if ref == chat_id:
                    ref = None
                users["users"][str(chat_id)] = {
                    "ref": ref,
                    "points": 0,
                    "verified": False
                }
                save_users(users)

            groups = load_groups()["groups"]
            send_message(
                chat_id,
                "📢 Tham gia các nhóm sau:\n" + "\n".join(groups),
                reply_markup={"inline_keyboard": [[{"text": "✅ Xác Minh", "callback_data": "verify"}]]}
            )
            return jsonify(success=True)

    return jsonify(success=True)

if __name__ == "__main__":
    set_commands()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
