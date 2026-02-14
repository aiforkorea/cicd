# apps/provider/views.py
import os, docker
from flask import Blueprint, render_template, request, flash, redirect, url_for
from apps.provider import provider
from apps.auth.decorators import permission_required
@provider.route('/upload', methods=['GET', 'POST'])
@permission_required('service_upload')
def upload_ai():
    if request.method == 'POST':
        file = request.files.get('ai_code')
        if not file or file.filename == '':
            flash('파일을 선택해주세요.')
            return redirect(request.url)
        # 1. 파일 저장
        save_path = os.path.join('uploads', file.filename)
        file.save(save_path)
        # 2. 도커 실험실 가동
        client = docker.from_env()
        try:
            # 우리 서버의 uploads 폴더를 도커의 /app 폴더로 연결
            abs_path = os.path.abspath('uploads')
            # 격리된 환경에서 실행!
            container_output = client.containers.run(
                image="python:3.12-slim",
                command=f"python /app/{file.filename}",
                volumes={abs_path: {'bind': '/app', 'mode': 'ro'}},
                mem_limit="64m",
                network_disabled=True,
                remove=True,
                stderr=True,  # 에러 메시지도 캡처
                stdout=True,
            )
            flash(f"테스트 성공! 결과: {container_output.decode('utf-8')}", "success")
        except Exception as e:
            flash(f"보안 위험 또는 에러 발생: {str(e)}", "danger")
            if os.path.exists(save_path):
                os.remove(save_path) # 실패한 파일은 삭제

    return render_template('provider/upload.html')
