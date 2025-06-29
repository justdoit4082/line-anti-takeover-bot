import logging
from datetime import datetime, timedelta
from linebot.exceptions import LineBotApiError
from linebot.models import TextSendMessage
from src.models.group import db, Group, Member, Blacklist, AuditLog

logger = logging.getLogger(__name__)

class AntiTakeoverService:
    """防翻群服務類別"""
    
    def __init__(self, line_bot_api):
        self.line_bot_api = line_bot_api
    
    def check_mass_join(self, group_id, new_member_count):
        """
        檢查是否為異常大量加入
        
        Args:
            group_id (str): 群組ID
            new_member_count (int): 新加入成員數量
            
        Returns:
            bool: 是否為異常大量加入
        """
        try:
            # 取得群組設定
            group = Group.query.filter_by(group_id=group_id).first()
            if not group:
                return False
            
            threshold = group.threshold
            
            # 檢查過去1分鐘內的加入事件
            one_minute_ago = datetime.utcnow() - timedelta(minutes=1)
            recent_joins = AuditLog.query.filter(
                AuditLog.group_id == group_id,
                AuditLog.action == 'member_join',
                AuditLog.timestamp >= one_minute_ago
            ).all()
            
            # 計算過去1分鐘內加入的總人數
            total_recent_joins = sum([
                len(log.get_details().get('member_ids', [])) 
                for log in recent_joins
            ])
            
            # 加上當前加入的人數
            total_joins = total_recent_joins + new_member_count
            
            logger.info(f"Group {group_id}: {total_joins} joins in last minute (threshold: {threshold})")
            
            return total_joins > threshold
            
        except Exception as e:
            logger.error(f"Error checking mass join: {e}")
            return False
    
    def kick_member(self, group_id, user_id):
        """
        踢出群組成員
        
        Args:
            group_id (str): 群組ID
            user_id (str): 使用者ID
        """
        try:
            if self.line_bot_api:
                # 注意：LINE Bot API目前不支援直接踢人功能
                # 這裡只是示範，實際上需要群組管理員手動操作
                logger.warning(f"Cannot kick user {user_id} from group {group_id}: API limitation")
                
                # 記錄嘗試踢人的事件
                log = AuditLog(
                    group_id=group_id,
                    user_id=user_id,
                    action='kick_attempt',
                    details={'reason': 'blacklisted_user'}
                )
                db.session.add(log)
                db.session.commit()
            
        except LineBotApiError as e:
            logger.error(f"LINE Bot API error when kicking user: {e}")
        except Exception as e:
            logger.error(f"Error kicking member: {e}")
    
    def block_user(self, group_id, user_id, reason=None):
        """
        封鎖使用者
        
        Args:
            group_id (str): 群組ID
            user_id (str): 使用者ID
            reason (str): 封鎖原因
        """
        try:
            # 檢查是否已在黑名單中
            existing_blacklist = Blacklist.query.filter_by(
                user_id=user_id,
                group_id=group_id
            ).first()
            
            if not existing_blacklist:
                # 新增到黑名單
                blacklist_entry = Blacklist(
                    user_id=user_id,
                    group_id=group_id,
                    reason=reason
                )
                db.session.add(blacklist_entry)
                
                # 記錄事件
                log = AuditLog(
                    group_id=group_id,
                    user_id=user_id,
                    action='user_blocked',
                    details={'reason': reason}
                )
                db.session.add(log)
                db.session.commit()
                
                logger.info(f"User {user_id} blocked in group {group_id}")
                return True
            else:
                logger.info(f"User {user_id} already blocked in group {group_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error blocking user: {e}")
            return False
    
    def unblock_user(self, group_id, user_id):
        """
        解除封鎖使用者
        
        Args:
            group_id (str): 群組ID
            user_id (str): 使用者ID
        """
        try:
            # 從黑名單中移除
            blacklist_entry = Blacklist.query.filter_by(
                user_id=user_id,
                group_id=group_id
            ).first()
            
            if blacklist_entry:
                db.session.delete(blacklist_entry)
                
                # 記錄事件
                log = AuditLog(
                    group_id=group_id,
                    user_id=user_id,
                    action='user_unblocked'
                )
                db.session.add(log)
                db.session.commit()
                
                logger.info(f"User {user_id} unblocked in group {group_id}")
                return True
            else:
                logger.info(f"User {user_id} not in blacklist for group {group_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error unblocking user: {e}")
            return False
    
    def is_user_blocked(self, group_id, user_id):
        """
        檢查使用者是否被封鎖
        
        Args:
            group_id (str): 群組ID
            user_id (str): 使用者ID
            
        Returns:
            bool: 是否被封鎖
        """
        try:
            # 檢查群組特定黑名單和全域黑名單
            blacklist_entry = Blacklist.query.filter(
                (Blacklist.user_id == user_id) & 
                ((Blacklist.group_id == group_id) | (Blacklist.group_id.is_(None)))
            ).first()
            
            return blacklist_entry is not None
            
        except Exception as e:
            logger.error(f"Error checking if user is blocked: {e}")
            return False
    
    def notify_admins(self, group, message):
        """
        通知群組管理員
        
        Args:
            group (Group): 群組物件
            message (str): 通知訊息
        """
        try:
            if not self.line_bot_api:
                logger.warning("LINE Bot API not configured")
                return
            
            admin_ids = group.get_admin_ids()
            
            if not admin_ids:
                logger.warning(f"No admins configured for group {group.group_id}")
                return
            
            # 發送訊息給每個管理員
            for admin_id in admin_ids:
                try:
                    self.line_bot_api.push_message(
                        admin_id,
                        TextSendMessage(text=f"[防翻群警報] {group.group_name or group.group_id}\n\n{message}")
                    )
                    logger.info(f"Notification sent to admin {admin_id}")
                except LineBotApiError as e:
                    logger.error(f"Failed to send notification to admin {admin_id}: {e}")
            
            # 記錄通知事件
            log = AuditLog(
                group_id=group.group_id,
                action='admin_notification',
                details={
                    'message': message,
                    'admin_count': len(admin_ids)
                }
            )
            db.session.add(log)
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Error notifying admins: {e}")
    
    def analyze_suspicious_activity(self, group_id, time_window_minutes=5):
        """
        分析可疑活動
        
        Args:
            group_id (str): 群組ID
            time_window_minutes (int): 分析時間窗口（分鐘）
            
        Returns:
            dict: 分析結果
        """
        try:
            time_threshold = datetime.utcnow() - timedelta(minutes=time_window_minutes)
            
            # 查詢最近的活動
            recent_logs = AuditLog.query.filter(
                AuditLog.group_id == group_id,
                AuditLog.timestamp >= time_threshold
            ).all()
            
            # 統計各種活動
            activity_stats = {
                'member_join': 0,
                'member_leave': 0,
                'message': 0,
                'suspicious_events': 0,
                'total_events': len(recent_logs)
            }
            
            for log in recent_logs:
                if log.action in activity_stats:
                    activity_stats[log.action] += 1
                
                if log.is_suspicious:
                    activity_stats['suspicious_events'] += 1
            
            # 判斷是否異常
            is_suspicious = (
                activity_stats['member_join'] > 10 or  # 5分鐘內超過10人加入
                activity_stats['suspicious_events'] > 0 or  # 有標記為可疑的事件
                activity_stats['total_events'] > 50  # 5分鐘內超過50個事件
            )
            
            return {
                'is_suspicious': is_suspicious,
                'stats': activity_stats,
                'analysis_time': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing suspicious activity: {e}")
            return {
                'is_suspicious': False,
                'stats': {},
                'error': str(e)
            }
    
    def get_group_statistics(self, group_id):
        """
        取得群組統計資訊
        
        Args:
            group_id (str): 群組ID
            
        Returns:
            dict: 統計資訊
        """
        try:
            group = Group.query.filter_by(group_id=group_id).first()
            if not group:
                return None
            
            member_count = Member.query.filter_by(group_id=group_id).count()
            blacklist_count = Blacklist.query.filter_by(group_id=group_id).count()
            
            # 最近24小時的活動
            yesterday = datetime.utcnow() - timedelta(days=1)
            recent_activity = AuditLog.query.filter(
                AuditLog.group_id == group_id,
                AuditLog.timestamp >= yesterday
            ).count()
            
            return {
                'group_id': group_id,
                'group_name': group.group_name,
                'member_count': member_count,
                'admin_count': len(group.get_admin_ids()),
                'blacklist_count': blacklist_count,
                'threshold': group.threshold,
                'recent_activity_24h': recent_activity,
                'created_at': group.created_at.isoformat() if group.created_at else None
            }
            
        except Exception as e:
            logger.error(f"Error getting group statistics: {e}")
            return None

