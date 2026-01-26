#tests/conftest.py
import pytest, sys, os
# 현재 폴더의 한 단계 위(프로젝트 루트)를 파이썬 경로에 추가합니다.
# ModuleNotFoundError: No module named 'apps' 에러 예방
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from apps import create_app
from apps.config import TestingConfig
from apps.extensions import db
from apps.dbmodels import User

@pytest.fixture
def app():
    app = create_app(TestingConfig)
    # create_app 안에 이미 db.create_all()과 seed_db()가 포함되어 있으므로
    # 별도의 생성 코드 없이 바로 사용 가능합니다.
    with app.app_context():
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth_client(client, app):
    with app.app_context():
        from apps.dbmodels import Role
        user_role = Role.query.filter_by(name='USER').first()
        user = User(username='testuser', email='test@test.com', 
                    password='password123', role=user_role, confirmed=True)
        db.session.add(user)
        db.session.commit()
    client.post('/auth/login', data={'email': 'test@test.com', 'password': 'password123'}, follow_redirects=True)
    return client

