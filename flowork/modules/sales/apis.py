import json
import io
import openpyxl
from flask import request, jsonify, send_file
from flask_login import login_required, current_user
from flowork.modules.sales import sales_bp
from flowork.modules.sales.services import create_new_sale, search_products_for_sales, process_refund
from flowork.models import db, Setting, Sale, SaleItem, Variant, Product, StoreStock
from sqlalchemy import or_

@sales_bp.route('/api/sales/settings', methods=['GET', 'POST'])
@login_required
def api_sales_settings():
    if not current_user.store_id: return jsonify({'status':'error'}), 403
    key = f'SALES_CONFIG_{current_user.store_id}'
    if request.method == 'POST':
        val = json.dumps(request.json, ensure_ascii=False)
        s = Setting.query.filter_by(brand_id=current_user.current_brand_id, key=key).first()
        if s: s.value = val
        else: db.session.add(Setting(brand_id=current_user.current_brand_id, key=key, value=val))
        db.session.commit()
        return jsonify({'status':'success'})
    else:
        s = Setting.query.filter_by(brand_id=current_user.current_brand_id, key=key).first()
        return jsonify({'status':'success', 'config': json.loads(s.value) if s else {}})

@sales_bp.route('/api/sales', methods=['POST'])
@login_required
def api_create_sale():
    if not current_user.store_id: return jsonify({'status':'error'}), 403
    ok, res, sid = create_new_sale(current_user.store_id, current_user.id, request.json)
    if ok: return jsonify({'status':'success', 'message':f'완료 ({res})', 'sale_id':sid})
    return jsonify({'status':'error', 'message':res}), 500

@sales_bp.route('/api/sales/search_products', methods=['POST'])
@login_required
def api_search_sales_prods():
    if not current_user.store_id: return jsonify({'status':'error'}), 403
    d = request.json
    mode = d.get('mode', 'sales')
    if mode == 'detail_stock':
        res = search_products_for_sales(current_user.current_brand_id, current_user.store_id, d.get('query'), mode)
        return jsonify({'status':'success', 'variants':res})
    else:
        res = search_products_for_sales(current_user.current_brand_id, current_user.store_id, d.get('query'), mode, d.get('start_date'), d.get('end_date'))
        return jsonify({'status':'success', 'results':res})

@sales_bp.route('/api/sales/refund_records', methods=['POST'])
@login_required
def api_refund_records():
    if not current_user.store_id: return jsonify({'status':'error'}), 403
    d = request.json
    res = []
    
    v_ids = [v.id for v in db.session.query(Variant.id).join(Product).filter(Product.product_number==d.get('product_number'), Product.brand_id==current_user.current_brand_id, Variant.color==d.get('color')).all()]
    
    if v_ids:
        items = db.session.query(Sale, SaleItem).join(SaleItem).filter(
            Sale.store_id==current_user.store_id, Sale.sale_date>=d.get('start_date'), Sale.sale_date<=d.get('end_date'),
            Sale.status=='valid', SaleItem.variant_id.in_(v_ids)
        ).order_by(Sale.sale_date.desc()).all()
        
        for s, i in items:
            res.append({
                'sale_id': s.id, 'sale_date': s.sale_date.strftime('%Y-%m-%d'), 'receipt_number': s.receipt_number,
                'product_number': i.product_number, 'product_name': i.product_name, 'color': i.color, 'size': i.size,
                'quantity': i.quantity, 'total_amount': s.total_amount
            })
    return jsonify({'status':'success', 'records':res})

@sales_bp.route('/api/sales/<int:sid>/refund', methods=['POST'])
@login_required
def api_refund_full(sid):
    if not current_user.store_id: return jsonify({'status':'error'}), 403
    ok, msg = process_refund(sid, current_user.store_id, current_user.id)
    if ok: return jsonify({'status':'success', 'message':f'환불 완료 ({msg})'})
    return jsonify({'status':'error', 'message':msg}), 500

@sales_bp.route('/api/sales/<int:sid>/refund_partial', methods=['POST'])
@login_required
def api_refund_partial(sid):
    if not current_user.store_id: return jsonify({'status':'error'}), 403
    ok, msg = process_refund(sid, current_user.store_id, current_user.id, request.json.get('items', []))
    if ok: return jsonify({'status':'success', 'message':'부분 환불 완료'})
    return jsonify({'status':'error', 'message':msg}), 500

@sales_bp.route('/api/sales/<int:sid>/details', methods=['GET'])
@login_required
def api_sale_details(sid):
    if not current_user.store_id: return jsonify({'status':'error'}), 403
    sale = Sale.query.filter_by(id=sid, store_id=current_user.store_id).first()
    if not sale: return jsonify({'status':'error'}), 404
    
    return jsonify({
        'status':'success',
        'sale': {'id':sale.id, 'receipt_number':sale.receipt_number, 'status':sale.status},
        'items': [{
            'variant_id': i.variant_id, 'name': i.product_name, 'pn': i.product_number,
            'color': i.color, 'size': i.size, 'price': i.unit_price, 'original_price': i.original_price,
            'discount_amount': i.discount_amount, 'quantity': i.quantity
        } for i in sale.items if i.quantity > 0]
    })