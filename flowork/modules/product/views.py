from flask import render_template, request, abort, flash, redirect, url_for
from flask_login import login_required, current_user
from flowork.modules.product import product_bp
from flowork.modules.product.services import get_product_detail, get_stock_overview, search_products
from flowork.services.db import get_filter_options_from_db
from flowork.models import Product, Store, db, Variant # Variant 추가

@product_bp.route('/product/<int:product_id>')
@login_required
def product_detail_view(product_id):
    if current_user.is_super_admin: abort(403)
    
    product, variants, stock_map = get_product_detail(product_id, current_user.current_brand_id)
    if not product: abort(404)
    
    variants_json = [{
        'id': v.id, 'barcode': v.barcode, 'color': v.color, 'size': v.size,
        'hq_quantity': v.hq_quantity or 0, 'original_price': v.original_price or 0,
        'sale_price': v.sale_price or 0
    } for v in variants]
    
    all_stores = Store.query.filter(Store.brand_id==current_user.current_brand_id, Store.is_active==True).all()
    
    return render_template(
        'detail.html', active_page='search', product=product, variants=variants,
        variants_list_for_json=variants_json, stock_data_map=stock_map,
        all_stores=all_stores, my_store_id=current_user.store_id,
        is_partial=request.args.get('partial') == '1'
    )

@product_bp.route('/stock_overview')
@login_required
def stock_overview_view():
    if not current_user.is_admin or current_user.store_id: abort(403)
    stores, variants, matrix = get_stock_overview(current_user.current_brand_id)
    return render_template('stock_overview.html', active_page='stock_overview', all_stores=stores, all_variants=variants, stock_matrix=matrix)

@product_bp.route('/list')
@login_required
def product_list_view():
    if current_user.is_super_admin: abort(403)
    params = {
        'product_name': request.args.get('product_name', ''),
        'product_number': request.args.get('product_number', ''),
        'item_category': request.args.get('item_category', ''),
        'release_year': request.args.get('release_year', ''),
        'color': request.args.get('color', ''),
        'size': request.args.get('size', ''),
        'original_price': request.args.get('original_price', ''),
        'sale_price': request.args.get('sale_price', ''),
        'min_discount': request.args.get('min_discount', ''),
    }
    
    page = request.args.get('page', 1, type=int)
    pagination = None
    showing_all = not any(params.values())
    
    if not showing_all:
        pagination = search_products(current_user.current_brand_id, params, page)
        
    options = get_filter_options_from_db(current_user.current_brand_id)
    return render_template(
        'list.html', active_page='list', products=pagination.items if pagination else [],
        pagination=pagination, filter_options=options, advanced_search_params=params, showing_all=showing_all
    )

@product_bp.route('/check')
@login_required
def check_page_view():
    stores = []
    if not current_user.store_id:
        stores = Store.query.filter_by(brand_id=current_user.current_brand_id, is_active=True).order_by(Store.store_name).all()
    return render_template('check.html', active_page='check', all_stores=stores)

@product_bp.route('/stock')
@login_required
def stock_management_view():
    from sqlalchemy import or_ # import here or top
    missing = Product.query.filter(
        Product.brand_id == current_user.current_brand_id,
        or_(Product.item_category.is_(None), Product.item_category=='', Product.release_year.is_(None))
    ).order_by(Product.product_number).all()
    stores = []
    if not current_user.store_id:
        stores = Store.query.filter_by(brand_id=current_user.current_brand_id, is_active=True).order_by(Store.store_name).all()
    return render_template('stock.html', active_page='stock', missing_data_products=missing, all_stores=stores)

@product_bp.route('/search')
@login_required
def search_page_view():
    if current_user.is_super_admin: abort(403)
    
    # 카테고리 버튼 설정 로드
    cat_config = {'columns': 5, 'buttons': [{'label': '전체', 'value': '전체'}]}
    
    # DB에서 카테고리 목록 조회
    cats = [r[0] for r in db.session.query(Product.item_category).filter(Product.brand_id==current_user.current_brand_id).distinct().order_by(Product.item_category).all() if r[0]]
    for c in cats[:24]: cat_config['buttons'].append({'label': c, 'value': c})
        
    return render_template('search.html', active_page='search', category_config=cat_config, showing_favorites=True)