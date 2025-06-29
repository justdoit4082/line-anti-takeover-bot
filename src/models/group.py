from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class Group(db.Model):
    __tablename__ = 'groups'
    
    group_id = db.Column(db.String(255), primary_key=True)
    group_name = db.Column(db.String(255), nullable=True)
    admin_ids = db.Column(db.Text, nullable=True)  # JSON格式儲存管理員ID列表
    threshold = db.Column(db.Integer, default=5)  # 預設1分鐘內允許5人加入
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __init__(self, group_id, group_name=None, admin_ids=None, threshold=5):
        self.group_id = group_id
        self.group_name = group_name
        self.admin_ids = json.dumps(admin_ids) if admin_ids else json.dumps([])
        self.threshold = threshold
    
    def get_admin_ids(self):
        """取得管理員ID列表"""
        return json.loads(self.admin_ids) if self.admin_ids else []
    
    def set_admin_ids(self, admin_ids):
        """設定管理員ID列表"""
        self.admin_ids = json.dumps(admin_ids)
    
    def add_admin(self, user_id):
        """新增管理員"""
        admins = self.get_admin_ids()
        if user_id not in admins:
            admins.append(user_id)
            self.set_admin_ids(admins)
    
    def remove_admin(self, user_id):
        """移除管理員"""
        admins = self.get_admin_ids()
        if user_id in admins:
            admins.remove(user_id)
            self.set_admin_ids(admins)
    
    def is_admin(self, user_id):
        """檢查是否為管理員"""
        return user_id in self.get_admin_ids()
    
    def to_dict(self):
        return {
            'group_id': self.group_id,
            'group_name': self.group_name,
            'admin_ids': self.get_admin_ids(),
            'threshold': self.threshold,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Member(db.Model):
    __tablename__ = 'members'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(255), nullable=False)
    group_id = db.Column(db.String(255), db.ForeignKey('groups.group_id'), nullable=False)
    display_name = db.Column(db.String(255), nullable=True)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)
    is_blocked = db.Column(db.Boolean, default=False)
    
    # 建立複合唯一索引
    __table_args__ = (db.UniqueConstraint('user_id', 'group_id', name='unique_user_group'),)
    
    def __init__(self, user_id, group_id, display_name=None, is_admin=False):
        self.user_id = user_id
        self.group_id = group_id
        self.display_name = display_name
        self.is_admin = is_admin
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'group_id': self.group_id,
            'display_name': self.display_name,
            'joined_at': self.joined_at.isoformat() if self.joined_at else None,
            'is_admin': self.is_admin,
            'is_blocked': self.is_blocked
        }

class Blacklist(db.Model):
    __tablename__ = 'blacklist'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(255), nullable=False)
    group_id = db.Column(db.String(255), nullable=True)  # NULL表示全域黑名單
    reason = db.Column(db.Text, nullable=True)
    blocked_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __init__(self, user_id, group_id=None, reason=None):
        self.user_id = user_id
        self.group_id = group_id
        self.reason = reason
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'group_id': self.group_id,
            'reason': self.reason,
            'blocked_at': self.blocked_at.isoformat() if self.blocked_at else None
        }

class AuditLog(db.Model):
    __tablename__ = 'audit_log'
    
    log_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    group_id = db.Column(db.String(255), db.ForeignKey('groups.group_id'), nullable=False)
    user_id = db.Column(db.String(255), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text, nullable=True)  # JSON格式儲存詳細資訊
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_suspicious = db.Column(db.Boolean, default=False)
    
    def __init__(self, group_id, action, user_id=None, details=None, is_suspicious=False):
        self.group_id = group_id
        self.user_id = user_id
        self.action = action
        self.details = json.dumps(details) if details else None
        self.is_suspicious = is_suspicious
    
    def get_details(self):
        """取得詳細資訊"""
        return json.loads(self.details) if self.details else {}
    
    def set_details(self, details):
        """設定詳細資訊"""
        self.details = json.dumps(details)
    
    def to_dict(self):
        return {
            'log_id': self.log_id,
            'group_id': self.group_id,
            'user_id': self.user_id,
            'action': self.action,
            'details': self.get_details(),
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'is_suspicious': self.is_suspicious
        }

