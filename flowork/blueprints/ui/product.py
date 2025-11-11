import traceback
from flask import render_template, request, abort
from flask_login import login_required, current_user
from sqlalchemy import func
from sqlalchemy.orm import selectinload, joinedload

from flowork.models import db, Product, Variant, Store
from flowork.utils import clean_string_upper
# [수정] services 패키지 경로 수정
from flowork.services.db import get_filter_options_from_db
from . import ui_bp

@ui_bp.route('/product/<int:product_id>')
@login_required
def product_detail(product_id):
    if current_user.is_super_admin:
        abort(403, description="슈퍼 관리자는 상품 상세를 볼 수 없습니다.")

    try:
        current_brand_id = current_user.current_brand_id
        my_store_id = current_user.store_id
        
        product = Product.query.options(
            selectinload(Product.variants).selectinload(Variant.stock_levels)
        ).filter(
            Product.id == product_id,
            Product.brand_id == current_brand_id
        ).first()

        if not product:
            abort(404, description=f"상품을 찾을 수 없거나 권한이 없습니다.")
        
        product_variants_for_map = product.variants 
        
        variants = db.session.query(Variant).filter(
            Variant.product_id == product.id
        ).order_by(Variant.color, Variant.size).all()
        
        variants_list_for_json = [{
            'id': v.id,
            'barcode': v.barcode,
            'color': v.color,
            'size': v.size,
            'hq_quantity': v.hq_quantity or 0,
            'original_price': v.original_price or 0,
            'sale_price': v.sale_price or 0
        } for v in variants]
        
        
        all_stores = Store.query.filter(
            Store.brand_id == current_brand_id,
            Store.is_active == True
        ).order_by(Store.store_name).all()
        
        store_id_set = {s.id for s in all_stores}
        
        stock_data_map = {s.id: {} for s in all_stores}
        
        for v in product_variants_for_map:
            for stock_level in v.stock_levels:
                if stock_level.store_id in store_id_set:
                    stock_data_map[stock_level.store_id][v.id] = {
                        'quantity': stock_level.quantity,
                        'actual_stock': stock_level.actual_stock
                    }

        image_pn = product.product_number.split(' ')[0]
        image_url = f"https://files.ebizway.co.kr/files/10249/Style/{image_pn}.jpg"
        
        related_products = []
        if product.item_category:
            related_products = Product.query.options(selectinload(Product.variants)).filter(
                Product.brand_id == current_brand_id, 
                Product.item_category == product.item_category,
                Product.id != product.id
            ).order_by(func.random()).limit(5).all()

        context = {
            'active_page': 'search',
            'product': product,
            'variants': variants,
            'variants_list_for_json': variants_list_for_json,
            'stock_data_map': stock_data_map,
            'all_stores': all_stores,
            'my_store_id': my_store_id,
            'image_url': image_url,
            'related_products': related_products
        }
        return render_template('detail.html', **context)

    except Exception as e:
        print(f"Error loading product detail: {e}")
        traceback.print_exc()
        abort(500, description="상품 상세 정보를 불러오는 중 오류가 발생했습니다.")

@ui_bp.route('/stock_overview')
@login_required
def stock_overview():
    if not current_user.is_admin or current_user.store_id:
        abort(403, description="통합 재고 현황은 본사 관리자만 조회할 수 있습니다.")
    
    try:
        current_brand_id = current_user.current_brand_id
        
        all_stores = Store.query.filter(
            Store.brand_id == current_brand_id,
            Store.is_active == True
        ).order_by(Store.store_name).all()
        
        store_id_set = {s.id for s in all_stores}

        all_variants = db.session.query(Variant)\
            .join(Product)\
            .filter(Product.brand_id == current_brand_id)\
            .options(
                joinedload(Variant.product),
                selectinload(Variant.stock_levels)
            )\
            .order_by(Product.product_number, Variant.color, Variant.size)\
            .all()
        
        stock_matrix = {}
        for v in all_variants:
            stock_map_for_variant = {}
            for stock_level in v.stock_levels:
                if stock_level.store_id in store_id_set:
                    stock_map_for_variant[stock_level.store_id] = stock_level.quantity
            
            stock_matrix[v.id] = stock_map_for_variant

        context = {
            'active_page': 'stock_overview',
            'all_stores': all_stores,
            'all_variants': all_variants,
            'stock_matrix': stock_matrix
        }
        return render_template('stock_overview.html', **context)

    except Exception as e:
        print(f"Error loading stock overview: {e}")
        traceback.print_exc()
        abort(500, description="통합 재고 현황 로드 중 오류가 발생했습니다.")

@ui_bp.route('/list')
@login_required
def list_page():
    if current_user.is_super_admin:
        abort(403, description="슈퍼 관리자는 상세 검색을 사용할 수 없습니다.")

    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        current_brand_id = current_user.current_brand_id
        
        filter_options = get_filter_options_from_db(current_brand_id)

        search_params = {
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
        
        query = db.session.query(Product).options(selectinload(Product.variants)).distinct().filter(
             Product.brand_id == current_brand_id
        )
        
        needs_variant_join = False
        variant_filters = []
        
        if search_params['product_name']:
            query = query.filter(Product.product_name_cleaned.like(f"%{clean_string_upper(search_params['product_name'])}%"))
        if search_params['product_number']:
            query = query.filter(Product.product_number_cleaned.like(f"%{clean_string_upper(search_params['product_number'])}%"))
        if search_params['item_category']:
            query = query.filter(Product.item_category == search_params['item_category'])
        if search_params['release_year']:
            query = query.filter(Product.release_year == int(search_params['release_year']))

        if search_params['color']:
            needs_variant_join = True
            variant_filters.append(Variant.color_cleaned == clean_string_upper(search_params['color']))
        if search_params['size']:
            needs_variant_join = True
            variant_filters.append(Variant.size_cleaned == clean_string_upper(search_params['size']))
        if search_params['original_price']:
            needs_variant_join = True
            variant_filters.append(Variant.original_price == int(search_params['original_price']))
        if search_params['sale_price']:
            needs_variant_join = True
            variant_filters.append(Variant.sale_price == int(search_params['sale_price']))
        if search_params['min_discount']:
            try:
                min_discount_val = float(search_params['min_discount']) / 100.0
                if min_discount_val > 0:
                    needs_variant_join = True
                    variant_filters.append(Variant.original_price > 0)
                    variant_filters.append((Variant.sale_price / Variant.original_price) <= (1.0 - min_discount_val))
            except (ValueError, TypeError):
                pass 

        if needs_variant_join:
            query = query.join(Product.variants).filter(*variant_filters)
            
        showing_all = not any(v for v in search_params.values())

        if showing_all:
             pagination = None
        else:
            pagination = query.order_by(
                Product.release_year.desc(), Product.product_name
            ).paginate(page=page, per_page=per_page, error_out=False)

        context = {
            'active_page': 'list',
            'products': pagination.items if pagination else [],
            'pagination': pagination,
            'filter_options': filter_options,
            'advanced_search_params': search_params,
            'showing_all': showing_all
        }
        
        return render_template('list.html', **context)

    except Exception as e:
        print(f"Error loading list page: {e}")
        traceback.print_exc()
        abort(500, description="상세 검색 중 오류가 발생했습니다.")

@ui_bp.route('/check')
@login_required
def check_page():
    if not current_user.store_id:
        abort(403, description="재고 실사는 매장 계정만 사용할 수 있습니다.")
        
    return render_template('check.html', active_page='check')

@ui_bp.route('/stock')
@login_required
def stock_management():
    if not current_user.store_id:
        abort(403, description="재고 관리는 매장 계정만 사용할 수 있습니다.")

    try:
        missing_data_products = Product.query.filter(
            Product.brand_id == current_user.current_brand_id, 
            or_(
                Product.item_category.is_(None),
                Product.item_category == '',
                Product.release_year.is_(None)
            )
        ).order_by(Product.product_number).all()
        
        context = {
            'active_page': 'stock',
            'missing_data_products': missing_data_products
        }
        return render_template('stock.html', **context)

    except Exception as e:
        print(f"Error loading stock management page: {e}")
        abort(500, description="DB 관리 페이지 로드 중 오류가 발생했습니다.")