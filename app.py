import os
import json
import requests
from flask import Flask, request, jsonify

TOKEN = os.environ.get("TELEGRAM_TOKEN")
API_URL = f"https://api.telegram.org/bot{TOKEN}"

ADMIN_ID = 8252036966

USER_STORAGE_ID = -1003326550194
GROUP_STORAGE_ID = -1003630051728
CODE_STORAGE_ID = -1003505984119

USERS_FILE = "users.json"
GROUPS_FILE = "groups.json"
CODES_FILE = "codes.json"

app = Flask(__name__)

def load_file(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def save_file(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(f"{API_URL}/sendMessage", json=payload)

def log_to_channel(channel_id, text):
    requests.post(
        f"{API_URL}/sendMessage",
        json={"chat_id": channel_id, "text": text}
    )

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

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()

    users = load_file(USERS_FILE, {"users": {}})
    groups = load_file(GROUPS_FILE, {"groups": []})
    codes = load_file(CODES_FILE, {"codes": []})

    if "callback_query" in update:
        cq = update["callback_query"]
        data = cq["data"]
        chat_id = cq["message"]["chat"]["id"]
        user_id = str(cq["from"]["id"])

        requests.post(
            f"{API_URL}/answerCallbackQuery",
            json={"callback_query_id": cq["id"]}
        )

        if user_id not in users["users"]:
            return jsonify(success=True)

        if data == "verify":
            not_joined = []

            for g in groups["groups"]:
                r = requests.get(
                    f"{API_URL}/getChatMember",
                    params={"chat_id": g, "user_id": user_id}
                ).json()
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
                    send_message(
                        ref,
                        "🎉 Bạn vừa nhận được <b>+3000 điểm</b> từ 1 lượt giới thiệu hợp lệ"
                    )

                save_file(USERS_FILE, users)

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

        if data == "invite":
            bot = requests.get(f"{API_URL}/getMe").json()["result"]["username"]
            link = f"https://t.me/{bot}?start={user_id}"
            send_message(chat_id, f"👥 <b>LINK MỜI BẠN BÈ</b>\n{link}")
            return jsonify(success=True)

        if data == "account":
            u = users["users"][user_id]
            send_message(
                chat_id,
                f"👤 ID: {user_id}\n💰 Điểm: {u['points']}\n👥 Ref: {u['ref']}"
            )
            return jsonify(success=True)

        if data == "withdraw":
            if int(user_id) == ADMIN_ID:
                send_message(chat_id, f"📦 Số code còn lại: <b>{len(codes['codes'])}</b>")
                return jsonify(success=True)

            if users["users"][user_id]["points"] < 10000:
                send_message(chat_id, "❌ Bạn cần tối thiểu 10000 điểm để rút code")
                return jsonify(success=True)

            if not codes["codes"]:
                send_message(chat_id, "❌ Hiện đã hết code")
                return jsonify(success=True)

            code = codes["codes"].pop(0)
            users["users"][user_id]["points"] -= 10000

            save_file(USERS_FILE, users)
            save_file(CODES_FILE, codes)

            log_to_channel(CODE_STORAGE_ID, f"USED CODE: {code}")

            send_message(chat_id, f"🎁 <b>CODE CỦA BẠN:</b>\n<code>{code}</code>")
            return jsonify(success=True)

        if data == "stats":
            if int(user_id) != ADMIN_ID:
                send_message(chat_id, "❌ Không có quyền")
                return jsonify(success=True)

            send_message(
                chat_id,
                f"📊 Tổng user: {len(users['users'])}\n📦 Code còn: {len(codes['codes'])}"
            )
            return jsonify(success=True)

    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"].get("text", "")

        if chat_id == ADMIN_ID:
            if text.startswith("/addgroup"):
                g = text.split(" ", 1)[1]
                if g not in groups["groups"]:
                    groups["groups"].append(g)
                    save_file(GROUPS_FILE, groups)
                    log_to_channel(GROUP_STORAGE_ID, f"ADD GROUP: {g}")
                send_message(chat_id, "Đã thêm nhóm")
                return jsonify(success=True)

            if text.startswith("/themcode"):
                lines = text.replace("/themcode", "").strip().split("\n")
                for c in lines:
                    if c.strip():
                        codes["codes"].append(c.strip())
                        log_to_channel(CODE_STORAGE_ID, f"ADD CODE: {c.strip()}")
                save_file(CODES_FILE, codes)
                send_message(chat_id, "Đã thêm code")
                return jsonify(success=True)

        if text.startswith("/start"):
            parts = text.split(" ")
            ref = None
            if len(parts) > 1:
                try:
                    ref = int(parts[1])
                except:
                    ref = None

            if ref == chat_id:
                ref = None

            if str(chat_id) not in users["users"]:
                users["users"][str(chat_id)] = {
                    "ref": ref,
                    "points": 0,
                    "verified": False
                }
                save_file(USERS_FILE, users)
                log_to_channel(
                    USER_STORAGE_ID,
                    json.dumps(
                        {"uid": chat_id, "ref": ref, "points": 0, "verified": False},
                        ensure_ascii=False
                    )
                )

            send_message(
                chat_id,
                "📢 Tham gia các nhóm sau:\n" + "\n".join(groups["groups"]),
                reply_markup={
                    "inline_keyboard": [
                        [{"text": "✅ Xác Minh", "callback_data": "verify"}]
                    ]
                }
            )
            return jsonify(success=True)

    return jsonify(success=True)

if __name__ == "__main__":
    set_commands()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
