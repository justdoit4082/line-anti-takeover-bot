import os
import json
import time
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
    # 驗證簽名
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
    user_id = event.source.user_id
    group_id = getattr(event.source, 'group_id', None)

    # 如果沒有 group_id，代表是個人聊天，不處理
    if not group_id:
        return

    text = event.message.text
    print(f"來自群組 {group_id} 的訊息：{text}")

    reply_text = f"你說的是：{text}"
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

@handler.add(JoinEvent)
@handler.add(FollowEvent)
@handler.add(MemberJoinedEvent)
def handle_join(event):
    user_id = event.source.user_id
    group_id = getattr(event.source, 'group_id', None)
    print(f"加入事件：user_id={user_id}, group_id={group_id}")

    welcome_text = "感謝加入，這是一個防踢群機器人。"
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
    # 可選擇寫入離開記錄等

# ✅ 新增測試 webhook 接收事件用的端點（LINE 驗證 200 回應）
@webhook_bp.route('/webhook-test', methods=['POST'])
def webhook_test():
    try:
        payload = request.get_json(force=True, silent=True)
        if payload is None:
            return jsonify({'status': 'no payload'}), 400

        events = payload.get('events', [])
        results = []

        for event in events:
            results.append({'status': 'event received'})

        return jsonify(results), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
