# apps/auth/views.py
from datetime import datetime
from flask import current_app, render_template, flash, url_for, redirect, request
from flask_login import current_user, login_user, logout_user
from apps.auth.utils import confirm_token, generate_token, send_email, oauth
from apps.extensions import db
from apps.dbmodels import User, Role
from .forms import ResetPasswordForm, ResetPasswordRequestForm, SignUpForm, LoginForm
from . import auth  # 현재 패키지(__init__.py)의 auth Blueprint 객체 임포트
from apps.auth.decorators import permission_required # 경비원 임포트
from flask_login import login_required

# index 엔드포인트
@auth.route("/")
def index():
    return render_template("auth/index.html")

# signup 엔드포인트
@auth.route("/signup", methods=["GET", "POST"])
def signup():
    form = SignUpForm()
    if form.validate_on_submit():
        # 1. 새 사용자 객체 생성
        user = User(
            username=form.username.data, email=form.email.data,
            password=form.password.data, confirmed=False # 기본값 미인증
        )

        # [추가] 2. 'USER' 역할(이름표)을 찾아서 달아주기
        user_role = Role.query.filter_by(name='USER').first()
        if user_role:
            user.roles.append(user_role) # 다대다 관계이므로 append 사용!

        db.session.add(user)
        db.session.commit()
        # 토큰 생성 및 메일 발송
        token = generate_token(user.email, salt='email-confirm-salt')
        confirm_url = url_for('auth.confirm_email', token=token, _external=True)
        send_email(
            subject="[서비스] 이메일 주소를 인증해주세요",
            to=user.email,
            template="auth/email/confirm", # templates/auth/email/confirm.html 필요
            username=user.username,
            confirm_url=confirm_url
        )
        flash("가입 확인 메일이 발송되었습니다. 이메일을 확인해주세요.", "info")
        return redirect(url_for("auth.login"))
    return render_template("auth/signup.html", form=form)

# login 엔드포인트
@auth.route("/login",methods=["GET", "POST"])     
def login():
    current_app.logger.info("메인 페이지에 접근했습니다.")
    current_app.logger.debug("사용자 IP: %s", request.remote_addr)
    form = LoginForm()    # LoginForm 회원로그인 객체 form 생성
    if form.validate_on_submit():
        # 사용자가 입력한 이메일 값을 DEBUG 레벨로 로깅
        current_app.logger.debug("사용자가 입력한 이메일: %s", form.email.data)
        user = User.query.filter_by(email=form.email.data).first()
        # DB에 사용자 존재 및 비번 일치하면
        if user is not None and user.verify_password(form.password.data): 
            if not user.confirmed:
                flash("이메일 인증이 필요합니다. 메일 확인 필요", "warning")
                return redirect(url_for("auth.login"))
            # 사용자 정보 세션 저장
            login_user(user, remember=form.remember.data)
            send_email("[보안] 로그인 알림", user.email, "auth/email/login_notification",
                       username=user.username, login_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                       ip_address=request.remote_addr, user_agent=request.user_agent.string)
            return redirect(url_for("main.index"))   # main.index로 이동
        # 로그인 실패 메시지
        flash("이메일 주소 및 비번 확인 필요")
    return render_template("auth/login.html",form=form)

# logout 엔드포인트 
@auth.route("/logout")     
def logout():
    # 사용자 로그아웃
    logout_user()
    return redirect(url_for("auth.login"))

@auth.route('/confirm/<token>')
def confirm_email(token):
    email = confirm_token(token, salt='email-confirm-salt')
    if not email:
        flash('인증 링크가 만료되었거나 잘못되었습니다.', 'danger')
        return redirect(url_for('main.index'))
    user = User.query.filter_by(email=email).first_or_404()
    if user.confirmed:
        flash('이미 인증된 계정입니다.', 'success')
    else:
        user.confirmed = True
        user.confirmed_at = datetime.now()
        db.session.commit()
        flash('이메일 인증이 완료되었습니다!', 'success')
    return redirect(url_for('main.index'))

@auth.route('/reset-password-request', methods=['GET', 'POST'])
def reset_password_request():
    # 1. 이미 로그인한 사용자가 이 페이지에 오면 홈으로 보냅니다.
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        # 2. 입력받은 이메일로 사용자를 찾습니다.
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            # 3. 1회용 보안 토큰 생성 (salt를 'password-reset-salt'로 지정)
            token = generate_token(user.email, salt='password-reset-salt')
            # 4. 사용자가 클릭할 전체 URL 생성 (_external=True 필수!)
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            # 5. 이메일 발송
            send_email(
                subject="[MyService] 비밀번호 재설정 요청", to=user.email, 
                template="auth/email/reset_password",
                username=user.username, 
                reset_url=reset_url
            )
        # 6. 보안 팁: 실제 이메일이 있든 없든 같은 메시지를 보여줌. 특정 이메일 가입 여부 확인 못하게 하기 위함
        flash('비밀번호 재설정 지침이 담긴 이메일을 보냈습니다. 메일함을 확인해 주세요.', 'info')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password_request.html', form=form)

# 2. 실제 비밀번호 변경 페이지 (메일 링크 클릭 시 접속)
@auth.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    email = confirm_token(token, salt='password-reset-salt')
    if not email:
        flash('유효하지 않거나 만료된 링크입니다.', 'danger')
        return redirect(url_for('auth.login'))
    user = User.query.filter_by(email=email).first_or_404()
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.password = form.password.data # 모델의 setter에 의해 자동 해싱
        db.session.commit()
        # 보안 알림 메일 발송
        send_email(
            subject="[보안] 비밀번호가 성공적으로 변경되었습니다",
            to=user.email,
            template="auth/email/password_changed",
            username=user.username,
            change_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            user_agent=request.user_agent.string
        )
        flash('비밀번호가 변경되었습니다. 이제 새 비밀번호로 로그인하세요.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)

@auth.route('/login/google')
def google_login():
    # 구글 로그인 페이지로 보내버리기
    redirect_uri = url_for('auth.google_authorize', _external=True)
    print(f"DEBUG: 생성된 리디렉션 주소는 -> {redirect_uri}") # 터미널 확인용
    return oauth.google.authorize_redirect(redirect_uri)

@auth.route('/login/google/callback')
def google_authorize():
    # 구글이 보낸 증명서를 확인하기
    token = oauth.google.authorize_access_token()
    user_info = token.get('userinfo')
    
    # DB에서 이 이메일의 사용자가 있는지 확인
    user = User.query.filter_by(email=user_info['email']).first()
    
    if not user:
        # 1. 처음 온 사람이라면 회원가입 시켜주기
        user = User(username=user_info['name'], email=user_info['email'], confirmed=True,
                confirmed_at=datetime.now() # 인증 시간 기록
                # password_hash는 None으로 들어감 (nullable=True이므로 허용됨)  
        )

        # [추가] 2. 구글 사용자에게도 'USER' 이름표 달아주기   다대다 관계
        user_role = Role.query.filter_by(name='USER').first()
        if user_role:
            user.roles.append(user_role)

        db.session.add(user)
        db.session.commit()
    
    login_user(user)
    flash(f"{user.username}님, 구글 계정으로 로그인되었습니다!", "success")
    return redirect(url_for('main.index'))

@auth.route('/expert-only')
@login_required # 일단 로그인은 해야 하고
@permission_required('expert_service') # '전문가 서비스' 이름표가 있어야 통과!
def expert_page():
    return "<h1>환영합니다, 전문가님!</h1><p>이곳은 전문가 전용 비밀 페이지입니다.</p>"

