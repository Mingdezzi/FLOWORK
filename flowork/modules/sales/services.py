import json
from datetime import datetime, date
from sqlalchemy import func, or_
from sqlalchemy.orm import selectinload
from flowork.models import db, Sale, SaleItem, StoreStock, StockHistory, Variant, Product, Setting
from flowork.utils import clean_string_upper, get_sort_key

def get_sales_stats(store_id, start, end):
    amt, cnt = db.session.query(func.sum(Sale.total_amount), func.count(Sale.id)).filter(
        Sale.store_id == store_id, Sale.sale_date >= start, Sale.sale_date <= end, Sale.status == 'valid'
    ).first()
    
    disc = db.session.query(func.sum(SaleItem.discount_amount * SaleItem.quantity)).join(Sale).filter(
        Sale.store_id == store_id, Sale.sale_date >= start, Sale.sale_date <= end, Sale.status == 'valid'
    ).scalar()
    
    return {
        'total_amount': int(amt or 0),
        'total_discount': int(disc or 0),
        'total_count': int(cnt or 0)
    }

def get_sales_list(store_id, start, end, page):
    return Sale.query.filter(
        Sale.store_id == store_id, Sale.sale_date >= start, Sale.sale_date <= end
    ).order_by(Sale.created_at.desc()).paginate(page=page, per_page=20)

def create_new_sale(store_id, user_id, data):
    try:
        items = data.get('items', [])
        if not items: return False, "상품 없음", None
        
        s_date = datetime.strptime(data.get('sale_date'), '%Y-%m-%d').date() if data.get('sale_date') else date.today()
        last = Sale.query.filter_by(store_id=store_id, sale_date=s_date).order_by(Sale.daily_number.desc()).first()
        
        sale = Sale(
            store_id=store_id, user_id=user_id, payment_method=data.get('payment_method', '카드'),
            sale_date=s_date, daily_number=(last.daily_number + 1) if last else 1,
            status='valid', is_online=data.get('is_online', False)
        )
        db.session.add(sale)
        db.session.flush()
        
        total = 0
        for i in items:
            vid = i.get('variant_id')
            qty = int(i.get('quantity', 1))
            price = int(i.get('price', 0))
            disc = int(i.get('discount_amount', 0))
            
            stk = StoreStock.query.filter_by(store_id=store_id, variant_id=vid).with_for_update().first()
            if not stk:
                stk = StoreStock(store_id=store_id, variant_id=vid, quantity=0)
                db.session.add(stk)
            
            hist = StockHistory(store_id=store_id, variant_id=vid, change_type='SALE', quantity_change=-qty, current_quantity=stk.quantity - qty, user_id=user_id)
            db.session.add(hist)
            stk.quantity -= qty
            
            v = db.session.get(Variant, vid)
            sub = (price - disc) * qty
            
            si = SaleItem(
                sale_id=sale.id, variant_id=vid, product_name=v.product.product_name, product_number=v.product.product_number,
                color=v.color, size=v.size, original_price=v.original_price, unit_price=price,
                discount_amount=disc, discounted_price=price-disc, quantity=qty, subtotal=sub
            )
            db.session.add(si)
            total += sub
            
        sale.total_amount = total
        db.session.commit()
        return True, sale.receipt_number, sale.id
    except Exception as e:
        db.session.rollback()
        return False, str(e), None

def search_products_for_sales(brand_id, store_id, query, mode, start=None, end=None):
    if not query: return []
    qc = clean_string_upper(query)
    
    if mode == 'detail_stock':
        prod = Product.query.filter(Product.brand_id==brand_id, Product.product_number==query).first()
        if not prod: return []
        
        settings = {s.key: s.value for s in Setting.query.filter_by(brand_id=brand_id).all()}
        vars = sorted(prod.variants, key=lambda v: get_sort_key(v, settings))
        
        v_ids = [v.id for v in vars]
        stocks = StoreStock.query.filter(StoreStock.store_id==store_id, StoreStock.variant_id.in_(v_ids)).all()
        s_map = {s.variant_id: s.quantity for s in stocks}
        
        return [{
            'variant_id': v.id, 'color': v.color, 'size': v.size,
            'original_price': v.original_price, 'sale_price': v.sale_price,
            'stock': s_map.get(v.id, 0)
        } for v in vars]
    
    base = Product.query.filter(Product.brand_id==brand_id, or_(Product.product_number_cleaned.contains(qc), Product.product_name_cleaned.contains(qc))).limit(50).all()
    res = []
    for p in base:
        v_all = p.variants
        c_map = {}
        for v in v_all:
            if v.color not in c_map: c_map[v.color] = {'ids': [], 'org': v.original_price, 'sale': v.sale_price}
            c_map[v.color]['ids'].append(v.id)
            
        for col, d in c_map.items():
            qty = 0
            if mode == 'sales':
                q = db.session.query(func.sum(StoreStock.quantity)).filter(StoreStock.store_id==store_id, StoreStock.variant_id.in_(d['ids'])).scalar()
                qty = q if q else 0
            elif mode == 'refund' and start and end:
                q = db.session.query(func.sum(SaleItem.quantity)).join(Sale).filter(
                    Sale.store_id==store_id, Sale.sale_date>=start, Sale.sale_date<=end,
                    Sale.status=='valid', SaleItem.variant_id.in_(d['ids'])
                ).scalar()
                qty = q if q else 0
            
            res.append({
                'product_number': p.product_number, 'product_name': p.product_name,
                'year': p.release_year, 'color': col, 'original_price': d['org'],
                'sale_price': d['sale'], 'stat_qty': qty
            })
    return res

def process_refund(sale_id, store_id, user_id, items=None):
    try:
        sale = Sale.query.filter_by(id=sale_id, store_id=store_id).first()
        if not sale: return False, "내역 없음"
        if sale.status == 'refunded': return False, "이미 환불됨"
        
        if not items: # 전체 환불
            for i in sale.items:
                stk = StoreStock.query.filter_by(store_id=store_id, variant_id=i.variant_id).first()
                if stk:
                    hist = StockHistory(store_id=store_id, variant_id=i.variant_id, change_type='REFUND_FULL', quantity_change=i.quantity, current_quantity=stk.quantity + i.quantity, user_id=user_id)
                    db.session.add(hist)
                    stk.quantity += i.quantity
            sale.status = 'refunded'
        else: # 부분 환불
            refunded_total = 0
            all_zero = True
            for ri in items:
                vid = ri['variant_id']
                qty = int(ri['quantity'])
                if qty <= 0: continue
                
                si = SaleItem.query.filter_by(sale_id=sale.id, variant_id=vid).first()
                if si and si.quantity >= qty:
                    amt = si.discounted_price * qty
                    si.quantity -= qty
                    si.subtotal -= amt
                    sale.total_amount -= amt
                    refunded_total += amt
                    
                    stk = StoreStock.query.filter_by(store_id=store_id, variant_id=vid).first()
                    if stk:
                        hist = StockHistory(store_id=store_id, variant_id=vid, change_type='REFUND_PARTIAL', quantity_change=qty, current_quantity=stk.quantity + qty, user_id=user_id)
                        db.session.add(hist)
                        stk.quantity += qty
                        
            for i in sale.items:
                if i.quantity > 0: all_zero = False
            if all_zero: sale.status = 'refunded'
            
        db.session.commit()
        return True, sale.receipt_number
    except Exception as e:
        db.session.rollback()
        return False, str(e)