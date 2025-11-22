from datetime import datetime
from urllib.parse import quote
from sqlalchemy import extract
from sqlalchemy.orm import selectinload
from flowork.models import db, Order, OrderProcessing, Product, Store, Setting, Brand, StoreOrder, StoreReturn, Variant, StoreStock, StockHistory
from flowork.constants import OrderStatus, ReceptionMethod

def get_customer_orders(store_id, year=None, month=None):
    base_query = db.session.query(Order).options(
        selectinload(Order.product_ref),
        selectinload(Order.store)
    ).filter(Order.store_id == store_id)

    pending_orders = base_query.filter(
        Order.order_status.not_in([OrderStatus.COMPLETED, OrderStatus.ETC])
    ).order_by(Order.created_at.desc(), Order.id.desc()).all()

    monthly_orders = []
    if year and month:
        monthly_orders = base_query.filter(
            extract('year', Order.created_at) == year,
            extract('month', Order.created_at) == month
        ).order_by(Order.created_at.desc(), Order.id.desc()).all()
        
    return pending_orders, monthly_orders

def get_order_detail(order_id, store_id):
    return Order.query.options(
        selectinload(Order.processing_steps).selectinload(OrderProcessing.source_store)
    ).filter_by(id=order_id, store_id=store_id).first()

def create_customer_order(store_id, form_data):
    try:
        created_at = datetime.strptime(form_data.get('created_at'), '%Y-%m-%d') if form_data.get('created_at') else datetime.now()
        completed_at = datetime.strptime(form_data.get('completed_at'), '%Y-%m-%d') if form_data.get('completed_at') else None
        
        product = Product.query.filter_by(product_number=form_data.get('product_number'), brand_id=form_data.get('brand_id')).first()
        
        order = Order(
            store_id=store_id,
            product_id=product.id if product else None,
            reception_method=form_data.get('reception_method'),
            created_at=created_at,
            customer_name=form_data.get('customer_name'),
            customer_phone=form_data.get('customer_phone'),
            postcode=form_data.get('postcode'),
            address1=form_data.get('address1'),
            address2=form_data.get('address2'),
            product_number=form_data.get('product_number'),
            product_name=form_data.get('product_name'),
            color=form_data.get('color'),
            size=form_data.get('size'),
            order_status=form_data.get('order_status'),
            completed_at=completed_at,
            courier=form_data.get('courier'),
            tracking_number=form_data.get('tracking_number'),
            remarks=form_data.get('remarks')
        )
        
        src_ids = form_data.get('processing_source', [])
        src_res = form_data.get('processing_result', [])
        
        for sid, res in zip(src_ids, src_res):
            if sid:
                step = OrderProcessing(source_store_id=int(sid), source_result=res if res else None)
                order.processing_steps.append(step)
                
        db.session.add(order)
        db.session.commit()
        return True, order
    except Exception as e:
        db.session.rollback()
        return False, str(e)

def update_customer_order(order_id, store_id, form_data):
    try:
        order = get_order_detail(order_id, store_id)
        if not order: return False, "주문 없음"
        
        order.reception_method = form_data.get('reception_method')
        order.created_at = datetime.strptime(form_data.get('created_at'), '%Y-%m-%d') if form_data.get('created_at') else order.created_at
        order.customer_name = form_data.get('customer_name')
        order.customer_phone = form_data.get('customer_phone')
        order.postcode = form_data.get('postcode')
        order.address1 = form_data.get('address1')
        order.address2 = form_data.get('address2')
        
        product = Product.query.filter_by(product_number=form_data.get('product_number'), brand_id=form_data.get('brand_id')).first()
        order.product_id = product.id if product else None
        
        order.product_number = form_data.get('product_number')
        order.product_name = form_data.get('product_name')
        order.color = form_data.get('color')
        order.size = form_data.get('size')
        order.order_status = form_data.get('order_status')
        order.completed_at = datetime.strptime(form_data.get('completed_at'), '%Y-%m-%d') if form_data.get('completed_at') else None
        order.courier = form_data.get('courier')
        order.tracking_number = form_data.get('tracking_number')
        order.remarks = form_data.get('remarks')
        
        for step in order.processing_steps: db.session.delete(step)
        
        src_ids = form_data.get('processing_source', [])
        src_res = form_data.get('processing_result', [])
        for sid, res in zip(src_ids, src_res):
            if sid:
                step = OrderProcessing(source_store_id=int(sid), source_result=res if res else None)
                order.processing_steps.append(step)
                
        db.session.commit()
        return True, None
    except Exception as e:
        db.session.rollback()
        return False, str(e)

def delete_customer_order(order_id, store_id):
    try:
        order = Order.query.filter_by(id=order_id, store_id=store_id).first()
        if not order: return False, "주문 없음"
        name = order.customer_name
        db.session.delete(order)
        db.session.commit()
        return True, name
    except Exception as e:
        db.session.rollback()
        return False, str(e)

def update_order_status_simple(order_id, store_id, new_status):
    try:
        order = Order.query.filter_by(id=order_id, store_id=store_id).first()
        if not order: return False, "주문 없음"
        order.order_status = new_status
        db.session.commit()
        return True, None
    except Exception as e:
        db.session.rollback()
        return False, str(e)

def get_store_orders_list(brand_id, store_id=None, page=1):
    query = StoreOrder.query.join(Store).filter(Store.brand_id == brand_id)
    if store_id: query = query.filter(StoreOrder.store_id == store_id)
    return query.order_by(StoreOrder.created_at.desc()).paginate(page=page, per_page=20)

def get_store_returns_list(brand_id, store_id=None, page=1):
    query = StoreReturn.query.join(Store).filter(Store.brand_id == brand_id)
    if store_id: query = query.filter(StoreReturn.store_id == store_id)
    return query.order_by(StoreReturn.created_at.desc()).paginate(page=page, per_page=20)

def create_store_request(model_class, store_id, variant_id, qty, date_str):
    try:
        req = model_class(
            store_id=store_id,
            variant_id=variant_id,
            quantity=qty,
            status='REQUESTED'
        )
        if date_str:
            if model_class == StoreOrder: req.order_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            else: req.return_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
        db.session.add(req)
        db.session.commit()
        return True, None
    except Exception as e:
        db.session.rollback()
        return False, str(e)

def process_store_request_status(model_class, req_id, status, conf_qty, user_id):
    try:
        req = db.session.get(model_class, req_id)
        if not req: return False, "내역 없음"
        if req.status != 'REQUESTED': return False, "이미 처리됨"
        
        if status == 'APPROVED':
            if conf_qty <= 0: return False, "수량 오류"
            variant = db.session.get(Variant, req.variant_id)
            stock = StoreStock.query.filter_by(store_id=req.store_id, variant_id=req.variant_id).first()
            
            if not stock:
                stock = StoreStock(store_id=req.store_id, variant_id=req.variant_id, quantity=0)
                db.session.add(stock)
            
            if model_class == StoreOrder: # 매장 입고 (본사 출고)
                variant.hq_quantity -= conf_qty
                stock.quantity += conf_qty
                change_type = 'ORDER_IN'
                qty_change = conf_qty
            else: # 매장 반품 (본사 입고)
                stock.quantity -= conf_qty
                variant.hq_quantity += conf_qty
                change_type = 'RETURN_OUT'
                qty_change = -conf_qty
                
            history = StockHistory(
                store_id=req.store_id, variant_id=req.variant_id, user_id=user_id,
                change_type=change_type, quantity_change=qty_change, current_quantity=stock.quantity
            )
            db.session.add(history)
            req.confirmed_quantity = conf_qty
            req.status = 'APPROVED'
            
        elif status == 'REJECTED':
            req.status = 'REJECTED'
            
        db.session.commit()
        return True, None
    except Exception as e:
        db.session.rollback()
        return False, str(e)

def generate_sms_link(order, brand_name):
    try:
        phone = order.customer_phone.replace('-', '')
        dt = order.created_at.strftime('%Y-%m-%d')
        if order.address1:
            body = f"안녕하세요 {order.customer_name}님, {brand_name}입니다. {dt} 주문하신 {order.product_name} 제품이 발송되었습니다. {order.courier or ''} {order.tracking_number or ''} 감사합니다."
        else:
            body = f"안녕하세요 {order.customer_name}님, {brand_name}입니다. {dt} 주문하신 {order.product_name} 제품이 매장에 도착했습니다. 방문 부탁드립니다."
        return f"sms:{phone}?body={quote(body)}"
    except: return "#"