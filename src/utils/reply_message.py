# src/utils/reply_message.py
from linebot import LineBotApi
from linebot.models import TextSendMessage

def reply_text_message(line_bot_api: LineBotApi, reply_token: str, text: str):
    """
    安全回覆訊息封裝函數，避免 bot crash
    :param line_bot_api: LINE Bot API 實例
    :param reply_token: 回應 token
    :param text: 要發送的訊息
    """
    try:
        line_bot_api.reply_message(
            reply_token,
            TextSendMessage(text=text)
        )
    except Exception as e:
        print(f"[錯誤] 回應訊息失敗：{str(e)}")
