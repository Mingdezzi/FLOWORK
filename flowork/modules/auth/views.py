from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from flowork.modules.auth import auth_bp
from flowork.modules.auth.services import authenticate_user, create_brand_and_admin, request_store_registration, get_all_brands

@auth_bp.route('/login', methods=['GET', 'POST'])
def login_view():
    if current_user.is_authenticated:
        return redirect(url_for('ui.home')) 

    if request.method == 'POST':
        brand_id_str = request.form.get('brand_id')
        username = request.form.get('username')
        password = request.form.get('password')
        
        try:
            brand_id = int(brand_id_str) if brand_id_str else None
            user = authenticate_user(username, password, brand_id)
            
            if user:
                login_user(user)
                flash('로그인 성공!', 'success')
                next_page = request.args.get('next')
                return redirect(next_page or url_for('ui.home'))
            else:
                flash('로그인 실패. 정보를 확인하세요. (승인 대기 매장일 수 있습니다)', 'error')
                
        except ValueError:
            flash('잘못된 요청입니다.', 'error')

    brands = get_all_brands()
    return render_template('login.html', brands=brands)

@auth_bp.route('/logout')
def logout_view():
    logout_user()
    flash('로그아웃 되었습니다.', 'info')
    return redirect(url_for('auth.login_view'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register_brand_view():
    if current_user.is_authenticated:
        return redirect(url_for('ui.home'))
        
    if request.method == 'POST':
        brand_name = request.form.get('brand_name')
        password = request.form.get('password')

        if not all([brand_name, password]):
            flash('모든 항목을 입력하세요.', 'error')
        else:
            success, msg = create_brand_and_admin(brand_name, password)
            if success:
                flash("브랜드 등록 성공! 로그인하세요.", 'success')
                return redirect(url_for('auth.login_view'))
            else:
                flash(f'오류 발생: {msg}', 'error')

    return render_template('register.html')

@auth_bp.route('/register_store', methods=['GET', 'POST'])
def register_store_view():
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
                flash('모든 항목을 입력하세요.', 'error')
            else:
                success, msg = request_store_registration(brand_id, store_id, manager_name, username, password)
                if success:
                    flash('가입 요청 완료. 승인 후 로그인 가능합니다.', 'success')
                    return redirect(url_for('auth.login_view'))
                else:
                    flash(msg, 'error')
        except ValueError:
            flash('입력 값이 올바르지 않습니다.', 'error')

    brands = get_all_brands()
    return render_template('register_store.html', brands=brands)