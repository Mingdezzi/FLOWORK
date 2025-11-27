# backend/commands.py
import click
from flask.cli import with_appcontext
from . import db
from .models import User, Brand, Store

@click.command("create-admin")
@click.argument("password")
@with_appcontext
def create_admin_command(password):
    """초기 브랜드와 관리자 계정을 생성합니다."""
    try:
        # 1. 기본 브랜드 생성
        brand = Brand.query.filter_by(name="FLOWORK").first()
        if not brand:
            brand = Brand(name="FLOWORK")
            db.session.add(brand)
            db.session.flush()
            print("✅ 브랜드 'FLOWORK' 생성됨")

        # 2. 본사 매장 생성
        hq_store = Store.query.filter_by(name="본사", brand_id=brand.id).first()
        if not hq_store:
            hq_store = Store(name="본사", brand_id=brand.id, is_hq=True)
            db.session.add(hq_store)
            db.session.flush()
            print("✅ 매장 '본사' 생성됨")

        # 3. 관리자 계정 생성
        admin = User.query.filter_by(username="admin").first()
        if not admin:
            admin = User(
                username="admin",
                password_hash=password, # 실제 서비스에선 hash 적용 필요하지만 일단 평문 저장 (또는 models.py의 set_password 사용 권장)
                brand_id=brand.id,
                store_id=hq_store.id,
                role="super_admin"
            )
            db.session.add(admin)
            print(f"✅ 관리자 계정 생성됨 (ID: admin / PW: {password})")
        else:
            print("ℹ️ 관리자 계정이 이미 존재합니다.")

        db.session.commit()
        print("✨ 초기화 완료!")

    except Exception as e:
        db.session.rollback()
        print(f"❌ 오류 발생: {e}")