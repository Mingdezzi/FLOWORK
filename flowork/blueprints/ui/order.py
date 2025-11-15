import traceback
from datetime import datetime
from urllib.parse import quote
from flask import render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from sqlalchemy import extract
from sqlalchemy.orm import selectinload

from flowork.models import db, Order, OrderProcessing, Product, Store, Setting, Brand
from flowork.constants import OrderStatus, ReceptionMethod
from . import ui_bp

ORDER_STATUSES_LIST = OrderStatus.ALL
PENDING_STATUSES = OrderStatus.PENDING

def _parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return None

def _get_brand_name_for_sms(brand_id):
    try:
        brand_name_setting = Setting.query.filter_by(brand_id=brand_id, key='BRAND_NAME').first()
        if brand_name_setting and brand_name_setting.value:
            return brand_name_setting.value
        brand = db.session.get(Brand, brand_id)
        if brand and brand.brand_name:
            return brand.brand_name
        return "FLOWORK"
    except Exception:
        return "FLOWORK"

def _generate_sms_link(order, brand_name="FLOWORK"):
    try:
        phone = order.customer_phone.replace('-', '')
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

def _get_order_sources_for_template():
    other_stores = []
    if not current_user.store_id:
        return []
    try:
        # [수정] 현재 로그인한 매장 제외하고 활성화된 매장만 조회
        query = Store.query.filter(
            Store.brand_id == current_user.current_brand_id,
            Store.id != current_user.store_id, 
            Store.is_active == True
        )
        
        stores = query.order_by(Store.store_name).all()
        
        # [수정] 본사(HQ) 매장 식별 및 최상단 배치 로직
        hq_store = None
        normal_stores = []
        
        # HQ_STORE_ID 설정 확인
        hq_setting = Setting.query.filter_by(brand_id=current_user.current_brand_id, key='HQ_STORE_ID').first()
        hq_id = int(hq_setting.value) if hq_setting and hq_setting.value else None
        
        for s in stores:
            # 설정된 HQ ID이거나 이름이 '본사'인 경우
            if (hq_id and s.id == hq_id) or s.store_name == '본사':
                hq_store = s
            else:
                normal_stores.append(s)
        
        # 본사를 리스트 맨 앞에 추가
        if hq_store:
            other_stores = [hq_store] + normal_stores
        else:
            other_stores = normal_stores
            
    except Exception as e:
        print(f"Error fetching other stores: {e}")
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

    if not customer_name: errors.append('고객명은 필수입니다.')
    if not customer_phone: errors.append('연락처는 필수입니다.')
    if not product_number or not product_name: errors.append('상품 정보(품번, 품명)는 필수입니다.')
    if not color or not size: errors.append('상품 옵션(컬러, 사이즈)은 필수입니다.')
    if not reception_method: errors.append('수령 방법은 필수입니다.')
    
    if reception_method == ReceptionMethod.DELIVERY:
        if not form.get('address1') or not form.get('address2'):
            errors.append('택배수령 시 기본주소와 상세주소는 필수입니다.')
    
    product_id = None
    if not errors and product_number:
        product = Product.query.filter_by(
            product_number=product_number,
            brand_id=current_user.current_brand_id
        ).first()
        if product:
            product_id = product.id
        else:
            errors.append(f"'{product_number}' 품번을 상품 DB에서 찾을 수 없습니다.")

    return errors, product_id

@ui_bp.route('/orders')
@login_required
def order_list():
    if not current_user.store_id:
        abort(403, description="고객 주문 관리는 매장 계정만 사용할 수 있습니다.")

    try:
        # [수정] datetime.now() 사용 (KST 적용됨)
        today = datetime.now()
        selected_year = request.args.get('year', today.year, type=int)
        selected_month = request.args.get('month', today.month, type=int)
        
        brand_name = _get_brand_name_for_sms(current_user.current_brand_id)
        
        pending_orders = db.session.query(Order).filter(
            Order.store_id == current_user.store_id, 
            Order.order_status.not_in([OrderStatus.COMPLETED, OrderStatus.ETC])
        ).order_by(Order.created_at.desc(), Order.id.desc()).all()
        
        monthly_orders = db.session.query(Order).filter(
            Order.store_id == current_user.store_id, 
            extract('year', Order.created_at) == selected_year,
            extract('month', Order.created_at) == selected_month
        ).order_by(Order.created_at.desc(), Order.id.desc()).all()
        
        current_year = today.year
        year_list = list(range(current_year, current_year - 3, -1))
        month_list = list(range(1, 13))

        for order in pending_orders: order.sms_link = _generate_sms_link(order, brand_name)
        for order in monthly_orders: order.sms_link = _generate_sms_link(order, brand_name)

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

@ui_bp.route('/order/new', methods=['GET', 'POST'])
@login_required
def new_order():
    if not current_user.store_id:
        abort(403, description="신규 주문 등록은 매장 계정만 사용할 수 있습니다.")
        
    other_stores = _get_order_sources_for_template()
    
    if request.method == 'POST':
        errors, product_id = _validate_order_form(request.form)
        
        if errors:
            for error in errors: flash(error, 'error')
            return render_template(
                'order_detail.html', active_page='order', order=None, 
                order_sources=other_stores, order_statuses=ORDER_STATUSES_LIST,
                default_created_at=datetime.now(), form_data=request.form 
            )

        try:
            created_at_date = _parse_date(request.form.get('created_at'))
            completed_at_date = _parse_date(request.form.get('completed_at'))

            new_order = Order(
                store_id=current_user.store_id,
                product_id=product_id,
                reception_method=request.form.get('reception_method'),
                created_at=created_at_date or datetime.now(), 
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
                'order_detail.html', active_page='order', order=None, 
                order_sources=other_stores, order_statuses=ORDER_STATUSES_LIST,
                default_created_at=datetime.now(), form_data=request.form
            )

    return render_template(
        'order_detail.html', active_page='order', order=None, 
        order_sources=other_stores, order_statuses=ORDER_STATUSES_LIST,
        default_created_at=datetime.now(), form_data=None 
    )

@ui_bp.route('/order/<int:order_id>', methods=['GET', 'POST'])
@login_required
def order_detail(order_id):
    if not current_user.store_id:
        abort(403, description="주문 상세 내역은 매장 계정만 사용할 수 있습니다.")
        
    order = Order.query.options(
        selectinload(Order.processing_steps).selectinload(OrderProcessing.source_store)
    ).filter_by(
        id=order_id, store_id=current_user.store_id
    ).first()
    
    if not order: abort(404, description="해당 주문을 찾을 수 없거나 권한이 없습니다.")

    all_stores_in_brand = _get_order_sources_for_template()

    if request.method == 'POST':
        errors, product_id = _validate_order_form(request.form)
        if errors:
            for error in errors: flash(error, 'error')
            return render_template(
                'order_detail.html', active_page='order', order=order, 
                order_sources=all_stores_in_brand, order_statuses=ORDER_STATUSES_LIST, form_data=request.form 
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

            for step in order.processing_steps: db.session.delete(step)
            
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
                'order_detail.html', active_page='order', order=order, 
                order_sources=all_stores_in_brand, order_statuses=ORDER_STATUSES_LIST, form_data=request.form 
            )

    return render_template(
        'order_detail.html', active_page='order', order=order, 
        order_sources=all_stores_in_brand, order_statuses=ORDER_STATUSES_LIST, form_data=None 
    )

@ui_bp.route('/order/delete/<int:order_id>', methods=['POST'])
@login_required
def delete_order(order_id):
    if not current_user.store_id:
        abort(403, description="주문 삭제는 매장 계정만 사용할 수 있습니다.")
    try:
        order = Order.query.filter_by(id=order_id, store_id=current_user.store_id).first()
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