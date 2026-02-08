# apps/auth/utils.py
from flask import current_app, render_template
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer
from apps.extensions import mail
from threading import Thread
from authlib.integrations.flask_client import OAuth # OAuth 라이브러리 임포트
from flask import current_app
from apps.extensions import db          # 공통 DB 도구

# oauth 객체 생성
oauth = OAuth() 

def generate_token(email, salt):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(email, salt=salt)
def confirm_token(token, salt, expiration=3600):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        return serializer.loads(token, salt=salt, max_age=expiration)
    except:
        return False

def send_async_email(app, msg):
    with app.app_context():
        try:
            mail.send(msg)
        except Exception as e:
            app.logger.error(f"비동기 메일 전송 실패: {e}")

def send_email(subject, to, template, **kwargs):
    app = current_app._get_current_object()
    # 발신자 설정 확인
    sender = app.config.get('MAIL_DEFAULT_SENDER')
    msg = Message(subject, recipients=[to], sender=sender)
    msg.body = render_template(template + '.html', **kwargs)
    msg.html = render_template(template + '.html', **kwargs)
    # Render 배포 환경에서 Network Unreachable이 계속된다면 
    # 아래 Thread 부분을 주석처리하고 mail.send(msg)를 직접 호출해 보세요.
    if app.config.get('TESTING'):
        mail.send(msg)
    else:
        # 비동기 전송 시도
        Thread(target=send_async_email, args=[app, msg]).start()

def register_social_login(app):
    oauth.init_app(app)
    oauth.register(
        name='google',
        client_id=app.config.get('GOOGLE_CLIENT_ID'),
        client_secret=app.config.get('GOOGLE_CLIENT_SECRET'),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )

def upgrade_user_to_premium(user):
    from apps.dbmodels import Role
    # 1. 'PREMIUM'이라는 이름표를 찾습니다.
    premium_role = Role.query.filter_by(name='PREMIUM').first()
    # 2. 이미 가지고 있지 않다면 달아줍니다.
    if premium_role and premium_role not in user.roles:
        user.roles.append(premium_role)
        db.session.commit()
        return True
    return False 
