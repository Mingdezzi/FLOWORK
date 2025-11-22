from datetime import datetime
from flask import request, jsonify
from flask_login import login_required, current_user
from flowork.modules.crm import crm_bp
from flowork.models import db, Customer, Repair

@crm_bp.route('/api/customers', methods=['GET'])
@login_required
def api_get_customers():
    if not current_user.store_id: return jsonify({'status':'error'}), 403
    q = request.args.get('query', '').strip()
    pg = request.args.get('page', 1, type=int)
    
    base = Customer.query.filter_by(store_id=current_user.store_id)
    if q: base = base.filter((Customer.name.contains(q)) | (Customer.phone.contains(q)))
    
    pagination = base.order_by(Customer.created_at.desc()).paginate(page=pg, per_page=20, error_out=False)
    res = [{'id':c.id, 'code':c.customer_code, 'name':c.name, 'phone':c.phone, 'address':c.address or '', 'created_at':c.created_at.strftime('%Y-%m-%d')} for c in pagination.items]
    
    return jsonify({'status':'success', 'customers':res, 'total_pages':pagination.pages})

@crm_bp.route('/api/customers', methods=['POST'])
@login_required
def api_add_customer():
    if not current_user.store_id: return jsonify({'status':'error'}), 403
    d = request.json
    nm, ph = d.get('name'), d.get('phone')
    if not nm or not ph: return jsonify({'status':'error'}), 400
    
    try:
        ts = datetime.now().strftime('%Y%m%d')
        cnt = Customer.query.filter(Customer.customer_code.like(f"C-{ts}-%")).count()
        code = f"C-{ts}-{str(cnt+1).zfill(3)}"
        c = Customer(store_id=current_user.store_id, name=nm, phone=ph, address=d.get('address'), customer_code=code)
        db.session.add(c)
        db.session.commit()
        return jsonify({'status':'success', 'message':'등록 완료', 'customer_id':c.id})
    except Exception as e: return jsonify({'status':'error', 'message':str(e)}), 500

@crm_bp.route('/api/repairs', methods=['POST'])
@login_required
def api_add_repair():
    if not current_user.store_id: return jsonify({'status':'error'}), 403
    d = request.json
    cid = d.get('customer_id')
    
    if not cid:
        nm, ph = d.get('customer_name'), d.get('customer_phone')
        if nm and ph:
            cust = Customer.query.filter_by(store_id=current_user.store_id, phone=ph, name=nm).first()
            if not cust:
                ts = datetime.now().strftime('%Y%m%d')
                cnt = Customer.query.filter(Customer.customer_code.like(f"C-{ts}-%")).count()
                cust = Customer(store_id=current_user.store_id, name=nm, phone=ph, customer_code=f"C-{ts}-{str(cnt+1).zfill(3)}")
                db.session.add(cust)
                db.session.flush()
            cid = cust.id
        else: return jsonify({'status':'error', 'message':'고객정보 필요'}), 400
        
    try:
        r = Repair(
            store_id=current_user.store_id, customer_id=cid,
            reception_date=datetime.strptime(d.get('date', datetime.now().strftime('%Y-%m-%d')), '%Y-%m-%d'),
            product_info=d.get('product_info'), product_code=d.get('product_code'),
            color=d.get('color'), size=d.get('size'), description=d.get('description'), status='접수'
        )
        db.session.add(r)
        db.session.commit()
        return jsonify({'status':'success'})
    except Exception as e: return jsonify({'status':'error', 'message':str(e)}), 500

@crm_bp.route('/api/repairs/<int:rid>/status', methods=['POST'])
@login_required
def api_update_repair_status(rid):
    if not current_user.store_id: return jsonify({'status':'error'}), 403
    stat = request.json.get('status')
    r = Repair.query.filter_by(id=rid, store_id=current_user.store_id).first()
    if not r: return jsonify({'status':'error'}), 404
    r.status = stat
    db.session.commit()
    return jsonify({'status':'success'})