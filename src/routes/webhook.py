import os
import json
from flask import Blueprint, request, abort, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, JoinEvent, FollowEvent,
    MemberJoinedEvent, MemberLeftEvent, UnfollowEvent, LeaveEvent
)
from src.utils.check_admin import is_user_group_admin
from src.utils.create_log import create_event_log
from src.utils.reply_message import reply_text_message

webhook_bp = Blueprint('webhook', __name__)

channel_secret = os.getenv('LINE_CHANNEL_SECRET')
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')

if not channel_secret or not channel_access_token:
    print("缺少 LINE_CHANNEL_SECRET 或 LINE_CHANNEL_ACCESS_TOKEN")
    handler = None
    line_bot_api = None
else:
    handler = WebhookHandler(channel_secret)
    line_bot_api = LineBotApi(channel_access_token)

@webhook_bp.route("/webhook", methods=['POST'])
def webhook():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)

    try:
        if not handler:
            return jsonify({'error': 'Bot not configured properly.'}), 500
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK', 200

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    import os

    user_id = event.source.user_id
    group_id = getattr(event.source, 'group_id', None)
    user_message = event.message.text.strip()

    print(f"[DEBUG] user_id: {user_id}, group_id: {group_id}, message: {user_message}")

    group_admins = ['請填入你的 userId，例如 U123xxx']

    if not group_id:
        reply_text_message(line_bot_api, event.reply_token, "請在群組中使用此機器人功能。")
        return

    if user_message.lower() == "/help":
        help_text = (
            "🤖 機器人功能指令清單：\n"
            "🛡 /warn [@使用者]：發出警告\n"
            "👑 /admin：查詢群組管理員\n"
            "📋 /log：檢查警告紀錄\n"
            "🚫 /banlist：查看封鎖名單\n"
            "📖 /help：顯示此說明列表"
        )
        reply_text_message(line_bot_api, event.reply_token, help_text)
        return

    if user_message.lower() == "/admin":
        reply_text_message(line_bot_api, event.reply_token, f"👑 管理員 ID：\n" + "\n".join(group_admins))
        return

    if user_message.lower().startswith("/warn"):
        if is_user_group_admin(user_id, group_admins):
            create_event_log("warn", user_id, group_id, user_message)
            reply_text_message(line_bot_api, event.reply_token, "⚠️ 已記錄警告。")
        else:
            reply_text_message(line_bot_api, event.reply_token, "❌ 你不是管理員，不能使用 /warn 指令。")
        return

    if user_message.lower() == "/log":
        log_file = f"logs/{group_id}_warn.log"
        if os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()[-5:]
            log_text = "📋 最新警告紀錄：\n" + "".join(lines)
        else:
            log_text = "📋 尚無任何警告紀錄。"
        reply_text_message(line_bot_api, event.reply_token, log_text)
        return

    if user_message.lower() == "/banlist":
        banlist_file = "banlist.txt"
        if os.path.exists(banlist_file):
            with open(banlist_file, "r", encoding="utf-8") as f:
                users = f.read().strip()
            ban_text = "🚫 封鎖名單如下：\n" + users if users else "🚫 封鎖名單為空。"
        else:
            ban_text = "🚫 尚未建立封鎖名單。"
        reply_text_message(line_bot_api, event.reply_token, ban_text)
        return

    reply_text = f"你說的是：{user_message}"
    reply_text_message(line_bot_api, event.reply_token, reply_text)

@handler.add(JoinEvent)
@handler.add(FollowEvent)
@handler.add(MemberJoinedEvent)
def handle_join(event):
    user_id = event.source.user_id
    group_id = getattr(event.source, 'group_id', None)
    print(f"加入事件：user_id={user_id}, group_id={group_id}")

    welcome_text = "感謝加入，這是一個防踢群機器人。輸入 /help 查看功能列表。"
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=welcome_text)
    )

@handler.add(UnfollowEvent)
@handler.add(LeaveEvent)
@handler.add(MemberLeftEvent)
def handle_leave(event):
    user_id = event.source.user_id
    group_id = getattr(event.source, 'group_id', None)
    print(f"離開事件：user_id={user_id}, group_id={group_id}")
