import json
import traceback
from flask import render_template, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from sqlalchemy.orm import selectinload

from flowork.models import db, Product, Setting
from . import ui_bp

@ui_bp.route('/')
@login_required
def home():
    if current_user.is_super_admin:
        flash("슈퍼 관리자 계정입니다. (시스템 설정)", "info")
        return redirect(url_for('ui.setting_page'))
        
    return render_template('index.html', active_page='home')

@ui_bp.route('/search')
@login_required
def search_page():
    if current_user.is_super_admin:
        abort(403, description="슈퍼 관리자는 상품 검색을 사용할 수 없습니다.")

    try:
        current_brand_id = current_user.current_brand_id
        
        # [수정] DB에서 '품목(item_category)'을 조회하여 동적으로 버튼 구성
        # 1. DB에 존재하는 품목 리스트 조회 (가나다순 정렬)
        db_categories = [
            r[0] for r in db.session.query(Product.item_category)
            .filter(Product.brand_id == current_brand_id)
            .distinct()
            .order_by(Product.item_category)
            .all() 
            if r[0] # 비어있거나 None인 값 제외
        ]
        
        # 2. 버튼 리스트 생성 (항상 '전체'가 1번 - 고정)
        buttons = [{'label': '전체', 'value': '전체'}]
        
        # 3. DB에서 가져온 품목 추가 (최대 14개 추가 -> 전체 포함 15개)
        for cat in db_categories[:14]:
            buttons.append({'label': cat, 'value': cat})
            
        # 4. 카테고리 설정 객체 생성 (5열 고정)
        category_config = {
            'columns': 5, # 5열 레이아웃 (3행 5열 = 15개)
            'buttons': buttons
        }

        # (기존 수동 설정 로직은 무시하고 위 동적 로직을 사용합니다)

        # 상품 목록 조회 (즐겨찾기 등)
        products_query = Product.query.options(selectinload(Product.variants)).filter(
            Product.brand_id == current_brand_id, 
            Product.is_favorite == 1
        )
        products = products_query.order_by(Product.item_category, Product.product_name).all()
        
        context = {
            'active_page': 'search',
            'showing_favorites': True,
            'products': products,
            'query': '',
            'selected_category': '전체',
            'category_config': category_config
        }
        return render_template('search.html', **context)
    
    except Exception as e:
        print(f"Error loading search page: {e}")
        traceback.print_exc()
        flash("페이지 로드 중 오류가 발생했습니다.", "error")
        # 오류 발생 시에도 기본 설정으로 렌더링 시도
        fallback_config = {'columns': 5, 'buttons': [{'label': '전체', 'value': '전체'}]}
        return render_template('search.html', active_page='search', showing_favorites=True, products=[], query='', selected_category='전체', category_config=fallback_config)