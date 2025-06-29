from flask import Blueprint, request, jsonify
from src.models.group import db, Group, Member, Blacklist, AuditLog
from src.services.anti_takeover import AntiTakeoverService
import logging

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/groups', methods=['GET'])
def get_groups():
    """取得所有群組列表"""
    try:
        groups = Group.query.all()
        return jsonify({
            'success': True,
            'groups': [group.to_dict() for group in groups]
        })
    except Exception as e:
        logger.error(f"Error getting groups: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/groups/<group_id>', methods=['GET'])
def get_group(group_id):
    """取得特定群組資訊"""
    try:
        group = Group.query.filter_by(group_id=group_id).first()
        if not group:
            return jsonify({'success': False, 'error': 'Group not found'}), 404
        
        # 取得群組統計
        anti_takeover_service = AntiTakeoverService(None)
        stats = anti_takeover_service.get_group_statistics(group_id)
        
        return jsonify({
            'success': True,
            'group': group.to_dict(),
            'statistics': stats
        })
    except Exception as e:
        logger.error(f"Error getting group {group_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/groups/<group_id>/members', methods=['GET'])
def get_group_members(group_id):
    """取得群組成員列表"""
    try:
        members = Member.query.filter_by(group_id=group_id).all()
        return jsonify({
            'success': True,
            'members': [member.to_dict() for member in members]
        })
    except Exception as e:
        logger.error(f"Error getting members for group {group_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/groups/<group_id>/blacklist', methods=['GET'])
def get_group_blacklist(group_id):
    """取得群組黑名單"""
    try:
        blacklist = Blacklist.query.filter_by(group_id=group_id).all()
        return jsonify({
            'success': True,
            'blacklist': [entry.to_dict() for entry in blacklist]
        })
    except Exception as e:
        logger.error(f"Error getting blacklist for group {group_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/groups/<group_id>/logs', methods=['GET'])
def get_group_logs(group_id):
    """取得群組操作日誌"""
    try:
        # 取得查詢參數
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        action = request.args.get('action')
        suspicious_only = request.args.get('suspicious_only', False, type=bool)
        
        # 建立查詢
        query = AuditLog.query.filter_by(group_id=group_id)
        
        if action:
            query = query.filter(AuditLog.action == action)
        
        if suspicious_only:
            query = query.filter(AuditLog.is_suspicious == True)
        
        # 按時間倒序排列
        query = query.order_by(AuditLog.timestamp.desc())
        
        # 分頁
        logs = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'success': True,
            'logs': [log.to_dict() for log in logs.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': logs.total,
                'pages': logs.pages,
                'has_next': logs.has_next,
                'has_prev': logs.has_prev
            }
        })
    except Exception as e:
        logger.error(f"Error getting logs for group {group_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/groups/<group_id>/settings', methods=['PUT'])
def update_group_settings(group_id):
    """更新群組設定"""
    try:
        data = request.get_json()
        
        group = Group.query.filter_by(group_id=group_id).first()
        if not group:
            return jsonify({'success': False, 'error': 'Group not found'}), 404
        
        # 更新設定
        if 'threshold' in data:
            threshold = data['threshold']
            if isinstance(threshold, int) and threshold > 0:
                group.threshold = threshold
            else:
                return jsonify({'success': False, 'error': 'Invalid threshold value'}), 400
        
        if 'group_name' in data:
            group.group_name = data['group_name']
        
        if 'admin_ids' in data:
            if isinstance(data['admin_ids'], list):
                group.set_admin_ids(data['admin_ids'])
            else:
                return jsonify({'success': False, 'error': 'admin_ids must be a list'}), 400
        
        db.session.commit()
        
        # 記錄設定變更
        log = AuditLog(
            group_id=group_id,
            action='settings_updated',
            details=data
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'group': group.to_dict()
        })
    except Exception as e:
        logger.error(f"Error updating group settings {group_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/groups/<group_id>/block', methods=['POST'])
def block_user(group_id):
    """封鎖使用者"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        reason = data.get('reason', '')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'user_id is required'}), 400
        
        anti_takeover_service = AntiTakeoverService(None)
        success = anti_takeover_service.block_user(group_id, user_id, reason)
        
        if success:
            return jsonify({'success': True, 'message': 'User blocked successfully'})
        else:
            return jsonify({'success': False, 'error': 'User already blocked or error occurred'}), 400
    except Exception as e:
        logger.error(f"Error blocking user in group {group_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/groups/<group_id>/unblock', methods=['POST'])
def unblock_user(group_id):
    """解除封鎖使用者"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'user_id is required'}), 400
        
        anti_takeover_service = AntiTakeoverService(None)
        success = anti_takeover_service.unblock_user(group_id, user_id)
        
        if success:
            return jsonify({'success': True, 'message': 'User unblocked successfully'})
        else:
            return jsonify({'success': False, 'error': 'User not in blacklist or error occurred'}), 400
    except Exception as e:
        logger.error(f"Error unblocking user in group {group_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/groups/<group_id>/analyze', methods=['GET'])
def analyze_group_activity(group_id):
    """分析群組活動"""
    try:
        time_window = request.args.get('time_window', 5, type=int)
        
        anti_takeover_service = AntiTakeoverService(None)
        analysis = anti_takeover_service.analyze_suspicious_activity(group_id, time_window)
        
        return jsonify({
            'success': True,
            'analysis': analysis
        })
    except Exception as e:
        logger.error(f"Error analyzing group activity {group_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/statistics', methods=['GET'])
def get_overall_statistics():
    """取得整體統計資訊"""
    try:
        total_groups = Group.query.count()
        total_members = Member.query.count()
        total_blacklist = Blacklist.query.count()
        
        # 最近24小時的活動
        from datetime import datetime, timedelta
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_activity = AuditLog.query.filter(
            AuditLog.timestamp >= yesterday
        ).count()
        
        suspicious_activity = AuditLog.query.filter(
            AuditLog.timestamp >= yesterday,
            AuditLog.is_suspicious == True
        ).count()
        
        return jsonify({
            'success': True,
            'statistics': {
                'total_groups': total_groups,
                'total_members': total_members,
                'total_blacklist': total_blacklist,
                'recent_activity_24h': recent_activity,
                'suspicious_activity_24h': suspicious_activity
            }
        })
    except Exception as e:
        logger.error(f"Error getting overall statistics: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

