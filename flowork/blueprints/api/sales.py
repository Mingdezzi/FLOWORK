import json
import io
import traceback
from datetime import datetime
from flask import request, jsonify, send_file
from flask_login import login_required, current_user
from sqlalchemy import func, or_
import openpyxl

from flowork.models import db, Sale, SaleItem, Setting, StoreStock, Variant, Product, Store, StockHistory
from flowork.utils import clean_string_upper, get_sort_key
from flowork.services.sales_service import SalesService
from . import api_bp

@api_bp.route('/api/sales/settings', methods=['GET', 'POST'])
@login_required
def sales_settings():
    if not current_user.store_id:
        return jsonify({'status': 'error', 'message': '매장 권한 필요'}), 403
    
    SETTING_KEY = f'SALES_CONFIG_{current_user.store_id}'
    
    if request.method == 'POST':
        data = request.json
        value_str = json.dumps(data, ensure_ascii=False)
        
        setting = Setting.query.filter_by(brand_id=current_user.current_brand_id, key=SETTING_KEY).first()
        if setting:
            setting.value = value_str
        else:
            setting = Setting(brand_id=current_user.current_brand_id, key=SETTING_KEY, value=value_str)
            db.session.add(setting)
        db.session.commit()
        return jsonify({'status': 'success', 'message': '판매 설정이 저장되었습니다.'})
        
    else:
        setting = Setting.query.filter_by(brand_id=current_user.current_brand_id, key=SETTING_KEY).first()
        config = json.loads(setting.value) if setting and setting.value else {}
        return jsonify({'status': 'success', 'config': config})

@api_bp.route('/api/sales', methods=['POST'])
@login_required
def create_sale():
    if not current_user.store_id: return jsonify({'status': 'error'}), 403
        
    data = request.json
    items = data.get('items', [])
    payment_method = data.get('payment_method', '카드')
    date_str = data.get('sale_date')
    is_online = data.get('is_online', False)
    
    if not items: return jsonify({'status': 'error', 'message': '상품 없음'}), 400
    
    # 서비스 호출로 위임
    result = SalesService.create_sale(
        store_id=current_user.store_id,
        user_id=current_user.id,
        sale_date_str=date_str,
        items=items,
        payment_method=payment_method,
        is_online=is_online
    )
    
    status_code = 200 if result['status'] == 'success' else 500
    return jsonify(result), status_code

@api_bp.route('/api/sales/search_products', methods=['POST'])
@login_required
def search_sales_products():
    if not current_user.store_id:
        return jsonify({'status': 'error', 'message': '권한 없음'}), 403
    
    data = request.json
    query = data.get('query', '').strip()
    mode = data.get('mode', 'sales') 
    
    if not query:
        return jsonify({'status': 'success', 'results': []})

    q_clean = clean_string_upper(query)
    search_filter = or_(
        Product.product_number_cleaned.contains(q_clean),
        Product.product_name_cleaned.contains(q_clean)
    )

    if mode == 'detail_stock':
        product = Product.query.filter(
            Product.brand_id == current_user.current_brand_id,
            Product.product_number == query 
        ).first()
        
        if not product: return jsonify({'status': 'error', 'variants': []})
        
        settings_query = Setting.query.filter_by(brand_id=current_user.current_brand_id).all()
        brand_settings = {s.key: s.value for s in settings_query}
        
        variants = db.session.query(Variant).filter_by(product_id=product.id).all()
        variants.sort(key=lambda v: get_sort_key(v, brand_settings))
        
        stocks = db.session.query(StoreStock).filter(
            StoreStock.store_id == current_user.store_id,
            StoreStock.variant_id.in_([v.id for v in variants])
        ).all()
        stock_map = {s.variant_id: s.quantity for s in stocks}
        
        result_vars = []
        for v in variants:
            result_vars.append({
                'variant_id': v.id,
                'color': v.color,
                'size': v.size,
                'original_price': v.original_price,
                'sale_price': v.sale_price,
                'stock': stock_map.get(v.id, 0)
            })
        return jsonify({'status': 'success', 'variants': result_vars})

    products = Product.query.filter(
        Product.brand_id == current_user.current_brand_id,
        search_filter
    ).limit(50).all()
    
    results = []
    for p in products:
        base_info = {
            'product_id': p.id,
            'product_number': p.product_number,
            'product_name': p.product_name,
            'year': p.release_year,
        }
        
        variants_all = Variant.query.filter_by(product_id=p.id).all()
        color_map = {}
        for v in variants_all:
            if v.color not in color_map:
                color_map[v.color] = {'ids': [], 'org': v.original_price, 'sale': v.sale_price}
            color_map[v.color]['ids'].append(v.id)
        
        for color, v_data in color_map.items():
            row = base_info.copy()
            row['color'] = color
            row['original_price'] = v_data['org']
            row['sale_price'] = v_data['sale']
            
            stat_qty = 0
            
            if mode == 'sales':
                stocks = db.session.query(func.sum(StoreStock.quantity)).filter(
                    StoreStock.store_id == current_user.store_id,
                    StoreStock.variant_id.in_(v_data['ids'])
                ).scalar()
                stat_qty = stocks if stocks else 0
                
            elif mode == 'refund':
                start_dt = data.get('start_date')
                end_dt = data.get('end_date')
                if start_dt and end_dt:
                    sold = db.session.query(func.sum(SaleItem.quantity)).join(Sale).filter(
                        Sale.store_id == current_user.store_id,
                        Sale.sale_date >= start_dt,
                        Sale.sale_date <= end_dt,
                        Sale.status == 'valid',
                        SaleItem.variant_id.in_(v_data['ids'])
                    ).scalar()
                    stat_qty = sold if sold else 0
            
            row['stat_qty'] = stat_qty
            results.append(row)
            
    return jsonify({'status': 'success', 'results': results})

@api_bp.route('/api/sales/refund_records', methods=['POST'])
@login_required
def get_refund_records():
    if not current_user.store_id:
        return jsonify({'status': 'error'}), 403
        
    data = request.json
    pn = data.get('product_number')
    color = data.get('color')
    start_dt = data.get('start_date')
    end_dt = data.get('end_date')
    
    variants = db.session.query(Variant.id).join(Product).filter(
        Product.product_number == pn,
        Product.brand_id == current_user.current_brand_id,
        Variant.color == color
    ).all()
    v_ids = [v[0] for v in variants]
    
    if not v_ids: return jsonify({'records': []})
    
    items = db.session.query(Sale, SaleItem).join(SaleItem).filter(
        Sale.store_id == current_user.store_id,
        Sale.sale_date >= start_dt,
        Sale.sale_date <= end_dt,
        Sale.status == 'valid',
        SaleItem.variant_id.in_(v_ids)
    ).order_by(Sale.sale_date.desc()).all()
    
    records = []
    for sale, item in items:
        records.append({
            'sale_id': sale.id,
            'sale_date': sale.sale_date.strftime('%Y-%m-%d'),
            'receipt_number': sale.receipt_number,
            'product_number': item.product_number,
            'product_name': item.product_name,
            'color': item.color,
            'size': item.size,
            'quantity': item.quantity,
            'total_amount': sale.total_amount
        })
        
    return jsonify({'status': 'success', 'records': records})

@api_bp.route('/api/sales/list_by_date', methods=['GET'])
@login_required
def get_sales_by_date():
    if not current_user.store_id:
        return jsonify({'status': 'error', 'message': '권한이 없습니다.'}), 403
        
    date_str = request.args.get('date')
    if not date_str:
        return jsonify({'status': 'error', 'message': '날짜가 필요합니다.'}), 400

    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        sales = Sale.query.filter_by(
            store_id=current_user.store_id, 
            sale_date=target_date
        ).order_by(Sale.daily_number.desc()).all()
        
        results = []
        for s in sales:
            items_summary = ", ".join([f"{i.product_name}({i.color}/{i.size})" for i in s.items])
            if len(items_summary) > 30:
                items_summary = items_summary[:30] + "..."
            
            results.append({
                'id': s.id,
                'receipt_number': s.receipt_number,
                'time': s.created_at.strftime('%H:%M'),
                'items_summary': items_summary,
                'total_amount': s.total_amount,
                'status': s.status
            })
            
        return jsonify({'status': 'success', 'sales': results})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@api_bp.route('/api/sales/search_history', methods=['POST'])
@login_required
def search_sales_history():
    if not current_user.store_id: return jsonify({'status': 'error'}), 403
    
    data = request.json
    query = data.get('query', '').strip()
    page = data.get('page', 1)
    per_page = 10
    
    if not query: return jsonify({'status': 'success', 'results': [], 'has_next': False})
    
    try:
        q = clean_string_upper(query)
        base_query = db.session.query(SaleItem, Sale).join(Sale).filter(
            Sale.store_id == current_user.store_id,
            or_(
                SaleItem.product_number.ilike(f"%{q}%"),
                SaleItem.product_name.ilike(f"%{q}%")
            )
        ).order_by(Sale.sale_date.desc(), Sale.id.desc())
        
        pagination = base_query.paginate(page=page, per_page=per_page, error_out=False)
        
        results = []
        for item, sale in pagination.items:
            results.append({
                'sale_id': sale.id,
                'receipt_number': sale.receipt_number,
                'date': sale.sale_date.strftime('%Y-%m-%d'),
                'product_info': f"{item.product_name} ({item.color}/{item.size})",
                'qty': item.quantity,
                'amount': item.subtotal,
                'status': sale.status
            })
            
        return jsonify({
            'status': 'success', 
            'results': results, 
            'has_next': pagination.has_next,
            'page': page
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@api_bp.route('/api/sales/export_daily', methods=['GET'])
@login_required
def export_daily_sales():
    if not current_user.store_id: return jsonify({'status': 'error'}), 403
    
    date_str = request.args.get('date')
    if not date_str: return "날짜가 필요합니다.", 400
    
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        sales = Sale.query.filter_by(store_id=current_user.store_id, sale_date=target_date).order_by(Sale.daily_number).all()
        
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"{date_str} 판매내역"
        
        headers = ["판매일자", "영수번호", "품번", "품명", "컬러", "사이즈", "최초가", "판매가", "수량", "할인액", "할인적용가", "합계", "구분", "상태"]
        ws.append(headers)
        
        total_daily_amount = 0
        
        for sale in sales:
            status_str = "정상" if sale.status == 'valid' else "환불"
            type_str = "온라인" if sale.is_online else "오프라인"
            
            for item in sale.items:
                row = [
                    sale.sale_date.strftime('%Y-%m-%d'),
                    sale.receipt_number,
                    item.product_number,
                    item.product_name,
                    item.color,
                    item.size,
                    item.original_price,
                    item.unit_price,
                    item.quantity,
                    item.discount_amount,
                    item.discounted_price,
                    item.subtotal,
                    type_str,
                    status_str
                ]
                ws.append(row)
                if sale.status == 'valid':
                    total_daily_amount += item.subtotal
        
        ws.append([])
        ws.append(["", "", "", "", "", "", "", "", "", "", "일일 총 매출:", total_daily_amount])
        
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f"Daily_Sales_{date_str}.xlsx"
        )
        
    except Exception as e:
        return f"Export Error: {e}", 500

@api_bp.route('/api/sales/<int:sale_id>/refund', methods=['POST'])
@login_required
def refund_sale(sale_id):
    if not current_user.store_id: return jsonify({'status': 'error'}), 403
    
    # 서비스 호출로 위임
    result = SalesService.refund_sale_full(sale_id, current_user.store_id, current_user.id)
    
    status_code = 200 if result['status'] == 'success' else 500
    return jsonify(result), status_code

@api_bp.route('/api/sales/<int:sale_id>/refund_partial', methods=['POST'])
@login_required
def refund_sale_partial(sale_id):
    if not current_user.store_id: return jsonify({'status': 'error'}), 403
    
    data = request.json
    refund_items = data.get('items', []) 
    
    if not refund_items:
        return jsonify({'status': 'error', 'message': '환불할 상품이 없습니다.'}), 400

    # 서비스 호출로 위임
    result = SalesService.refund_sale_partial(sale_id, current_user.store_id, current_user.id, refund_items)
    
    status_code = 200 if result['status'] == 'success' else 500
    return jsonify(result), status_code


@api_bp.route('/api/sales/<int:sale_id>/details', methods=['GET'])
@login_required
def get_sale_details(sale_id):
    if not current_user.store_id: return jsonify({'status': 'error'}), 403
    
    sale = Sale.query.filter_by(id=sale_id, store_id=current_user.store_id).first()
    if not sale: return jsonify({'status': 'error'}), 404
    
    items = []
    for i in sale.items:
        if i.quantity > 0:
            items.append({
                'variant_id': i.variant_id,
                'name': i.product_name,
                'pn': i.product_number,
                'color': i.color,
                'size': i.size,
                'price': i.unit_price,
                'original_price': i.original_price,
                'discount_amount': i.discount_amount,
                'quantity': i.quantity
            })
    
    return jsonify({
        'status': 'success', 
        'sale': {
            'id': sale.id,
            'receipt_number': sale.receipt_number,
            'status': sale.status,
            'is_online': sale.is_online
        },
        'items': items
    })

@api_bp.route('/api/sales/product_variants', methods=['POST'])
@login_required
def get_product_variants_for_sale():
    data = request.json
    product_id = data.get('product_id')
    if not product_id: return jsonify({'status': 'error', 'message': 'ID 없음'}), 400
        
    try:
        settings_query = Setting.query.filter_by(brand_id=current_user.current_brand_id).all()
        brand_settings = {s.key: s.value for s in settings_query}

        variants = db.session.query(Variant).filter_by(product_id=product_id).all()
        variants.sort(key=lambda v: get_sort_key(v, brand_settings))

        variant_ids = [v.id for v in variants]
        stocks = db.session.query(StoreStock).filter(StoreStock.store_id == current_user.store_id, StoreStock.variant_id.in_(variant_ids)).all()
        stock_map = {s.variant_id: s.quantity for s in stocks}
        
        result = []
        for v in variants:
            result.append({
                'variant_id': v.id,
                'color': v.color,
                'size': v.size,
                'price': v.sale_price,
                'stock': stock_map.get(v.id, 0)
            })
        
        product = db.session.get(Product, product_id)
        
        return jsonify({'status': 'success', 'product_name': product.product_name, 'product_number': product.product_number, 'variants': result})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@api_bp.route('/api/init_sales_tables', methods=['GET'])
def init_sales_tables():
    try:
        SaleItem.__table__.drop(db.engine, checkfirst=True)
        Sale.__table__.drop(db.engine, checkfirst=True)
        db.create_all()
        return "Sales tables re-initialized successfully!"
    except Exception as e:
        return f"Error initializing tables: {e}"