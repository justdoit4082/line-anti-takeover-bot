import os  
from flask import Blueprint, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, MemberLeftEvent
from datetime import datetime
from linebot import LineBotApi


webhook_bp = Blueprint('webhook', __name__, url_prefix="/callback", strict_slashes=False)


line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))
ADMIN_USER_IDS = ["U27bdcfedc1a0d11770345793882688c6"]

LOG_DIR = "./logs"
os.makedirs(LOG_DIR, exist_ok=True)
ADMIN_USER_IDS = ["U27bdcfedc1a0d11770345793882688c6"]  # 你是管理員

@handler.add(MemberLeftEvent)
def handle_member_left(event):
    left_user_id = event.left.user_id  # 被踢出的人
    kicker_user_id = get_kicker_id(event.source.group_id)  # 這是你自訂函數，需自己記錄最後發出踢人訊息者

    # 發送通知
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=f"⚠️ 有成員從群組離開或被踢出：\n{left_user_id}\n由：\n{kicker_user_id}")
    )

    # 如果踢人者不是管理員，將其移出群組
    if kicker_user_id not in ADMIN_USER_IDS:
        try:
            line_bot_api.kickout(event.source.group_id, kicker_user_id)
            print(f"已將未授權踢人者 {kicker_user_id} 移出群組")
        except Exception as e:
            print(f"踢出失敗：{e}")

@webhook_bp.route("/", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    try:
        user_id = event.source.user_id
        group_id = getattr(event.source, 'group_id', None)
        text = event.message.text.strip()

        if group_id is None:
            return

        if text == "/myid":
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"你的ID是：{user_id}"))
        elif text == "/warn" and user_id in ADMIN_USER_IDS:
            log_path = f"{LOG_DIR}/{group_id}_warn.log"
            with open(log_path, "a", encoding="utf-8") as log:
                log.write(f"⚠️ 管理員警告：{datetime.now().isoformat()} - 由 {user_id} 發出\n")
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 已記錄警告。"))
        elif text == "/banlist":
            path = f"{LOG_DIR}/{group_id}_banlist.txt"
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
            else:
                content = "(尚無封鎖名單)"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=content))
        elif text.startswith("/"):
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"你說的是：{text}"))
    except Exception as e:
        print(f"處理訊息時出錯：{e}")

@handler.add(MemberLeftEvent)
def handle_member_left(event):
    try:
        left_user_id = event.left.members[0].user_id if hasattr(event.left, 'members') and event.left.members else "未知"
        group_id = getattr(event.source, 'group_id', None)
        if group_id:
            log_path = f"{LOG_DIR}/{group_id}_warn.log"
            with open(log_path, "a", encoding="utf-8") as log:
                log.write(f"🚨 成員離開偵測：{datetime.now().isoformat()} - {left_user_id}\n")

            for admin_id in ADMIN_USER_IDS:
                try:
                    line_bot_api.push_message(admin_id, TextSendMessage(
                        text=f"⚠️ 有成員從群組 {group_id} 離開或被踢出：\n{left_user_id}"
                    ))
                except Exception as e:
                    print(f"通知失敗: {e}")
    except Exception as e:
        print(f"處理成員離開事件時出錯：{e}")
