import traceback
from flask import render_template, request, abort
from flask_login import login_required, current_user
from sqlalchemy import or_
from sqlalchemy.orm import selectinload

from flowork.models import db, Product, Variant
from flowork.utils import clean_string_upper
from flowork.services.db import get_filter_options_from_db
from flowork.services.product_service import ProductService
from . import ui_bp

@ui_bp.route('/product/<int:product_id>')
@login_required
def product_detail(product_id):
    if current_user.is_super_admin:
        abort(403, description="슈퍼 관리자는 상품 상세를 볼 수 없습니다.")

    is_partial = request.args.get('partial') == '1'

    try:
        current_brand_id = current_user.current_brand_id
        my_store_id = current_user.store_id
        
        # 서비스 호출로 로직 위임
        data = ProductService.get_product_detail_context(product_id, current_brand_id, my_store_id)
        
        if not data:
            abort(404, description="상품을 찾을 수 없거나 권한이 없습니다.")

        context = {
            'active_page': 'search',
            'is_partial': is_partial,
            **data # 서비스에서 리턴한 딕셔너리 언패킹 (product, variants 등 포함)
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
        # 서비스 호출로 로직 위임
        data = ProductService.get_stock_overview_matrix(current_user.current_brand_id)

        context = {
            'active_page': 'stock_overview',
            **data # all_stores, all_variants, stock_matrix 포함
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

        pagination = query.order_by(
            Product.release_year.desc(), Product.product_name
        ).paginate(page=page, per_page=per_page, error_out=False)

        context = {
            'active_page': 'list',
            'products': pagination.items,
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