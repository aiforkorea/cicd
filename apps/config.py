#apps/config.py
import os
from datetime import timedelta
if os.environ.get('RENDER', None) != 'true':
    from dotenv import load_dotenv      # render.com이 아닌 로컬 환경에서만 .env를 로드(안해도 됨)
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    dotenv_path = os.path.join(BASE_DIR, '..', '.env')
    load_dotenv(dotenv_path)
class Config:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SECRET_KEY = os.getenv('SECRET_KEY', 'default-key')
    #API_KEY = os.getenv('API_KEY')
    #IRIS_LABELS = ['setosa', 'versicolor', 'virginica']
    INSTANCE_DIR = os.path.join(BASE_DIR, '..', 'instance')
    if not os.path.exists(INSTANCE_DIR):
        os.makedirs(INSTANCE_DIR)
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(INSTANCE_DIR, 'mydb.sqlite3')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Flask-Login
    # REMEMBER_COOKIE_DURATION = 3600  # 1시간
    CSRF_ENABLED = True
    CSRF_SESSION_KEY = os.getenv('CSRF_SESSION_KEY', SECRET_KEY) # 없으면,SECRET_KEY사용

# Brevo(Sendinblue) 이메일 설정
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp-relay.brevo.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587)) # 2525 포트 사용 권장
    
    # 2. 문자열 'True'를 불리언 True로 안전하게 변환
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() in ['true', '1', 't']
    MAIL_USE_SSL = os.getenv('MAIL_USE_SSL', 'False').lower() in ['true', '1', 't']
    
    MAIL_USERNAME = os.getenv('MAIL_USERNAME') # Brevo Login 이메일
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD') # Brevo SMTP Key
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', MAIL_USERNAME)
    # ADMIN config 
    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME')    
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL')    
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')

    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')

# 태스팅 config 추가
class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    MAIL_SUPPRESS_SEND = True
    # [추가] 테스트용 발신자 정보 강제 설정
    MAIL_USERNAME = "test@example.com"
    MAIL_DEFAULT_SENDER = "test@example.com"
