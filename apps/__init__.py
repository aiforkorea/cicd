# apps/__init__.py
import os, logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from werkzeug.security import generate_password_hash

from apps.dbmodels import Permission
from .extensions import db, migrate, login_manager, csrf, mail
from .config import Config # 기본 설정
from apps.auth.utils import oauth, register_social_login # 이름 맞추기
from .utils import seed_db  # 위에서 만든 함수 가져오기

def create_app(config_class=Config): # 설정 클래스를 인자로 받음(테스트를 위해 추가 필요함)
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 로깅 설정
    if app.debug:
        app.logger.setLevel(logging.DEBUG)
    elif not app.testing: 
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

    # 확장 기능 초기화
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)

    with app.app_context():
        # 이 부분을 수정하세요!
        from apps.auth.utils import register_social_login # 이름을 utils.py와 맞춤
        register_social_login(app)
        
    from .dbmodels import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        from flask import flash, redirect, url_for, request
        flash('로그인이 필요합니다.', 'warning')
        return redirect(url_for('auth.login', next=request.path))

    from .main import main
    from .auth import auth
    from .provider import provider

    app.register_blueprint(main)
    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(provider, url_prefix='/provider')

    with app.app_context():
        # 1. 소셜 로그인 설정
        from apps.auth.utils import register_social_login
        register_social_login(app)
        
        # 2. DB 테이블 생성 (운영시는 migrate 권장이나 초기엔 create_all)
        #db.drop_all()         # 운영시에는 커멘트 처리 필요
        db.create_all()
        
        # 3. [추가] 기본 권한/역할 자동 생성 실행!
        seed_db(app)

        # 4. 관리자 계정 생성 로직 수정
        from .dbmodels import User, Role # Role 추가
        admin_email = app.config.get('ADMIN_EMAIL')
        if admin_email:
            if not User.query.filter_by(email=admin_email).first():
                admin_role = Role.query.filter_by(name='ADMIN').first()
                new_admin = User(
                    username=app.config.get('ADMIN_USERNAME'),
                    email=admin_email,
                    password=app.config.get('ADMIN_PASSWORD'),
                    confirmed=True
                )
                new_admin.roles.append(admin_role) # 리스트에 추가 (다대다 확인)
                db.session.add(new_admin)
                db.session.commit()
                print("관리자 계정 생성 완료!")

    # ... (템플릿용 변수 설정 부분 수정) ...
    @app.context_processor
    def inject_permissions():
        # 이제 템플릿(HTML)에서 Permission 모델을 직접 조회할 수 있어요.
        from .dbmodels import Permission
        return dict(Permission=Permission)

    return app