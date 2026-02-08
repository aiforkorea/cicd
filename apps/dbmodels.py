# apps/dbmodels.py
import enum
from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from apps.extensions import db

# --- 1. 연결 테이블 (누가 무엇을 할 수 있는지 잇는 중간 다리) (다대다 관계를 위한 다리) ---

# [추가] 사용자와 역할을 이어주는 다리
user_roles = db.Table('user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True)
)

# 역할(Role)과 권한(Permission)을 이어주는 다리
role_permissions = db.Table('role_permissions',
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permissions.id'), primary_key=True)
)

# --- 2. 권한 관련 모델 ---
class Permission(db.Model):
    __tablename__ = 'permissions'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)  # 예: 'menu_access', 'api_call'
    description = db.Column(db.String(200)) # 이 권한이 뭐하는 건지 설명

    def __repr__(self):
        return f"<Permission {self.name}>"

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False) # 예: 'ADMIN', 'EXPERT', 'USER'
    
    # 이 역할이 가진 권한들 (다대다 관계)
    permissions = db.relationship('Permission', secondary=role_permissions, backref=db.backref('roles', lazy='dynamic'))

    def __repr__(self):
        return f"<Role {self.name}>"

# --- 3. 사용자 모델 ---
class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True)
    email = db.Column(db.String(120), unique=True, index=True, nullable=False)
    # 소셜 유저를 위해 True로 변경 및 구글 로그인 시 password를 비워두고, 인증 시간을 기록, 일반 유저는 암호 입력을 별도 처리
    password_hash = db.Column(db.String, nullable=True)   
    # [중요] 한 유저는 여러 역할을 수행함. 이제 하나의 role_id가 아니라 'roles'라는 리스트(다대다)를 가집니다.
    roles = db.relationship('Role', secondary=user_roles, backref=db.backref('users', lazy='dynamic'))
    is_active = db.Column(db.Boolean, default=True)
    confirmed = db.Column(db.Boolean, default=False)
    confirmed_at = db.Column(db.DateTime, nullable=True)
    # 서비스 이용 제한 관련
    usage_count = db.Column(db.Integer, default=0)
    daily_limit = db.Column(db.Integer, default=1000)
    monthly_limit = db.Column(db.Integer, default=5000)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    # 구독 정보와 연결 (User <-> Subscription)
    subscriptions = db.relationship('Subscription', back_populates='user', cascade='all, delete-orphan')

    @property
    def password(self):
        raise AttributeError('비밀번호는 읽을 수 없는 속성입니다.')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)
    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    # 사용자가 특정 권한을 가졌는지 모든 역할을 탐색. 여러 역할 중 하나라도 해당 권한을 가지고 있는지 확인
    def can(self, permission_name):
        for role in self.roles:
            if any(p.name == permission_name for p in role.permissions):
                return True
        return False

    # [수정] 관리자 역할이 리스트 안에 있는지 확인
    def is_admin(self):
        return any(role.name == 'ADMIN' for role in self.roles)

    # [편의 기능] 사용자에게 역할 추가하기
    def add_role(self, role_name):
        role = Role.query.filter_by(name=role_name).first()
        if role and role not in self.roles:
            self.roles.append(role)

    def __repr__(self):
        return f'<User {self.username}>'

# --- 4. 서비스 및 구독  모델 ---
class Service(db.Model):
    __tablename__ = "services"
    id = db.Column(db.Integer, primary_key=True)
    servicename = db.Column(db.String(100), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_auto = db.Column(db.Boolean, default=True)  # 자동 승인 여부
    price = db.Column(db.Integer, default=0)
    description = db.Column(db.Text)
    service_endpoint = db.Column(db.String(255))
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    subscriptions = db.relationship('Subscription', back_populates='service', cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Service {self.servicename}>"

class Subscription(db.Model):
    __tablename__ = "subscriptions"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=False) 
    status = db.Column(db.String(20), default='pending') # pending, approved, rejected
    
    request_date = db.Column(db.DateTime, default=datetime.now)
    approval_date = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', back_populates='subscriptions')
    service = db.relationship('Service', back_populates='subscriptions')

    # 한 사람이 같은 서비스를 여러번 신청 못하게 방지
    __table_args__ = (db.UniqueConstraint('user_id', 'service_id', name='_user_service_uc'),)

class Payment(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False) # 결제 금액
    merchant_uid = db.Column(db.String(100), unique=True) # 주문 번호
    status = db.Column(db.String(20), default='ready') # 상태 (ready: 대기, paid: 완료, cancelled: 취소)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    user = db.relationship('User', backref='payments')
