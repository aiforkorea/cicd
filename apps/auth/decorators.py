# apps/auth/decorators.py
from functools import wraps
from flask import abort
from flask_login import current_user

def permission_required(permission_name):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 현재 로그인한 유저가 해당 권한이 있는지 확인
            if not current_user.can(permission_name):
                abort(403) # "권한 없음" 에러 발생!
            return f(*args, **kwargs)
        return decorated_function
    return decorator
