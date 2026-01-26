# tests/test_main.py
import pytest
from apps.dbmodels import User, Role, Permission
from apps.extensions import db, mail

def test_main_index(client):
    """메인 페이지가 잘 열리는지 확인"""
    response = client.get('/')
    assert response.status_code == 200
    assert "서비스" in response.get_data(as_text=True)

def test_login_process(client, app):
    """회원가입 후 이메일 인증을 거쳐 로그인이 되는지 확인"""
    with mail.record_messages() as outbox:
        # 1. 회원가입 시도
        client.post('/auth/signup', data={
            'username': 'tester',
            'email': 'tester@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        assert len(outbox) == 1
    
    with app.app_context():
        # 2. 가입된 유저를 찾아서 강제로 '이메일 인증' 처리
        user = User.query.filter_by(email='tester@example.com').first()
        if user:
            user.confirmed = True
            # [중요] 가입 시 'USER' 역할이 자동으로 들어갔는지 확인
            user_role = Role.query.filter_by(name='USER').first()
            if user_role not in user.roles:
                user.roles.append(user_role)
            db.session.commit()

    # 3. 로그인 테스트
    response = client.post('/auth/login', data={
        'email': 'tester@example.com',
        'password': 'password123'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert "tester" in response.get_data(as_text=True)

def test_admin_menu_visibility(client, app):
    """이름표(Role)에 따라 메뉴가 보이고 안 보이는지 확인"""
    with app.app_context():
        # 테스트용 데이터 깔끔하게 정리
        User.query.filter(User.email.in_(['u@t.com', 'a@t.com'])).delete()
        
        # 이름표 가져오기 (conftest에서 이미 만들어진 상태)
        user_role = Role.query.filter_by(name='USER').first()
        admin_role = Role.query.filter_by(name='ADMIN').first()

        # 일반 유저 생성
        user = User(username='regular', email='u@t.com', password='p1', confirmed=True)
        user.roles.append(user_role)
        
        # 관리자 유저 생성
        admin = User(username='boss', email='a@t.com', password='p1', confirmed=True)
        admin.roles.append(admin_role)
        
        db.session.add_all([user, admin])
        db.session.commit()

    # 1. 일반 유저로 로그인해서 보기
    client.post('/auth/login', data={'email': 'u@t.com', 'password': 'p1'}, follow_redirects=True)
    page_user = client.get('/').get_data(as_text=True)
    assert "관리자" not in page_user # 일반 유저는 관리자 글자가 안 보여야 함
    client.get('/auth/logout', follow_redirects=True)

    # 2. 관리자 유저로 로그인해서 보기
    client.post('/auth/login', data={'email': 'a@t.com', 'password': 'p1'}, follow_redirects=True)
    page_admin = client.get('/').get_data(as_text=True)
    # base.html에서 current_user.can('admin_access')를 사용하므로
    # ADMIN 역할에 admin_access 권한이 있다면 "관리자" 글자가 보여야 함
    assert "관리자" in page_admin 

def test_login_failure_invalid_password(client, app):
    """비밀번호 틀렸을 때 실패하는지 확인"""
    with app.app_context():
        User.query.filter_by(email='f@t.com').delete()
        db.session.add(User(username='f', email='f@t.com', password='correct', confirmed=True))
        db.session.commit()
    
    response = client.post('/auth/login', data={'email': 'f@t.com', 'password': 'wrong'}, follow_redirects=True)
    assert "확인 필요" in response.get_data(as_text=True)

