from flowork.models import db, User, Brand, Store

def authenticate_user(username, password, brand_id=None):
    if not brand_id:
        if username == 'superadmin':
            return User.query.filter_by(is_super_admin=True, username='superadmin').first()
        return None

    user = User.query.filter_by(
        username=username, 
        brand_id=brand_id, 
        is_super_admin=False
    ).first()

    if user and user.store_id:
        if not user.store or not user.store.is_approved or not user.store.is_active:
            return None 

    if user and user.check_password(password):
        return user
    
    return None

def create_brand_and_admin(brand_name, password):
    try:
        new_brand = Brand(brand_name=brand_name)
        db.session.add(new_brand)
        db.session.flush()

        hq_user = User(
            username='admin',
            brand_id=new_brand.id,
            store_id=None,
            is_admin=True,
            is_super_admin=False
        )
        hq_user.set_password(password)
        db.session.add(hq_user)
        db.session.commit()
        return True, None
    except Exception as e:
        db.session.rollback()
        return False, str(e)

def request_store_registration(brand_id, store_id, manager_name, username, password):
    try:
        store = db.session.get(Store, store_id)
        if not store or store.brand_id != brand_id:
            return False, "잘못된 매장 정보입니다."
        
        if store.is_registered:
            return False, "이미 가입 요청된 매장입니다."

        existing_user = User.query.filter_by(username=username, brand_id=brand_id).first()
        if existing_user:
            return False, "이미 사용 중인 아이디입니다."

        new_user = User(
            username=username,
            brand_id=brand_id,
            store_id=store_id,
            is_admin=True,
            is_super_admin=False
        )
        new_user.set_password(password)
        db.session.add(new_user)
        
        store.is_registered = True
        store.manager_name = manager_name
        
        db.session.commit()
        return True, None
    except Exception as e:
        db.session.rollback()
        return False, str(e)

def change_user_password(user, current_pw, new_pw):
    if not user.check_password(current_pw):
        return False, "현재 비밀번호가 일치하지 않습니다."
    
    user.set_password(new_pw)
    db.session.commit()
    return True, None

def get_all_brands():
    return Brand.query.order_by(Brand.brand_name).all()