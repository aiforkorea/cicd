# apps/utils.py (새로 만들기)
from apps.extensions import db
from apps.dbmodels import Role, Permission, User

def seed_db(app):
    """데이터베이스에 기본 권한과 역할을 자동으로 채워주는 함수"""
    
    # 1. 우리가 쓸 권한(Permission) 목록
    perms = {
        'menu_view': '메뉴 보기 권한',
        'api_call': 'API 호출 권한',
        'admin_access': '관리자 페이지 접근 권한',
        'expert_service': '전문가 서비스'
    }
    
    # 2. 권한 테이블 채우기
    perm_objs = {}
    for name, desc in perms.items():
        p = Permission.query.filter_by(name=name).first()
        if not p:
            p = Permission(name=name, description=desc)
            db.session.add(p)
        perm_objs[name] = p
    
    db.session.commit() # 권한 먼저 저장!

    # 3. 역할(Role) 정의 및 권한 연결
    # 역할이름: [가져갈 권한들]
    roles_data = {
        'USER': ['menu_view', 'api_call'],
        'EXPERT': ['menu_view', 'api_call', 'expert_service'],
        'ADMIN': ['menu_view', 'api_call', 'expert_service', 'admin_access']
    }

    for rname, pnames in roles_data.items():
        role = Role.query.filter_by(name=rname).first()
        if not role:
            role = Role(name=rname)
            db.session.add(role)
        
        # 해당 역할에 권한들 쏙쏙 넣어주기
        role.permissions = [perm_objs[pn] for pn in pnames]
    
    db.session.commit() # 역할 저장!
    print("기본 권한 및 역할 설정 완료!")

    # 관리자 계정 생성 부분 수정
    admin_email = app.config.get('ADMIN_EMAIL')
    if admin_email:
        admin = User.query.filter_by(email=admin_email).first()
        if not admin:
            admin_role = Role.query.filter_by(name='ADMIN').first()
            user_role = Role.query.filter_by(name='USER').first() # 일반 유저 역할도 같이 부여해볼까요?
            
            new_admin = User(
                username=app.config.get('ADMIN_USERNAME'),
                email=admin_email,
                password=app.config.get('ADMIN_PASSWORD'),
                confirmed=True
            )
            # [수정] 역할들을 리스트에 추가
            new_admin.roles.append(admin_role)
            new_admin.roles.append(user_role)
            
            db.session.add(new_admin)
            db.session.commit()
