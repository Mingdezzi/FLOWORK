from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from flowork.models import db, Brand, Store, User 

auth_bp = Blueprint('auth', __name__, template_folder='../templates')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """(수정) 로그인 페이지 - 브랜드 선택 드롭다운 포함"""
    if current_user.is_authenticated:
        return redirect(url_for('ui.home')) 

    if request.method == 'POST':
        brand_id_str = request.form.get('brand_id')
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = None
        
        if not brand_id_str:
            # 케이스 1: 슈퍼 관리자
            if username == 'superadmin':
                user = User.query.filter_by(is_super_admin=True, username='superadmin').first()
        else:
            # 케이스 2: 본사/매장 계정
            try:
                brand_id = int(brand_id_str)
                user = User.query.filter_by(
                    username=username, 
                    brand_id=brand_id, 
                    is_super_admin=False
                ).first()
                
                # [수정] '매장 계정'일 경우 (store_id가 있을 경우)에만 승인/활성 여부 체크
                if user and user.store_id: 
                    if not user.store or not user.store.is_approved or not user.store.is_active:
                        flash(f"'{user.store.store_name}' 매장이 승인 대기 중이거나 비활성화 상태입니다. 본사에 문의하세요.", 'error')
                        user = None # 로그인 차단
                    
            except ValueError:
                flash('잘못된 브랜드 값입니다.', 'error')

        if user and user.check_password(password):
            login_user(user) 
            flash('로그인 성공!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('ui.home'))
        elif user:
             # 유저는 찾았으나 (승인 대기 등) 로그인이 차단된 경우는 위에서 flash 처리됨
             pass
        else:
            flash('로그인 실패. 브랜드, 아이디 또는 비밀번호를 확인하세요.', 'error')

    brands = Brand.query.order_by(Brand.brand_name).all()
    return render_template('login.html', brands=brands)


@auth_bp.route('/logout')
def logout():
    """로그아웃"""
    logout_user() 
    flash('로그아웃 되었습니다.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register_brand():
    """
    (수정) '최초 브랜드 등록' 페이지.
    브랜드와 해당 브랜드의 '본사 관리자 (admin)' 계정을 생성합니다.
    """
    if current_user.is_authenticated:
        return redirect(url_for('ui.home'))
        
    if request.method == 'POST':
        try:
            brand_name = request.form.get('brand_name')
            password = request.form.get('password')
            username = 'admin' # (고정)

            if not all([brand_name, password]):
                flash('브랜드명과 비밀번호를 모두 입력해야 합니다.', 'error')
                return render_template('register.html')

            # 1. 브랜드 생성
            new_brand = Brand(brand_name=brand_name)
            db.session.add(new_brand)
            db.session.flush() 

            # 2. '본사 관리자' User 생성
            hq_user = User(
                username=username,
                brand_id=new_brand.id,
                store_id=None,
                is_admin=True, # 본사 '관리자'
                is_super_admin=False
            )
            hq_user.set_password(password)
            db.session.add(hq_user)

            db.session.commit() 

            flash(f"'{brand_name}' 브랜드 등록 성공! 'admin' 아이디로 로그인하세요.", 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            print(f"Error during brand registration: {e}")
            flash(f'등록 중 오류 발생 (브랜드명 중복 등): {e}', 'error')

    return render_template('register.html')


@auth_bp.route('/register_store', methods=['GET', 'POST'])
def register_store():
    """
    [신규] (요청사항 2) '매장 가입 요청' 페이지.
    매장 담당자가 브랜드/매장을 선택하고 계정 정보를 입력합니다.
    """
    if current_user.is_authenticated:
        return redirect(url_for('ui.home'))
        
    if request.method == 'POST':
        try:
            brand_id = int(request.form.get('brand_id'))
            store_id = int(request.form.get('store_id'))
            manager_name = request.form.get('manager_name', '').strip()
            username = request.form.get('username', '').strip()
            password = request.form.get('password')

            if not all([brand_id, store_id, manager_name, username, password]):
                flash('모든 항목을 입력해야 합니다.', 'error')
                return redirect(url_for('auth.register_store'))

            # 1. Store 유효성 검증
            store = db.session.get(Store, store_id)
            if not store or store.brand_id != brand_id:
                flash('선택한 매장이 잘못되었거나 해당 브랜드 소속이 아닙니다.', 'error')
                return redirect(url_for('auth.register_store'))
            
            # 2. 이미 가입 신청(등록)되었는지 확인
            if store.is_registered:
                flash(f"'{store.store_name}' 매장은 이미 가입 요청이 완료되었습니다. 본사 승인을 기다리세요.", 'warning')
                return redirect(url_for('auth.login'))

            # 3. User ID가 브랜드 내에서 중복되는지 확인 (UniqueConstraint)
            existing_user = User.query.filter_by(
                username=username, 
                brand_id=brand_id
            ).first()
            if existing_user:
                flash(f"아이디 '{username}'(은)는 해당 브랜드에서 이미 사용 중입니다.", 'error')
                return redirect(url_for('auth.register_store'))

            # 4. 매장 사용자 계정 생성 (is_admin=True, 매장 관리자)
            new_user = User(
                username=username,
                brand_id=brand_id,
                store_id=store_id,
                is_admin=True, # 매장 관리자
                is_super_admin=False
            )
            new_user.set_password(password)
            db.session.add(new_user)
            
            # 5. Store 상태 업데이트 (가입 신청 완료)
            store.is_registered = True
            store.manager_name = manager_name
            # (is_approved는 False인 상태로 본사 승인을 기다림)

            db.session.commit() 

            flash('매장 가입 요청이 완료되었습니다. 본사 관리자의 승인 후 로그인할 수 있습니다.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            print(f"Error during store registration: {e}")
            flash(f'가입 요청 중 오류 발생: {e}', 'error')

    # GET 요청: 브랜드 목록을 템플릿에 전달
    brands = Brand.query.order_by(Brand.brand_name).all()
    return render_template('register_store.html', brands=brands)

@auth_bp.route('/change_password', methods=['POST'])
@login_required
def change_password():
    """[신규 2-5] 비밀번호 변경 API"""
    data = request.json
    current_pw = data.get('current_password')
    new_pw = data.get('new_password')
    
    if not current_pw or not new_pw:
        return jsonify({'status': 'error', 'message': '입력 값이 부족합니다.'}), 400
        
    if not current_user.check_password(current_pw):
        return jsonify({'status': 'error', 'message': '현재 비밀번호가 일치하지 않습니다.'}), 400
        
    current_user.set_password(new_pw)
    db.session.commit()
    
    return jsonify({'status': 'success', 'message': '비밀번호가 변경되었습니다.'})