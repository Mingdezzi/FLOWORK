import traceback
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify
)
from flask_login import login_required, current_user
from sqlalchemy import or_, desc, func, extract
from sqlalchemy.orm import aliased, selectinload # (수정) selectinload 임포트 확인
from datetime import datetime
from urllib.parse import quote

# (수정) Staff 모델 임포트
from flowork.models import db, Product, Variant, Order, OrderProcessing, Announcement, Store, Setting, Brand, StoreStock, Staff
from flowork.utils import clean_string_upper, get_sort_key
from flowork.services_db import get_filter_options_from_db

ui_bp = Blueprint('ui', __name__, template_folder='../templates')

ORDER_STATUSES_LIST = [
    '고객주문', 
    '주문등록', 
    '매장도착', 
    '고객연락',
    '택배 발송',
    '완료', 
    '기타'
]

PENDING_STATUSES = [
    '고객주문', 
    '주문등록', 
    '매장도착', 
    '고객연락',
    '택배 발송'
]


def _parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return None

def _get_brand_name_for_sms(store):
    try:
        brand_name_setting = Setting.query.filter_by(
            store_id=store.id, 
            key='BRAND_NAME'
        ).first()
        
        if brand_name_setting and brand_name_setting.value:
            return brand_name_setting.value
        
        return store.brand.brand_name or "FLOWORK"
    except Exception:
        return "FLOWORK"


def _generate_sms_link(order, brand_name="FLOWORK"):
    try:
        phone = order.customer_phone.replace('-', '')
        
        # (수정) order.created_at이 None이 될 수 없으므로(모델 기본값), None 체크 제거
        date_str = order.created_at.strftime('%Y-%m-%d')
        product = order.product_name
        customer = order.customer_name
        
        if order.address1: 
            courier = order.courier or '[택배사정보없음]'
            tracking = order.tracking_number or '[송장번호없음]'
            body = f"안녕하세요 {customer}님, {brand_name}입니다. 고객님께서 {date_str} 에 주문하셨던 {product} 제품이 오늘 발송되었습니다. {courier} {tracking} 입니다. 감사합니다."
        
        else: 
            body = f"안녕하세요 {customer}님, {brand_name}입니다. 고객님께서 {date_str} 에 주문하셨던 {product} 제품이 오늘 매장에 도착하였습니다. 편하신 시간대에 방문해주시면 됩니다. 감사합니다."
        
        encoded_body = quote(body)
        
        return f"sms:{phone}?body={encoded_body}"
    
    except Exception as e:
        print(f"Error generating SMS link for order {order.id}: {e}")
        return "#"


@ui_bp.route('/')
@login_required
def home():
    return render_template('index.html', active_page='home')

@ui_bp.route('/search')
@login_required
def search_page():
    try:
        # (수정) .options(selectinload(Product.variants)) 추가 (N+1 해결)
        products_query = Product.query.options(selectinload(Product.variants)).filter(
            Product.brand_id == current_user.store.brand_id, 
            Product.is_favorite == 1
        )
        products = products_query.order_by(Product.item_category, Product.product_name).all()
        
        context = {
            'active_page': 'search',
            'showing_favorites': True,
            'products': products,
            'query': '',
            'selected_category': '전체'
        }
        return render_template('search.html', **context)
    
    except Exception as e:
        print(f"Error loading search page: {e}")
        traceback.print_exc()
        flash("페이지 로드 중 오류가 발생했습니다.", "error")
        return render_template('search.html', active_page='search', showing_favorites=True, products=[], query='', selected_category='전체')


@ui_bp.route('/product/<int:product_id>')
@login_required
def product_detail(product_id):
    try:
        # (수정) 재고 정보(stock_levels)도 함께 로드하도록 최적화
        product = Product.query.options(
            selectinload(Product.variants).selectinload(Variant.stock_levels)
        ).filter(
            Product.id == product_id,
            Product.brand_id == current_user.store.brand_id
        ).first()

        if not product:
            abort(404, description=f"상품을 찾을 수 없거나 권한이 없습니다.")
        
        # (수정) .all() 제거 (이미 로드됨)
        product_variants = product.variants 
        variants = sorted(product_variants, key=get_sort_key)
        
        # (수정) 개별 쿼리 대신, 미리 로드된 재고 정보 사용
        stock_data_map = {}
        for v in product_variants:
            # 현재 매장의 재고만 필터링
            my_stock = next((s for s in v.stock_levels if s.store_id == current_user.store_id), None)
            if my_stock:
                stock_data_map[v.id] = my_stock
        
        image_pn = product.product_number.split(' ')[0]
        image_url = f"https://files.ebizway.co.kr/files/10249/Style/{image_pn}.jpg"
        
        related_products = []
        if product.item_category:
            # (수정) 연관 상품 쿼리 시 variants도 함께 로드 (N+1 방지)
            related_products = Product.query.options(selectinload(Product.variants)).filter(
                Product.brand_id == current_user.store.brand_id, 
                Product.item_category == product.item_category,
                Product.id != product.id
            ).order_by(func.random()).limit(5).all()

        context = {
            'active_page': 'search',
            'product': product,
            'variants': variants, 
            'stock_data_map': stock_data_map,
            'image_url': image_url,
            'related_products': related_products
        }
        return render_template('detail.html', **context)

    except Exception as e:
        print(f"Error loading product detail: {e}")
        traceback.print_exc()
        abort(500, description="상품 상세 정보를 불러오는 중 오류가 발생했습니다.")


@ui_bp.route('/list')
@login_required
def list_page():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        filter_options = get_filter_options_from_db(current_user.store.brand_id)

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
             Product.brand_id == current_user.store.brand_id
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
    return render_template('check.html', active_page='check')

@ui_bp.route('/stock')
@login_required
def stock_management():
    try:
        missing_data_products = Product.query.filter(
            Product.brand_id == current_user.store.brand_id, 
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

@ui_bp.route('/setting')
@login_required
def setting_page():
    try:
        brand_name_setting = Setting.query.filter_by(
            store_id=current_user.store_id, 
            key='BRAND_NAME'
        ).first()
        
        brand_name_display = brand_name_setting.value if (brand_name_setting and brand_name_setting.value) else current_user.store.brand.brand_name

        my_store_id = current_user.store_id
        
        all_stores_in_brand = Store.query.filter(
            Store.brand_id == current_user.store.brand_id
        ).order_by(Store.store_name).all()
        
        # (신규) 직원 명단 조회
        staff_list = Staff.query.filter(
            Staff.store_id == current_user.store_id,
            Staff.is_active == True
        ).order_by(Staff.name).all()
        
        context = {
            'active_page': 'setting',
            'brand_name': brand_name_display,
            'my_store_id': my_store_id,
            'all_stores': all_stores_in_brand,
            'staff_list': staff_list # (신규) 템플릿에 전달
        }
        return render_template('setting.html', **context)
    
    except Exception as e:
        print(f"Error loading setting page: {e}")
        traceback.print_exc()
        abort(500, description="설정 페이지를 불러오는 중 오류가 발생했습니다.")


@ui_bp.route('/orders')
@login_required
def order_list():
    try:
        today = datetime.utcnow()
        
        selected_year = request.args.get('year', today.year, type=int)
        selected_month = request.args.get('month', today.month, type=int)
        
        # (수정) SMS 링크용 브랜드 이름은 한 번만 조회
        brand_name = _get_brand_name_for_sms(current_user.store)
        
        # (수정) .notin_ -> .not_in()
        pending_orders = db.session.query(Order).filter(
            Order.store_id == current_user.store_id, 
            Order.order_status.not_in(['완료', '기타'])
        ).order_by(Order.created_at.desc(), Order.id.desc()).all()
        
        monthly_orders = db.session.query(Order).filter(
            Order.store_id == current_user.store_id, 
            extract('year', Order.created_at) == selected_year,
            extract('month', Order.created_at) == selected_month
        ).order_by(Order.created_at.desc(), Order.id.desc()).all()
        
        current_year = today.year
        year_list = list(range(current_year, current_year - 3, -1))
        month_list = list(range(1, 13))

        for order in pending_orders:
            order.sms_link = _generate_sms_link(order, brand_name)
        for order in monthly_orders:
            order.sms_link = _generate_sms_link(order, brand_name)

        return render_template(
            'order.html',
            active_page='order',
            pending_orders=pending_orders,
            monthly_orders=monthly_orders,
            year_list=year_list,
            month_list=month_list,
            selected_year=selected_year,
            selected_month=selected_month,
            PENDING_STATUSES=PENDING_STATUSES 
        )
        
    except Exception as e:
        print(f"Error loading order list: {e}")
        traceback.print_exc() 
        abort(500, description="주문 목록 로드 중 오류가 발생했습니다.")

def _get_order_sources_for_template():
    other_stores = []
    try:
        other_stores = Store.query.filter(
            Store.brand_id == current_user.store.brand_id
        ).order_by(Store.store_name).all()
    except Exception as e:
        print(f"Error fetching other stores for new_order: {e}")
        flash("주문처(매장) 목록을 불러오는 중 오류가 발생했습니다.", "error")
    return other_stores

def _validate_order_form(form):
    errors = []
    customer_name = form.get('customer_name', '').strip()
    customer_phone = form.get('customer_phone', '').strip()
    product_number = form.get('product_number', '').strip()
    product_name = form.get('product_name', '').strip()
    reception_method = form.get('reception_method')
    color = form.get('color', '').strip()
    size = form.get('size', '').strip()

    if not customer_name:
        errors.append('고객명은 필수입니다.')
    if not customer_phone:
        errors.append('연락처는 필수입니다.')
    if not product_number or not product_name:
        errors.append('상품 정보(품번, 품명)는 필수입니다.')
    if not color or not size:
        errors.append('상품 옵션(컬러, 사이즈)은 필수입니다.')
    if not reception_method:
        errors.append('수령 방법은 필수입니다.')
    
    if reception_method == '택배수령':
        if not form.get('address1') or not form.get('address2'):
            errors.append('택배수령 시 기본주소와 상세주소는 필수입니다.')
    
    product_id = None
    if not errors and product_number:
        product = Product.query.filter_by(
            product_number=product_number,
            brand_id=current_user.store.brand_id
        ).first()
        if product:
            product_id = product.id
        else:
            errors.append(f"'{product_number}' 품번을 상품 DB에서 찾을 수 없습니다.")

    return errors, product_id

@ui_bp.route('/order/new', methods=['GET', 'POST'])
@login_required
def new_order():
    
    other_stores = _get_order_sources_for_template()
    
    if request.method == 'POST':
        errors, product_id = _validate_order_form(request.form)
        
        if errors:
            for error in errors:
                flash(error, 'error')
            
            return render_template(
                'order_detail.html',
                active_page='order',
                order=None, 
                order_sources=other_stores,
                order_statuses=ORDER_STATUSES_LIST,
                default_created_at=datetime.utcnow(),
                form_data=request.form 
            )

        try:
            created_at_date = _parse_date(request.form.get('created_at'))
            completed_at_date = _parse_date(request.form.get('completed_at'))

            new_order = Order(
                store_id=current_user.store_id,
                product_id=product_id,
                
                reception_method=request.form.get('reception_method'),
                created_at=created_at_date or datetime.utcnow(), 
                
                customer_name=request.form.get('customer_name').strip(),
                customer_phone=request.form.get('customer_phone').strip(),
                postcode=request.form.get('postcode'),
                address1=request.form.get('address1'),
                address2=request.form.get('address2'),
                
                product_number=request.form.get('product_number').strip(),
                product_name=request.form.get('product_name').strip(),
                color=request.form.get('color').strip(),
                size=request.form.get('size').strip(),
                
                order_status=request.form.get('order_status'),
                completed_at=completed_at_date,
                courier=request.form.get('courier'),
                tracking_number=request.form.get('tracking_number'),
                
                remarks=request.form.get('remarks')
            )
            
            processing_store_ids = request.form.getlist('processing_source')
            processing_results = request.form.getlist('processing_result')
            
            for store_id_str, result in zip(processing_store_ids, processing_results):
                if store_id_str:
                    step = OrderProcessing(
                        source_store_id=int(store_id_str),
                        source_result=result if result else None
                    )
                    step.order = new_order 
            
            db.session.add(new_order)
            db.session.commit()
            
            flash(f"신규 주문 (고객명: {new_order.customer_name})이(가) 등록되었습니다.", "success")
            return redirect(url_for('ui.order_list'))

        except Exception as e:
            db.session.rollback()
            print(f"Error creating new order: {e}")
            traceback.print_exc()
            flash(f"주문 등록 중 오류 발생: {e}", "error")
            
            return render_template(
                'order_detail.html',
                active_page='order',
                order=None, 
                order_sources=other_stores,
                order_statuses=ORDER_STATUSES_LIST,
                default_created_at=datetime.utcnow(),
                form_data=request.form
            )

    return render_template(
        'order_detail.html',
        active_page='order',
        order=None, 
        order_sources=other_stores,
        order_statuses=ORDER_STATUSES_LIST,
        default_created_at=datetime.utcnow(),
        form_data=None 
    )

@ui_bp.route('/order/<int:order_id>', methods=['GET', 'POST'])
@login_required
def order_detail(order_id):
    
    # (수정) N+1 문제 해결을 위해 processing_steps와 source_store를 함께 로드
    order = Order.query.options(
        selectinload(Order.processing_steps).selectinload(OrderProcessing.source_store)
    ).filter_by(
        id=order_id, 
        store_id=current_user.store_id
    ).first()
    
    if not order:
        abort(404, description="해당 주문을 찾을 수 없거나 권한이 없습니다.")

    all_stores_in_brand = _get_order_sources_for_template()

    if request.method == 'POST':
        errors, product_id = _validate_order_form(request.form)
        
        if errors:
            for error in errors:
                flash(error, 'error')

            return render_template(
                'order_detail.html',
                active_page='order',
                order=order, 
                order_sources=all_stores_in_brand,
                order_statuses=ORDER_STATUSES_LIST,
                form_data=request.form 
            )

        try:
            order.reception_method = request.form.get('reception_method')
            order.created_at = _parse_date(request.form.get('created_at'))
            
            order.customer_name = request.form.get('customer_name').strip()
            order.customer_phone = request.form.get('customer_phone').strip()
            order.postcode = request.form.get('postcode')
            order.address1 = request.form.get('address1')
            order.address2 = request.form.get('address2')

            order.product_id = product_id
            order.product_number = request.form.get('product_number').strip()
            order.product_name = request.form.get('product_name').strip()
            order.color = request.form.get('color').strip()
            order.size = request.form.get('size').strip()

            order.order_status = request.form.get('order_status')
            order.completed_at = _parse_date(request.form.get('completed_at'))
            order.courier = request.form.get('courier')
            order.tracking_number = request.form.get('tracking_number')

            order.remarks = request.form.get('remarks')

            # (수정) .all() 제거 (이미 로드됨)
            for step in order.processing_steps:
                db.session.delete(step)
            
            processing_store_ids = request.form.getlist('processing_source')
            processing_results = request.form.getlist('processing_result')

            for store_id_str, result in zip(processing_store_ids, processing_results):
                if store_id_str:
                    step = OrderProcessing(
                        source_store_id=int(store_id_str),
                        source_result=result if result else None
                    )
                    order.processing_steps.append(step)

            db.session.commit()
            flash(f"주문(ID: {order.id}) 정보가 수정되었습니다.", "success")
            return redirect(url_for('ui.order_detail', order_id=order.id))

        except Exception as e:
            db.session.rollback()
            print(f"Error updating order {order_id}: {e}")
            traceback.print_exc()
            flash(f"주문 수정 중 오류 발생: {e}", "error")
            
            return render_template(
                'order_detail.html',
                active_page='order',
                order=order, 
                order_sources=all_stores_in_brand,
                order_statuses=ORDER_STATUSES_LIST,
                form_data=request.form 
            )

    return render_template(
        'order_detail.html',
        active_page='order',
        order=order, 
        order_sources=all_stores_in_brand,
        order_statuses=ORDER_STATUSES_LIST,
        form_data=None 
    )

@ui_bp.route('/order/delete/<int:order_id>', methods=['POST'])
@login_required
def delete_order(order_id):
    try:
        order = Order.query.filter_by(
            id=order_id, 
            store_id=current_user.store_id
        ).first()
        
        if order:
            customer_name = order.customer_name
            db.session.delete(order)
            db.session.commit()
            flash(f"주문(고객명: {customer_name})이(가) 삭제되었습니다.", "success")
        else:
            flash("삭제할 주문을 찾을 수 없거나 권한이 없습니다.", "warning")
            
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting order {order_id}: {e}")
        flash(f"주문 삭제 중 오류 발생: {e}", "error")

    return redirect(url_for('ui.order_list'))

@ui_bp.route('/schedule')
@login_required
def schedule():
    # (신규) 캘린더 모달에서 사용할 직원 리스트 조회
    staff_list = Staff.query.filter(
        Staff.store_id == current_user.store_id,
        Staff.is_active == True
    ).order_by(Staff.name).all()
    
    return render_template('schedule.html', 
                           active_page='schedule',
                           staff_list=staff_list) # (신규) 템플릿에 전달

@ui_bp.route('/announcements')
@login_required
def announcement_list():
    try:
        items = Announcement.query.filter(
            Announcement.brand_id == current_user.store.brand_id
        ).order_by(Announcement.created_at.desc()).all()
        
        return render_template('announcements.html', 
                               active_page='announcements', 
                               announcements=items)
    except Exception as e:
        print(f"Error loading announcements: {e}")
        traceback.print_exc()
        abort(500, description="공지사항 로드 중 오류가 발생했습니다.")

@ui_bp.route('/announcement/<id>', methods=['GET', 'POST'])
@login_required
def announcement_detail(id):
    item = None
    if id == 'new':
        if not current_user.is_admin:
            abort(403, description="새 공지사항 작성 권한이 없습니다.")
        item = Announcement(title='', content='')
    else:
        item = Announcement.query.filter_by(
            id=int(id), 
            brand_id=current_user.store.brand_id
        ).first()
        
        if not item:
            abort(404, description="공지사항을 찾을 수 없거나 권한이 없습니다.")

    if request.method == 'POST':
        if not current_user.is_admin:
            abort(403, description="공지사항 수정 권한이 없습니다.")
        try:
            item.title = request.form['title']
            item.content = request.form['content']
            
            if id == 'new':
                item.brand_id = current_user.store.brand_id 
                db.session.add(item)
                flash("새 공지사항이 등록되었습니다.", "success")
            else:
                flash("공지사항이 수정되었습니다.", "success")
                
            db.session.commit()
            return redirect(url_for('ui.announcement_detail', id=item.id))

        except Exception as e:
            db.session.rollback()
            print(f"Error saving announcement: {e}")
            traceback.print_exc()
            flash(f"저장 중 오류 발생: {e}", "error")

    return render_template('announcement_detail.html', 
                           active_page='announcements', 
                           item=item)

@ui_bp.route('/announcement/delete/<int:id>', methods=['POST'])
@login_required
def delete_announcement(id):
    if not current_user.is_admin:
        abort(403, description="공지사항 삭제 권한이 없습니다.")
    try:
        item = Announcement.query.filter_by(
            id=int(id), 
            brand_id=current_user.store.brand_id
        ).first()
        
        if item:
            db.session.delete(item)
            db.session.commit()
            flash(f"공지사항(제목: {item.title})이(가) 삭제되었습니다.", "success")
        else:
            flash("삭제할 공지사항을 찾을 수 없거나 권한이 없습니다.", "warning")
            
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting announcement {id}: {e}")
        flash(f"공지사항 삭제 중 오류 발생: {e}", "error")

    return redirect(url_for('ui.announcement_list'))