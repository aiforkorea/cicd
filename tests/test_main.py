# tests/test_main.py
import pytest
from apps.dbmodels import User
from apps.extensions import db, mail
def test_main_index(client):
    response = client.get('/')
    assert response.status_code == 200
    assert "서비스" in response.get_data(as_text=True)
def test_login_process(client, app):
    """회원가입 시 메일 가로채기 확인 및 로그인 테스트"""
    with mail.record_messages() as outbox:
        # 1. 회원가입
        client.post('/auth/signup', data={
            'username': 'tester',
            'email': 'tester@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        assert len(outbox) == 1
        assert "인증" in outbox[0].subject
    # 2. 강제 인증 처리
    with app.app_context():
        user = User.query.filter_by(email='tester@example.com').first()
        if user:
            user.confirmed = True
            db.session.commit()
    # 3. 로그인 시도
    response = client.post('/auth/login', data={
        'email': 'tester@example.com',
        'password': 'password123'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert "tester" in response.get_data(as_text=True)
def test_admin_menu_visibility(client, app):
    """권한별 관리자 메뉴 노출 테스트"""
    with app.app_context():
        # 데이터 정리
        User.query.filter(User.email.in_(['u@t.com', 'a@t.com'])).delete()
        user = User(username='regular', email='u@t.com', password='p1', 
                    user_type=UserType.USER, confirmed=True)
        admin = User(username='boss', email='a@t.com', password='p1', 
                     user_type=UserType.ADMIN, confirmed=True)
        db.session.add_all([user, admin])
        db.session.commit()
    # 일반 유저 로그인
    client.post('/auth/login', data={'email': 'u@t.com', 'password': 'p1'}, follow_redirects=True)
    page_user = client.get('/').get_data(as_text=True)
    assert "regular" in page_user
    assert "관리자" not in page_user 
    client.get('/auth/logout', follow_redirects=True)
    # 관리자 로그인
    client.post('/auth/login', data={'email': 'a@t.com', 'password': 'p1'}, follow_redirects=True)
    page_admin = client.get('/').get_data(as_text=True)
    assert "boss" in page_admin
def test_login_failure_invalid_password(client, app):
    with app.app_context():
        User.query.filter_by(email='f@t.com').delete()
        db.session.add(User(username='f', email='f@t.com', password='correct', confirmed=True))
        db.session.commit()
    response = client.post('/auth/login', data={'email': 'f@t.com', 'password': 'wrong'}, follow_redirects=True)
    assert "확인 필요" in response.get_data(as_text=True)
def test_signup_duplicate_email(client, app):
    with app.app_context():
        User.query.filter_by(email='dup@t.com').delete()
        db.session.add(User(username='e', email='dup@t.com', password='p', confirmed=True))
        db.session.commit()
    response = client.post('/auth/signup', data={
        'username': 'n', 'email': 'dup@t.com', 'password': 'p', 'confirm_password': 'p'
    }, follow_redirects=True)
    assert "이미 사용 중" in response.get_data(as_text=True)