# apps/run.py
import os
from apps import create_app

app = create_app()

if __name__ == '__main__':
    # 1. 환경 변수 확인 (Render용인지 로컬용인지)
    port = int(os.environ.get("PORT", 5000))
    
    # 2. 로컬 테스트 환경인지 Render 배포 환경인지에 따라 다르게 설정
    # 로컬에서 실행할 때 (환경변수 PORT가 없는 경우가 많음)
    if os.environ.get("RENDER") is None: 
        print("--- 로컬 개발 모드로 실행 중 (No Reload) ---")
        app.run(
            host="127.0.0.1", 
            port=5000, 
            debug=True, 
            use_reloader=False  # <--- 이 부분이 핵심! 업로드 시 서버 재시작 방지
        )
    else:
        # Render.com 배포 환경
        print("--- Render 배포 모드로 실행 중 ---")
        app.run(host="0.0.0.0", port=port, debug=False)
