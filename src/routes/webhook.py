from flask import Blueprint, request, abort, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    JoinEvent, LeaveEvent, MemberJoinedEvent, MemberLeftEvent,
    PostbackEvent, FollowEvent, UnfollowEvent
)
import os
import logging
from datetime import datetime, timedelta
from src.models.group import db, Group, Member, Blacklist, AuditLog
from src.services.anti_takeover import AntiTakeoverService

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

webhook_bp = Blueprint('webhook', __name__)

# LINE Bot API設定
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')

if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_CHANNEL_SECRET:
    logger.warning("LINE_CHANNEL_ACCESS_TOKEN or LINE_CHANNEL_SECRET not set")
    line_bot_api = None
    handler = None
else:
    line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
    handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 初始化防翻群服務
anti_takeover_service = AntiTakeoverService(line_bot_api)

@webhook_bp.route('/webhook', methods=['POST'])
def webhook():
    """LINE Webhook端點"""
    if not handler:
        return jsonify({'error': 'Bot not configured properly. Please set LINE_CHANNEL_ACCESS_TOKEN and LINE_CHANNEL_SECRET environment variables.'}), 500
    
    # 取得X-Line-Signature header value
    signature = request.headers.get('X-Line-Signature')
    if not signature:
        abort(400)
    
    # 取得request body
    body = request.get_data(as_text=True)
    logger.info(f"Request body: {body}")
    
    # 處理webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        logger.error("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)
    except Exception as e:
        logger.error(f"Error handling webhook: {e}")
        abort(500)
    
    return 'OK'

# 只有在handler存在時才註冊事件處理器
if handler:
    @handler.add(MessageEvent, message=TextMessage)
    def handle_message(event):
        """處理文字訊息事件"""
        try:
            message_text = event.message.text.strip()
            user_id = event.source.user_id
            
            # 檢查是否為群組訊息
            if hasattr(event.source, 'group_id'):
                group_id = event.source.group_id
                
                # 記錄訊息事件
                log = AuditLog(
                    group_id=group_id,
                    user_id=user_id,
                    action='message',
                    details={'text': message_text[:100]}  # 只記錄前100字元
                )
                db.session.add(log)
                db.session.commit()
                
                # 處理機器人指令
                if message_text.startswith('/'):
                    handle_command(event, message_text, group_id, user_id)
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")

    def handle_command(event, command, group_id, user_id):
        """處理機器人指令"""
        try:
            # 檢查群組是否存在
            group = Group.query.filter_by(group_id=group_id).first()
            if not group:
                return
            
            # 檢查是否為管理員
            is_admin = group.is_admin(user_id)
            
            if command == '/help':
                help_text = """防翻群機器人指令說明：
/help - 顯示此說明
/status - 查看群組狀態
/threshold <數字> - 設定異常加入閾值 (僅管理員)
/addadmin <@使用者> - 新增管理員 (僅管理員)
/removeadmin <@使用者> - 移除管理員 (僅管理員)
/blacklist - 查看黑名單
/block <@使用者> - 封鎖使用者 (僅管理員)
/unblock <@使用者> - 解除封鎖 (僅管理員)"""
                
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=help_text)
                )
            
            elif command == '/status':
                member_count = Member.query.filter_by(group_id=group_id).count()
                blacklist_count = Blacklist.query.filter_by(group_id=group_id).count()
                
                status_text = f"""群組狀態：
群組名稱：{group.group_name or '未知'}
成員數量：{member_count}
異常加入閾值：{group.threshold}人/分鐘
黑名單數量：{blacklist_count}
管理員數量：{len(group.get_admin_ids())}"""
                
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=status_text)
                )
            
            elif command.startswith('/threshold ') and is_admin:
                try:
                    threshold = int(command.split(' ')[1])
                    if threshold > 0:
                        group.threshold = threshold
                        db.session.commit()
                        
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextSendMessage(text=f"異常加入閾值已設定為 {threshold} 人/分鐘")
                        )
                    else:
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextSendMessage(text="閾值必須大於0")
                        )
                except (ValueError, IndexError):
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text="請輸入有效的數字，例如：/threshold 5")
                    )
            
            elif command == '/blacklist':
                blacklist_users = Blacklist.query.filter_by(group_id=group_id).all()
                if blacklist_users:
                    blacklist_text = "黑名單使用者：\n"
                    for user in blacklist_users:
                        blacklist_text += f"• {user.user_id} ({user.reason or '無原因'})\n"
                else:
                    blacklist_text = "目前沒有黑名單使用者"
                
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=blacklist_text)
                )
            
            elif not is_admin and command.startswith(('/threshold', '/addadmin', '/removeadmin', '/block', '/unblock')):
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="此指令僅限管理員使用")
                )
        
        except Exception as e:
            logger.error(f"Error handling command: {e}")

    @handler.add(JoinEvent)
    def handle_join(event):
        """處理機器人加入群組事件"""
        try:
            group_id = event.source.group_id
            
            # 建立或更新群組記錄
            group = Group.query.filter_by(group_id=group_id).first()
            if not group:
                group = Group(group_id=group_id)
                db.session.add(group)
            
            # 記錄事件
            log = AuditLog(
                group_id=group_id,
                action='bot_join',
                details={'timestamp': datetime.utcnow().isoformat()}
            )
            db.session.add(log)
            db.session.commit()
            
            # 發送歡迎訊息
            welcome_message = """感謝邀請防翻群機器人！

我會幫助保護這個群組免受惡意攻擊。

主要功能：
• 自動檢測異常大量加入
• 防止未授權的管理操作
• 通知管理員可疑活動
• 自動處理惡意帳號

輸入 /help 查看完整指令說明
輸入 /status 查看群組狀態

請群組管理員使用 /addadmin @使用者 來設定機器人管理員。"""
            
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=welcome_message)
            )
            
            logger.info(f"Bot joined group: {group_id}")
        
        except Exception as e:
            logger.error(f"Error handling join event: {e}")

    @handler.add(LeaveEvent)
    def handle_leave(event):
        """處理機器人離開群組事件"""
        try:
            group_id = event.source.group_id
            
            # 記錄事件
            log = AuditLog(
                group_id=group_id,
                action='bot_leave',
                details={'timestamp': datetime.utcnow().isoformat()}
            )
            db.session.add(log)
            db.session.commit()
            
            logger.info(f"Bot left group: {group_id}")
        
        except Exception as e:
            logger.error(f"Error handling leave event: {e}")

    @handler.add(MemberJoinedEvent)
    def handle_member_joined(event):
        """處理成員加入群組事件"""
        try:
            group_id = event.source.group_id
            joined_members = event.joined.members
            
            # 檢查群組是否存在
            group = Group.query.filter_by(group_id=group_id).first()
            if not group:
                group = Group(group_id=group_id)
                db.session.add(group)
                db.session.commit()
            
            # 處理每個加入的成員
            for member in joined_members:
                user_id = member.user_id
                
                # 檢查是否在黑名單中
                is_blacklisted = Blacklist.query.filter(
                    (Blacklist.user_id == user_id) & 
                    ((Blacklist.group_id == group_id) | (Blacklist.group_id.is_(None)))
                ).first()
                
                if is_blacklisted:
                    # 自動踢出黑名單使用者
                    try:
                        anti_takeover_service.kick_member(group_id, user_id)
                        logger.info(f"Kicked blacklisted user {user_id} from group {group_id}")
                        
                        # 通知管理員
                        anti_takeover_service.notify_admins(
                            group,
                            f"已自動踢出黑名單使用者：{user_id}\n原因：{is_blacklisted.reason or '無'}"
                        )
                    except Exception as e:
                        logger.error(f"Failed to kick blacklisted user: {e}")
                    continue
                
                # 新增成員記錄
                existing_member = Member.query.filter_by(
                    user_id=user_id, 
                    group_id=group_id
                ).first()
                
                if not existing_member:
                    new_member = Member(
                        user_id=user_id,
                        group_id=group_id,
                        display_name=getattr(member, 'display_name', None)
                    )
                    db.session.add(new_member)
            
            # 檢查是否為異常大量加入
            is_suspicious = anti_takeover_service.check_mass_join(group_id, len(joined_members))
            
            # 記錄事件
            log = AuditLog(
                group_id=group_id,
                action='member_join',
                details={
                    'member_count': len(joined_members),
                    'member_ids': [m.user_id for m in joined_members]
                },
                is_suspicious=is_suspicious
            )
            db.session.add(log)
            db.session.commit()
            
            if is_suspicious:
                # 通知管理員
                anti_takeover_service.notify_admins(
                    group,
                    f"⚠️ 偵測到異常大量加入！\n在短時間內有 {len(joined_members)} 人加入群組\n請注意是否有翻群風險"
                )
            
            logger.info(f"Members joined group {group_id}: {len(joined_members)} members")
        
        except Exception as e:
            logger.error(f"Error handling member joined event: {e}")

    @handler.add(MemberLeftEvent)
    def handle_member_left(event):
        """處理成員離開群組事件"""
        try:
            group_id = event.source.group_id
            left_members = event.left.members
            
            # 處理每個離開的成員
            for member in left_members:
                user_id = member.user_id
                
                # 更新成員記錄（標記為已離開或刪除記錄）
                existing_member = Member.query.filter_by(
                    user_id=user_id,
                    group_id=group_id
                ).first()
                
                if existing_member:
                    db.session.delete(existing_member)
            
            # 記錄事件
            log = AuditLog(
                group_id=group_id,
                action='member_leave',
                details={
                    'member_count': len(left_members),
                    'member_ids': [m.user_id for m in left_members]
                }
            )
            db.session.add(log)
            db.session.commit()
            
            logger.info(f"Members left group {group_id}: {len(left_members)} members")
        
        except Exception as e:
            logger.error(f"Error handling member left event: {e}")

    @handler.add(PostbackEvent)
    def handle_postback(event):
        """處理回傳事件"""
        try:
            postback_data = event.postback.data
            user_id = event.source.user_id
            
            if hasattr(event.source, 'group_id'):
                group_id = event.source.group_id
                
                # 記錄事件
                log = AuditLog(
                    group_id=group_id,
                    user_id=user_id,
                    action='postback',
                    details={'data': postback_data}
                )
                db.session.add(log)
                db.session.commit()
            
            logger.info(f"Postback event: {postback_data}")
        
        except Exception as e:
            logger.error(f"Error handling postback event: {e}")

    @handler.add(FollowEvent)
    def handle_follow(event):
        """處理追蹤事件"""
        try:
            user_id = event.source.user_id
            
            welcome_message = """歡迎使用防翻群機器人！

請將我加入需要保護的LINE群組中，我會幫助：
• 監控異常大量加入
• 防止惡意操作
• 保護群組安全

如需協助，請聯繫機器人管理員。"""
            
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=welcome_message)
            )
            
            logger.info(f"User followed bot: {user_id}")
        
        except Exception as e:
            logger.error(f"Error handling follow event: {e}")

    @handler.add(UnfollowEvent)
    def handle_unfollow(event):
        """處理取消追蹤事件"""
        try:
            user_id = event.source.user_id
            logger.info(f"User unfollowed bot: {user_id}")
        
        except Exception as e:
            logger.error(f"Error handling unfollow event: {e}")

# 健康檢查端點
@webhook_bp.route('/health', methods=['GET'])
def health_check():
    """健康檢查端點"""
    return jsonify({
        'status': 'healthy',
        'bot_configured': handler is not None,
        'timestamp': datetime.utcnow().isoformat()
    })

