import os
import json
import requests
from flask import Flask, request, jsonify

TOKEN = os.environ.get("TELEGRAM_TOKEN")
API_URL = f"https://api.telegram.org/bot{TOKEN}"

ADMIN_ID = 8252036966
GROUPS_FILE = "groups.json"
USERS_FILE = "users.json"
CODES_FILE = "codes.json"

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

def load_codes():
    if not os.path.exists(CODES_FILE):
        return {"codes": []}
    with open(CODES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_codes(data):
    with open(CODES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
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
                    send_message(ref, "🎉 Bạn vừa nhận được <b>+3000 điểm</b> từ 1 lượt giới thiệu hợp lệ")
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
            send_message(chat_id, f"👥 <b>LINK MỜI BẠN BÈ</b>\n{link}")
            return jsonify(success=True)

        elif data == "account":
            p = users["users"][user_id]["points"]
            send_message(chat_id, f"👤 ID: {user_id}\n💰 Điểm: {p}")
            return jsonify(success=True)

        elif data == "withdraw":
            if int(user_id) == ADMIN_ID:
                codes = load_codes()
                send_message(chat_id, f"📦 Số code còn lại: <b>{len(codes['codes'])}</b>")
                return jsonify(success=True)

            if users["users"][user_id]["points"] < 10000:
                send_message(chat_id, "❌ Bạn cần tối thiểu 10000 điểm để rút code")
                return jsonify(success=True)

            codes = load_codes()
            if not codes["codes"]:
                send_message(chat_id, "❌ Hiện đã hết code")
                return jsonify(success=True)

            code = codes["codes"].pop(0)
            users["users"][user_id]["points"] -= 10000
            save_users(users)
            save_codes(codes)

            send_message(chat_id, f"🎁 <b>CODE CỦA BẠN:</b>\n<code>{code}</code>")
            return jsonify(success=True)

        elif data == "stats":
            if int(user_id) != ADMIN_ID:
                send_message(chat_id, "❌ Không có quyền")
                return jsonify(success=True)
            send_message(chat_id, f"📊 Tổng user: {len(users['users'])}")
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

            if text.startswith("/themcode"):
                lines = text.replace("/themcode", "").strip().split("\n")
                codes = load_codes()
                for c in lines:
                    if c.strip():
                        codes["codes"].append(c.strip())
                save_codes(codes)
                send_message(chat_id, "Đã thêm code")
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
                users["users"][str(chat_id)] = {"ref": ref, "points": 0, "verified": False}
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
