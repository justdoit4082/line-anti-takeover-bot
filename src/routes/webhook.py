import os
import json
import time
from flask import Blueprint, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, JoinEvent, LeaveEvent, UnfollowEvent

webhook_bp = Blueprint('webhook', __name__)

channel_secret = os.getenv('LINE_CHANNEL_SECRET')
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')

handler = WebhookHandler(channel_secret)
line_bot_api = LineBotApi(channel_access_token)

# 管理員 userId（輸入我的U-ID）
ADMIN_USER_ID = 'U27bdcfedc1a0d11770345793882688c6'

# 建立所需資料夾
os.makedirs('banlist', exist_ok=True)
os.makedirs('logs', exist_ok=True)
os.makedirs('watchdog', exist_ok=True)

# 接收 LINE webhook
@webhook_bp.route("/webhook", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    group_id = getattr(event.source, 'group_id', None)
    text = event.message.text.strip()

    if group_id is None:
        return

    if not text.startswith("/"):
        return

    if text == "/hi":
        reply(event, "你好！")
    elif text == "/myid":
        reply(event, f"你的 userId 是：{user_id}")
    elif text == "/warn":
        log_path = f'logs/{group_id}_warn.log'
        with open(log_path, 'a', encoding='utf-8') as logf:
            logf.write(f"[{time.ctime()}] ⚠️ 警告使用者 {user_id}
")
        reply(event, "⚠️ 已記錄警告。")
    elif text == "/ban":
        if user_id != ADMIN_USER_ID:
            reply(event, "❌ 只有管理員可以使用此指令。")
            return
        mention_id = extract_mention_id(event)
        if mention_id:
            banlist_path = f'banlist/{group_id}.txt'
            with open(banlist_path, 'a', encoding='utf-8') as f:
                f.write(mention_id + "
")
            try:
                line_bot_api.kickout_group_member(group_id, mention_id)
                reply(event, f"✅ 已踢除 {mention_id} 並加入黑名單。")
            except Exception as e:
                reply(event, f"⚠️ 踢除失敗：{str(e)}")
        else:
            reply(event, "請@要封鎖的對象")
    elif text == "/banlist":
        banlist_path = f'banlist/{group_id}.txt'
        if os.path.exists(banlist_path):
            with open(banlist_path, encoding='utf-8') as f:
                ids = f.read().strip().splitlines()
            reply(event, "📛 黑名單：
" + "
".join(ids))
        else:
            reply(event, "目前沒有黑名單")
    elif text == "/log":
        log_path = f'logs/{group_id}_warn.log'
        if os.path.exists(log_path):
            with open(log_path, encoding='utf-8') as f:
                lines = f.readlines()[-20:]
            reply(event, "📜 警告紀錄：
" + "".join(lines))
        else:
            reply(event, "尚無警告紀錄")

def reply(event, message):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=message)
    )

def extract_mention_id(event):
    """從 message 中找出@對象的 userId"""
    try:
        mentionees = event.message.mention.mentionees
        if mentionees:
            return mentionees[0].user_id
    except:
        return None
    return None
