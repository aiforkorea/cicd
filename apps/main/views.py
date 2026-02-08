# apps/main/views.py
from flask import render_template, current_app, request
#from flask_login import login_required, current_user
from apps.main import main
import uuid
from flask import redirect, url_for, flash
from flask_login import login_required, current_user
from . import main                      # 현재 폴더의 Blueprint 객체
from apps.extensions import db          # 공통 DB 도구
from apps.dbmodels import Payment       # 영수증 모델
from apps.auth.utils import upgrade_user_to_premium  # 등급 올리기 요정

@main.route("/")
def index():
    # INFO 레벨 로그: 정상적인 동작을 기록
    current_app.logger.info("메인 페이지에 접근했습니다.")
    # DEBUG 레벨 로그: 개발 및 디버깅용 메시지
    # (개발 환경에서만 콘솔에 출력, 배포 환경에서는 기록되지 않음)
    current_app.logger.debug("사용자 IP: %s", request.remote_addr)
    try:
        # 예시: 파일을 열다가 오류가 발생한 상황
        # open('non_existent_file.txt', 'r')
        pass # 현재는 에러가 발생하지 않으므로 pass
    except Exception as e:
        # ERROR 레벨 로그: 예외 발생 시 기록
        current_app.logger.error("파일 처리 중 오류 발생: %s", str(e))
        # WARNING 레벨 로그: 잠재적 문제점을 기록
        current_app.logger.warning("오류 발생으로 인해 특정 기능이 제대로 동작하지 않을 수 있습니다.")
#    if current_user.is_authenticated:
#        return render_template("main/index.html", username=current_user.username)
    return render_template("main/index.html")
@main.route("/services")
def services():
    # pass 대신에 뭐라도 화면을 보여줘야 합니다.
    return "<h1>홈페이지 서비스 페이지입니다</h1>" 
    # 또는 실제 템플릿이 있다면: return render_template("services.html")

@main.route("/simulate-payment", methods=['POST'])
@login_required
def simulate_payment():
    # 1. 가짜 결제 기록 생성
    new_payment = Payment(
        user_id=current_user.id,
        amount=9900,
        merchant_uid=f"TEST_{uuid.uuid4().hex[:8]}",
        status='paid'
    )
    db.session.add(new_payment)
    
    # 2. 요정 소환해서 등급 올리기
    upgrade_user_to_premium(current_user)
    
    db.session.commit() # 장부에 최종 기록!
    flash("결제가 성공했습니다! 이제 프리미엄 회원입니다.", "success")
    return redirect(url_for('main.index'))


