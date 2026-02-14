# tests/test_main.py
import pytest, io
from apps.dbmodels import User, Role, Payment, Permission
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

def test_expert_permission(client, app):
    """EXPERT 권한이 없는 유저가 전문가 전용 기능을 쓰려고 할 때 차단되는지 테스트"""
    with app.app_context():
        # 1. 일반 유저 생성 (EXPERT 권한 없음)
        User.query.filter_by(email='normal@test.com').delete()
        user_role = Role.query.filter_by(name='USER').first()
        # 1.1 일반 유저 객체 생성        
        user = User(username='normal', email='normal@test.com', password='p1', confirmed=True)
        # 1.2 장부에 먼저 추가(session에 넣기)
        db.session.add(user)
        # 1.3 그 다음에 이름표 달기(USER 역할만 제공, EXPERT 역할은 제공안함)
        if user_role:
            user.roles.append(user_role)
        db.session.commit()

    # 2. 일반 유저로 로그인
    client.post('/auth/login', data={'email': 'normal@test.com', 'password': 'p1'}, follow_redirects=True)
    # 3. [가정] 전문가 전용 페이지 접속 시도 'auth/expert-only'라고 할 때
    # (실제 뷰함수에 @permission_required('expert_service')가 달려있어야 함)
    response = client.get('/auth/expert-only') 
    
    # 4. 권한이 없으므로 403(Forbidden) 에러가 나야 성공!
    # (아직 /expert 페이지를 안 만들었다면 404가 날 수 있으니 나중에 페이지 만들고 확인하세요)
    assert response.status_code in [403, 404] 

##
def test_login_failure_invalid_password(client, app):
    """비밀번호 틀렸을 때 실패하는지 확인"""
    with app.app_context():
        User.query.filter_by(email='f@t.com').delete()
        db.session.add(User(username='f', email='f@t.com', password='correct', confirmed=True))
        db.session.commit()
    
    response = client.post('/auth/login', data={'email': 'f@t.com', 'password': 'wrong'}, follow_redirects=True)
    assert "확인 필요" in response.get_data(as_text=True)

def test_logout_process(auth_client):
    """테스트 6: 로그아웃하면 비밀 페이지에 못 들어가는지 확인"""
    # 1. 이미 로그인된 상태(auth_client)에서 로그아웃 버튼 클릭
    auth_client.get('/auth/logout', follow_redirects=True)
    
    # 2. 로그아웃 후 전문가 전용 페이지(/auth/expert-only)에 다시 접속 시도
    response = auth_client.get('/auth/expert-only')
    
    # 3. 로그인이 풀렸으므로 로그인 페이지로 쫓겨나거나(302), 접근 거부되어야 함
    # 보통 flask-login은 로그인 안 된 유저를 로그인 페이지로 리다이렉트(302) 시킵니다.
    assert response.status_code in [302, 401]

def test_signup_duplicate_email(client, app):
    """테스트 7: 이미 가입된 이메일로 또 가입하려고 할 때 막아주는지 확인"""
    with app.app_context():
        # 1. 미리 'king@test.com'이라는 유저를 만들어 둠
        User.query.filter_by(email='king@test.com').delete()
        user = User(username='king', email='king@test.com', password='p1', confirmed=True)
        db.session.add(user)
        db.session.commit()

    # 2. 똑같은 이메일로 다시 가입 시도
    response = client.post('/auth/signup', data={
        'username': 'fake_king',
        'email': 'king@test.com',
        'password': 'p2',
        'confirm_password': 'p2'
    }, follow_redirects=True)

    # 3. 화면에 "이미 사용 중" 또는 "이미 가입된"이라는 경고 문구가 나와야 함
    assert "이미 사용 중" in response.get_data(as_text=True) or "이미 가입된" in response.get_data(as_text=True)

def test_password_reset_request(client, app):
    """테스트 8: 비밀번호 재설정 메일이 잘 가는지 확인"""
    with app.app_context():
        # 1. 비밀번호를 바꿀 유저 준비
        User.query.filter_by(email='forgot@test.com').delete()
        user = User(username='lost', email='forgot@test.com', password='old_password', confirmed=True)
        db.session.add(user)
        db.session.commit()

    with mail.record_messages() as outbox:
        # 2. "비밀번호 잊어버렸어요" 페이지에서 이메일 제출
        client.post('/auth/reset-password-request', data={'email': 'forgot@test.com'}, follow_redirects=True)
        
        # 3. 실제로 재설정 링크가 담긴 메일이 1통 발송되었는지 확인
        assert len(outbox) == 1
        assert "비밀번호 재설정" in outbox[0].subject

def test_simulate_payment_success(auth_client, app): # auth, db_session 대신 auth_client, app 사용
    """결제 성공 시나리오 테스트"""
    # 1. auth_client는 이미 'testuser'로 로그인된 상태입니다. (conftest.py 참고)
    with app.app_context():
        user = User.query.filter_by(email='test@test.com').first()
        # 처음에는 전문가 권한이 없는지 확인
        assert user.can('expert_service') is False
    # 2. 결제 시뮬레이션 버튼 클릭 (POST 요청)
    response = auth_client.post('/simulate-payment', follow_redirects=True)
    # 3. 결과 확인
    assert response.status_code == 200
    assert "결제가 성공했습니다!" in response.get_data(as_text=True)
    # 4. DB 확인: 권한 및 영수증 체크
    with app.app_context():
        # 데이터베이스의 최신 상태를 확인하기 위해 다시 조회
        user = User.query.filter_by(email='test@test.com').first()
        assert user.can('expert_service') is True
        
        payment = Payment.query.filter_by(user_id=user.id).first()
        assert payment is not None
        assert payment.amount == 9900
        assert payment.status == 'paid'

def test_simulate_payment_fail_not_logged_in(client):
    """로그인 안 한 상태에서 결제 시도 시 실패 테스트"""
    # 로그인하지 않고 바로 결제 주소로 POST 요청
    response = client.post('/simulate-payment', follow_redirects=True)
    
    # 로그인 페이지로 리다이렉트 되거나 '로그인이 필요합니다' 메시지가 떠야 함
    assert "로그인이 필요합니다" in response.get_data(as_text=True)

def test_upload_page_access_denied_for_normal_user(auth_client):
    """일반 유저(USER 역할)는 업로드 페이지에 접근할 수 없어야 함 (403 예상)"""
    response = auth_client.get('/provider/upload')
    # permission_required 데코레이터가 실패 시 403을 주거나 
    # 혹은 메인으로 리다이렉트 시키는지 확인하세요.
    assert response.status_code in [403, 302]

def test_upload_page_access_granted_for_provider(client, app):
    """PROVIDER 권한을 가진 유저는 업로드 페이지에 접근 가능해야 함"""
    with app.app_context():
        # 1. 역할 가져오기
        provider_role = Role.query.filter_by(name='PROVIDER').first()
        
        # 2. PROVIDER 유저 생성
        user = User(username='provider1', email='provider@test.com',
                    password='password123', confirmed=True)
        
        if provider_role:
            user.roles.append(provider_role)
        
        # 3. DB 저장 (app.extensions를 복잡하게 부를 필요 없이 db 직접 사용)
        db.session.add(user)
        db.session.commit()

    # 4. 로그인 요청
    client.post('/auth/login', data={
        'email': 'provider@test.com',
        'password': 'password123'
    }, follow_redirects=True)

    # 5. 페이지 접근 확인
    response = client.get('/provider/upload')
    assert response.status_code == 200
    
def test_ai_code_upload_and_docker_run(client, app):
    """실제 파일 업로드 및 도커 실행 결과 테스트"""
    # PROVIDER 로그인 과정 (위와 동일하게 권한 부여 필요)
    with app.app_context():
        from apps.extensions import db
        provider_role = Role.query.filter_by(name='PROVIDER').first()
        p_user = User(username='dev_user', email='dev@test.com', password='password123', confirmed=True)
        p_user.roles.append(provider_role)
        db.session.add(p_user)
        db.session.commit()

    client.post('/auth/login', data={'email': 'dev@test.com', 'password': 'password123'}, follow_redirects=True)

    # 가짜 파이썬 파일 생성 (메모리 상에서 생성)
    data = {
        'ai_code': (io.BytesIO(b"print('Hello from Docker!')"), 'test_script.py'),
    }

    # 파일 업로드 요청 (CSRF 토큰 처리는 테스트 클라이언트에서 보통 무시되거나 수동 추가 필요)
    # 만약 CSRF 에러가 나면 @csrf.exempt를 잠시 쓰거나 테스트 설정에서 WT_CSRF_ENABLED = False 확인
    response = client.post('/provider/upload', data=data, content_type='multipart/form-data', follow_redirects=True)

    assert response.status_code == 200
    assert "테스트 성공!" in response.get_data(as_text=True)
    assert "Hello from Docker!" in response.get_data(as_text=True)
