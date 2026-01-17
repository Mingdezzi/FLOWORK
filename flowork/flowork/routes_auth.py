from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from flowork.models import db, Brand, Store, User

# 'auth'라는 이름의 새 블루프린트 생성
auth_bp = Blueprint('auth', __name__, template_folder='../templates')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """로그인 페이지"""
    if current_user.is_authenticated:
        return redirect(url_for('ui.home')) # 이미 로그인했다면 홈으로

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        # 유저가 존재하고, 비밀번호가 맞는지 확인
        if user and user.check_password(password):
            login_user(user) # Flask-Login을 통해 세션에 로그인
            flash('로그인 성공!', 'success')
            # 로그인이 필요한 페이지가 있었다면 거기로, 아니면 홈으로
            next_page = request.args.get('next')
            return redirect(next_page or url_for('ui.home'))
        else:
            flash('로그인 실패. 아이디나 비밀번호를 확인하세요.', 'error')

    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    """로그아웃"""
    logout_user() # Flask-Login을 통해 세션에서 로그아웃
    flash('로그아웃 되었습니다.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    (테스트용) 최초의 브랜드/매장/유저를 생성하는 회원가입 페이지.
    운영 시에는 관리자 기능으로 옮겨야 합니다.
    """
    if current_user.is_authenticated:
        return redirect(url_for('ui.home'))
        
    if request.method == 'POST':
        try:
            brand_name = request.form.get('brand_name')
            store_name = request.form.get('store_name')
            username = request.form.get('username')
            password = request.form.get('password')

            if not all([brand_name, store_name, username, password]):
                flash('모든 항목을 입력해야 합니다.', 'error')
                return render_template('register.html')

            # 1. 브랜드 생성
            new_brand = Brand(brand_name=brand_name)
            db.session.add(new_brand)
            db.session.flush() # brand.id를 미리 가져오기 위해

            # 2. 매장 생성 (이 브랜드를 참조)
            new_store = Store(
                store_name=store_name,
                brand_id=new_brand.id,
                is_hq=True # 최초 매장을 본사로 설정
            )
            db.session.add(new_store)
            db.session.flush() # store.id를 미리 가져오기 위해

            # 3. 유저 생성 (이 매장을 참조)
            new_user = User(
                username=username,
                store_id=new_store.id,
                is_admin=True # 최초 유저를 관리자로 설정
            )
            new_user.set_password(password) # 비밀번호 암호화
            db.session.add(new_user)

            db.session.commit() # 모든 변경사항 커밋

            flash('회원가입 성공! 생성된 아이디로 로그인하세요.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            print(f"Error during registration: {e}")
            flash(f'회원가입 중 오류 발생 (아이디 중복 등): {e}', 'error')

    return render_template('register.html')