import uuid
import os
import traceback
from flask import request, jsonify, send_file, abort, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import or_, delete
from sqlalchemy.orm import selectinload

from flowork.models import db, Product, Variant, StoreStock, Setting, StockHistory, Store
from flowork.utils import clean_string_upper, get_choseong, generate_barcode, get_sort_key
from flowork.modules.product import product_bp
from flowork.modules.product.services import update_stock_quantity, update_actual_stock_quantity, toggle_product_favorite, delete_product_data
# [수정됨] verify_stock_excel, analyze_excel_file은 excel_services에서, export_*는 export_services에서 import
from flowork.modules.product.excel_services import verify_stock_excel
from flowork.modules.product.export_services import export_db_to_excel, export_stock_check_excel, analyze_excel_file
from flowork.modules.product.tasks import task_upsert_inventory, task_import_db, task_process_images
from flowork.modules.product.image_services import save_options_logic

@product_bp.route('/api/verify_excel', methods=['POST'])
@login_required
def api_verify_excel():
    if 'excel_file' not in request.files: return jsonify({'status':'error','message':'파일 없음'}), 400
    f = request.files['excel_file']
    path = f"/tmp/verify_{uuid.uuid4()}.xlsx"
    f.save(path)
    res = verify_stock_excel(path, request.form, request.form.get('upload_mode', 'store'))
    if os.path.exists(path): os.remove(path)
    return jsonify(res)

@product_bp.route('/api/inventory/upsert', methods=['POST'])
@login_required
def api_inventory_upsert():
    mode = request.form.get('upload_mode')
    if mode not in ['db', 'hq', 'store']: return jsonify({'status':'error'}), 400
    if mode in ['db', 'hq'] and current_user.store_id: return jsonify({'status':'error'}), 403
    
    target_id = None
    if mode == 'store':
        target_id = current_user.store_id if current_user.store_id else request.form.get('target_store_id', type=int)
        if not target_id: return jsonify({'status':'error'}), 400
        
    f = request.files.get('excel_file')
    if not f: return jsonify({'status':'error'}), 400
    
    path = f"/tmp/upsert_{mode}_{uuid.uuid4()}.xlsx"
    f.save(path)
    
    excl = [int(x) for x in request.form.get('excluded_row_indices', '').split(',')] if request.form.get('excluded_row_indices') else []
    
    if mode == 'db' and request.form.get('is_full_import') == 'true':
        task = task_import_db.delay(path, request.form.to_dict(), current_user.current_brand_id)
    else:
        task = task_upsert_inventory.delay(path, request.form.to_dict(), mode, current_user.current_brand_id, target_id, excl, True)
        
    return jsonify({'status':'success', 'task_id':task.id})

@product_bp.route('/update_store_stock_excel', methods=['POST'])
@login_required
def api_update_store_stock_excel():
    target_id = current_user.store_id if current_user.store_id else request.form.get('target_store_id', type=int)
    if not target_id: return jsonify({'status':'error'}), 400
    f = request.files.get('excel_file')
    if not f: return jsonify({'status':'error'}), 400
    
    path = f"/tmp/store_upsert_{uuid.uuid4()}.xlsx"
    f.save(path)
    excl = [int(x) for x in request.form.get('excluded_row_indices', '').split(',')] if request.form.get('excluded_row_indices') else []
    
    task = task_upsert_inventory.delay(path, request.form.to_dict(), 'store', current_user.current_brand_id, target_id, excl, True)
    return jsonify({'status':'success', 'task_id':task.id})

@product_bp.route('/export_db_excel')
@login_required
def api_export_db():
    if current_user.is_super_admin: abort(403)
    output, name, err = export_db_to_excel(current_user.current_brand_id)
    if err:
        flash(err, 'warning')
        return redirect(url_for('ui.setting_page'))
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name=name)

@product_bp.route('/export_stock_check')
@login_required
def api_export_stock_check():
    tid = current_user.store_id if current_user.store_id else request.args.get('target_store_id', type=int)
    if not tid: abort(403)
    output, name, err = export_stock_check_excel(tid, current_user.current_brand_id)
    if err:
        flash(err, 'error')
        return redirect(url_for('product.check_page_view'))
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name=name)

@product_bp.route('/api/live_search', methods=['POST'])
@login_required
def api_live_search():
    data = request.json
    q = data.get('query', '')
    cat = data.get('category', '전체')
    page = data.get('page', 1)
    
    try:
        setting_prefix = Setting.query.filter_by(brand_id=current_user.current_brand_id, key='IMAGE_URL_PREFIX').first()
        setting_rule = Setting.query.filter_by(brand_id=current_user.current_brand_id, key='IMAGE_NAMING_RULE').first()
        img_prefix = setting_prefix.value if setting_prefix else "https://files.ebizway.co.kr/files/10249/Style/"
        img_rule = setting_rule.value if setting_rule else "{product_number}.jpg"
    except:
        img_prefix = "https://files.ebizway.co.kr/files/10249/Style/"
        img_rule = "{product_number}.jpg"
        
    base = Product.query.options(selectinload(Product.variants)).filter_by(brand_id=current_user.current_brand_id)
    fav = False
    
    if q or (cat and cat != '전체'):
        if q:
            qc = clean_string_upper(q)
            base = base.filter(or_(Product.product_number_cleaned.like(f"%{qc}%"), Product.product_name_cleaned.like(f"%{qc}%"), Product.product_name_choseong.like(f"%{qc}%")))
        if cat and cat != '전체':
            base = base.filter(Product.item_category == cat)
        final = base.order_by(Product.release_year.asc(), Product.item_category.asc(), Product.product_number.asc())
    else:
        fav = True
        final = base.filter(Product.is_favorite == 1).order_by(Product.item_category, Product.product_name)
        
    pg = final.paginate(page=page, per_page=10, error_out=False)
    
    res = []
    for p in pg.items:
        pn = p.product_number.split(' ')[0]
        yr = str(p.release_year) if p.release_year else (f"20{pn[3:5]}" if len(pn)>=5 and pn[3:5].isdigit() else "")
        color = "00"
        
        vars = p.variants
        colors = sorted(list(set(v.color for v in vars if v.color)))
        colors_str = ", ".join(colors)
        
        sp_str, op, disc = "가격정보없음", 0, "-"
        if vars:
            v0 = vars[0]
            if v0.color: color = v0.color
            sp_str = f"{v0.sale_price:,d}원"
            op = v0.original_price
            if op > 0 and op != v0.sale_price: disc = f"{int((1-(v0.sale_price/op))*100)}%"
            else: disc = "0%"
            
        try: fname = img_rule.format(product_number=pn, color=color, year=yr)
        except: fname = f"{pn}.jpg"
        
        res.append({
            "product_id": p.id, "product_number": p.product_number, "product_name": p.product_name,
            "image_url": f"{img_prefix}{fname}", "colors": colors_str, "sale_price": sp_str,
            "original_price": op, "discount": disc
        })
        
    return jsonify({
        "status": "success", "products": res, "showing_favorites": fav, "selected_category": cat,
        "current_page": pg.page, "total_pages": pg.pages, "total_items": pg.total
    })

@product_bp.route('/api/analyze_excel', methods=['POST'])
@login_required
def api_analyze_excel_route():
    if 'excel_file' not in request.files: return jsonify({'status':'error'}), 400
    res, err = analyze_excel_file(request.files['excel_file'])
    if err: return jsonify({'status':'error', 'message':err}), 500
    return jsonify({'status':'success', 'column_letters':res['letters'], 'preview_data':res['preview']})

@product_bp.route('/bulk_update_actual_stock', methods=['POST'])
@login_required
def api_bulk_update_actual():
    tid = current_user.store_id if current_user.store_id else request.json.get('target_store_id')
    if not tid: return jsonify({'status':'error'}), 403
    
    items = request.json.get('items', [])
    if not items: return jsonify({'status':'error'}), 400
    
    try:
        barcodes = {clean_string_upper(i.get('barcode','')): int(i.get('quantity',0)) for i in items if i.get('barcode')}
        if not barcodes: return jsonify({'status':'error'}), 400
        
        variants = db.session.query(Variant).join(Product).filter(Product.brand_id==current_user.current_brand_id, Variant.barcode_cleaned.in_(barcodes.keys())).all()
        v_map = {v.barcode_cleaned: v.id for v in variants}
        
        stocks = StoreStock.query.filter(StoreStock.store_id==tid, StoreStock.variant_id.in_(v_map.values())).all()
        s_map = {s.variant_id: s for s in stocks}
        
        new_stks = []
        for bc, vid in v_map.items():
            qty = barcodes[bc]
            if vid in s_map: s_map[vid].actual_stock = qty
            else: new_stks.append(StoreStock(store_id=tid, variant_id=vid, quantity=0, actual_stock=qty))
            
        if new_stks: db.session.add_all(new_stks)
        db.session.commit()
        
        unknown = [b for b in barcodes if b not in v_map]
        msg = f"{len(items)}개 항목 업데이트 완료."
        if unknown: flash(f"미확인 바코드 {len(unknown)}개 제외", 'warning')
        else: flash(msg, 'success')
        return jsonify({'status':'success', 'message':msg})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status':'error', 'message':str(e)}), 500

@product_bp.route('/api/fetch_variant', methods=['POST'])
@login_required
def api_fetch_variant_detail():
    tid = current_user.store_id if current_user.store_id else request.json.get('target_store_id')
    if not tid: return jsonify({'status':'error'}), 403
    
    bc = clean_string_upper(request.json.get('barcode', ''))
    if not bc: return jsonify({'status':'error'}), 400
    
    res = db.session.query(Variant, Product).join(Product).filter(Variant.barcode_cleaned==bc, Product.brand_id==current_user.current_brand_id).first()
    if res:
        v, p = res
        stk = StoreStock.query.filter_by(variant_id=v.id, store_id=tid).first()
        return jsonify({
            'status':'success', 'barcode':v.barcode, 'variant_id':v.id, 
            'product_number':p.product_number, 'product_name':p.product_name,
            'color':v.color, 'size':v.size, 'sale_price':v.sale_price,
            'store_stock': stk.quantity if stk else 0
        })
    return jsonify({'status':'error', 'message':'상품 없음'}), 404

@product_bp.route('/update_stock', methods=['POST'])
@login_required
def api_update_stock():
    tid = current_user.store_id if current_user.store_id else request.json.get('target_store_id')
    if not tid: return jsonify({'status':'error'}), 403
    
    bc = request.json.get('barcode')
    chg = int(request.json.get('change', 0))
    if not bc: return jsonify({'status':'error'}), 400
    
    ok, new_q, diff = update_stock_quantity(bc, chg, tid, current_user.current_brand_id)
    if ok: return jsonify({'status':'success', 'new_quantity':new_q, 'barcode':bc, 'new_stock_diff': diff if diff is not None else ''})
    return jsonify({'status':'error', 'message':new_q}), 500

@product_bp.route('/toggle_favorite', methods=['POST'])
@login_required
def api_toggle_favorite():
    if current_user.is_super_admin: return jsonify({'status':'error'}), 403
    pid = request.json.get('product_id')
    ok, res = toggle_product_favorite(pid, current_user.current_brand_id)
    if ok: return jsonify({'status':'success', 'new_favorite_status':res})
    return jsonify({'status':'error', 'message':res}), 500

@product_bp.route('/update_actual_stock', methods=['POST'])
@login_required
def api_update_actual():
    tid = current_user.store_id if current_user.store_id else request.json.get('target_store_id')
    if not tid: return jsonify({'status':'error'}), 403
    
    bc = request.json.get('barcode')
    act_str = request.json.get('actual_stock')
    act = int(act_str) if act_str and str(act_str).isdigit() else None
    if act is not None and act < 0: act = 0
    
    ok, val, diff = update_actual_stock_quantity(bc, act, tid, current_user.current_brand_id)
    if ok: return jsonify({'status':'success', 'barcode':bc, 'new_actual_stock':val if val is not None else '', 'new_stock_diff':diff if diff is not None else ''})
    return jsonify({'status':'error', 'message':val}), 500

@product_bp.route('/api/update_product_details', methods=['POST'])
@login_required
def api_update_details():
    if current_user.store_id or current_user.is_super_admin: abort(403)
    
    data = request.json
    pid = data.get('product_id')
    if not pid: return jsonify({'status':'error'}), 400
    
    try:
        brand_id = current_user.current_brand_id
        settings = {s.key: s.value for s in Setting.query.filter_by(brand_id=brand_id).all()}
        
        prod = Product.query.filter_by(id=pid, brand_id=brand_id).first()
        if not prod: return jsonify({'status':'error'}), 404
        
        prod.product_name = data.get('product_name', prod.product_name)
        prod.product_name_cleaned = clean_string_upper(prod.product_name)
        prod.product_name_choseong = get_choseong(prod.product_name)
        
        try: prod.release_year = int(data.get('release_year')) if data.get('release_year') else None
        except: prod.release_year = None
        prod.item_category = data.get('item_category', prod.item_category)
        
        vars_data = data.get('variants', [])
        del_ids, add_list, upd_map = [], [], {}
        
        for v in vars_data:
            act = v.get('action')
            vid = v.get('variant_id')
            if act == 'delete' and vid: del_ids.append(vid)
            elif act == 'add':
                row = {'product_number':prod.product_number, 'color':v.get('color'), 'size':v.get('size')}
                bc = generate_barcode(row, settings)
                if not bc: raise ValueError("바코드 생성 실패")
                add_list.append(Variant(
                    barcode=bc, product_id=prod.id, color=row['color'], size=row['size'],
                    original_price=int(v.get('original_price', 0)), sale_price=int(v.get('sale_price', 0)),
                    hq_quantity=0, barcode_cleaned=clean_string_upper(bc),
                    color_cleaned=clean_string_upper(row['color']), size_cleaned=clean_string_upper(row['size'])
                ))
            elif act == 'update' and vid:
                upd_map[vid] = {
                    'color': v.get('color'), 'size': v.get('size'),
                    'original_price': int(v.get('original_price', 0)), 'sale_price': int(v.get('sale_price', 0)),
                    'color_cleaned': clean_string_upper(v.get('color')), 'size_cleaned': clean_string_upper(v.get('size'))
                }
                
        if del_ids:
            db.session.execute(delete(StoreStock).where(StoreStock.variant_id.in_(del_ids)))
            db.session.execute(delete(Variant).where(Variant.id.in_(del_ids), Variant.product_id == prod.id))
            
        if upd_map:
            targets = Variant.query.filter(Variant.id.in_(upd_map.keys()), Variant.product_id == prod.id).all()
            for t in targets:
                ud = upd_map.get(str(t.id)) or upd_map.get(t.id)
                if ud:
                    for k, val in ud.items(): setattr(t, k, val)
                    
        if add_list: db.session.add_all(add_list)
        db.session.commit()
        return jsonify({'status':'success'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status':'error', 'message':str(e)}), 500

@product_bp.route('/api/product/delete/<int:pid>', methods=['POST'])
@login_required
def api_delete_product_route(pid):
    if current_user.store_id or current_user.is_super_admin: abort(403)
    ok, err = delete_product_data(pid, current_user.current_brand_id)
    if ok:
        flash('삭제되었습니다.', 'success')
        return redirect(url_for('product.product_list_view'))
    flash(f'삭제 실패: {err}', 'error')
    return redirect(url_for('product.product_detail_view', product_id=pid))

@product_bp.route('/api/reset_database_completely', methods=['POST'])
@login_required
def api_reset_db():
    if current_user.store_id: abort(403)
    try:
        bid = current_user.current_brand_id
        s_ids = db.session.query(Store.id).filter_by(brand_id=bid)
        db.session.query(StockHistory).filter(StockHistory.store_id.in_(s_ids)).delete(synchronize_session=False)
        db.session.query(StoreStock).filter(StoreStock.store_id.in_(s_ids)).delete(synchronize_session=False)
        p_ids = db.session.query(Product.id).filter_by(brand_id=bid)
        db.session.query(Variant).filter(Variant.product_id.in_(p_ids)).delete(synchronize_session=False)
        db.session.query(Product).filter_by(brand_id=bid).delete(synchronize_session=False)
        db.session.commit()
        flash('초기화 완료', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'오류: {e}', 'error')
    return redirect(url_for('product.stock_management_view'))

@product_bp.route('/api/find_product_details', methods=['POST'])
@login_required
def api_find_details():
    if not current_user.store_id: abort(403)
    pn = request.json.get('product_number')
    if not pn: return jsonify({'status':'error'}), 400
    
    try:
        settings = {s.key: s.value for s in Setting.query.filter_by(brand_id=current_user.current_brand_id).all()}
        q_clean = clean_string_upper(pn)
        prod = Product.query.options(selectinload(Product.variants)).filter(Product.brand_id==current_user.current_brand_id, Product.product_number_cleaned.like(f"%{q_clean}%")).first()
        
        if prod:
            vars = sorted(prod.variants, key=lambda v: get_sort_key(v, settings))
            cols = []
            sizs = []
            seen_c, seen_s = set(), set()
            for v in vars:
                if v.color not in seen_c:
                    cols.append(v.color)
                    seen_c.add(v.color)
                if v.size not in seen_s:
                    sizs.append(v.size)
                    seen_s.add(v.size)
            return jsonify({'status':'success', 'product_name':prod.product_name, 'product_number':prod.product_number, 'colors':cols, 'sizes':sizs})
        return jsonify({'status':'error'}), 404
    except Exception as e: return jsonify({'status':'error', 'message':str(e)}), 500

@product_bp.route('/api/order_product_search', methods=['POST'])
@login_required
def api_order_search():
    if not current_user.store_id: abort(403)
    q = clean_string_upper(request.json.get('query', ''))
    if not q: return jsonify({'status':'error'}), 400
    
    prods = Product.query.filter(Product.brand_id==current_user.current_brand_id, or_(Product.product_number_cleaned.like(f"%{q}%"), Product.product_name_cleaned.like(f"%{q}%"), Product.product_name_choseong.like(f"%{q}%"))).limit(20).all()
    
    if prods:
        return jsonify({'status':'success', 'products': [{'product_id':p.id, 'product_number':p.product_number, 'product_name':p.product_name} for p in prods]})
    return jsonify({'status':'error', 'message':'검색결과 없음'}), 404

@product_bp.route('/api/search_product_by_prefix', methods=['POST'])
@login_required
def api_search_prefix():
    if current_user.is_super_admin: return jsonify({'status':'error'}), 403
    pre = request.json.get('prefix')
    if not pre or len(pre) != 11: return jsonify({'status':'error'}), 400
    
    res = Product.query.filter(Product.brand_id==current_user.current_brand_id, Product.product_number_cleaned.startswith(clean_string_upper(pre))).all()
    
    if len(res) == 1: return jsonify({'status':'success', 'product_number':res[0].product_number})
    elif len(res) > 1: return jsonify({'status':'found_many', 'query':pre})
    return jsonify({'status':'error'}), 404

@product_bp.route('/api/product/images/process', methods=['POST'])
@login_required
def api_trigger_image_process():
    if not current_user.brand_id: return jsonify({'status':'error'}), 403
    data = request.json
    codes = data.get('style_codes', [])
    opts = data.get('options', {})
    if not codes: return jsonify({'status':'error'}), 400
    
    save_options_logic(current_user.id, current_user.current_brand_id, opts)
    
    for c in codes:
        db.session.query(Product).filter(Product.brand_id==current_user.current_brand_id, Product.product_number.like(f"{c}%")).update({Product.image_status:'PROCESSING', Product.last_message:'시작됨'}, synchronize_session=False)
    db.session.commit()
    
    task = task_process_images.delay(current_user.current_brand_id, codes, opts)
    return jsonify({'status':'success', 'task_id':task.id})