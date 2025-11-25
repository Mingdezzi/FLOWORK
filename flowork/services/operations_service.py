import traceback
from datetime import datetime
from flowork.extensions import db
from flowork.models import Attendance, CompetitorBrand, CompetitorSale

class OperationsService:
    @staticmethod
    def save_attendance(store_id, date_str, records):
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            for rec in records:
                staff_id = rec['staff_id']
                
                att = Attendance.query.filter_by(
                    store_id=store_id,
                    staff_id=staff_id,
                    work_date=target_date
                ).first()
                
                if not att:
                    att = Attendance(
                        store_id=store_id,
                        staff_id=staff_id,
                        work_date=target_date
                    )
                    db.session.add(att)
                
                att.status = rec.get('status', '출근')
                att.memo = rec.get('memo', '')
                
                in_time = rec.get('check_in')
                out_time = rec.get('check_out')
                
                att.check_in_time = datetime.strptime(in_time, '%H:%M').time() if in_time else None
                att.check_out_time = datetime.strptime(out_time, '%H:%M').time() if out_time else None
                
            db.session.commit()
            return {'status': 'success', 'message': '근태 기록이 저장되었습니다.'}
            
        except Exception as e:
            db.session.rollback()
            return {'status': 'error', 'message': str(e)}

    @staticmethod
    def add_competitor_brand(store_id, name):
        try:
            brand = CompetitorBrand(store_id=store_id, name=name)
            db.session.add(brand)
            db.session.commit()
            return {'status': 'success', 'message': '추가되었습니다.', 'id': brand.id}
        except Exception as e:
            db.session.rollback()
            return {'status': 'error', 'message': str(e)}

    @staticmethod
    def delete_competitor_brand(brand_id, store_id):
        try:
            brand = CompetitorBrand.query.filter_by(id=brand_id, store_id=store_id).first()
            if brand:
                brand.is_active = False # Soft Delete
                db.session.commit()
            return {'status': 'success'}
        except Exception as e:
            db.session.rollback()
            return {'status': 'error', 'message': str(e)}

    @staticmethod
    def save_competitor_sales(store_id, date_str, records):
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            for rec in records:
                brand_id = rec['brand_id']
                sale = CompetitorSale.query.filter_by(
                    store_id=store_id,
                    competitor_id=brand_id,
                    sale_date=target_date
                ).first()
                
                if not sale:
                    sale = CompetitorSale(
                        store_id=store_id,
                        competitor_id=brand_id,
                        sale_date=target_date
                    )
                    db.session.add(sale)
                
                sale.offline_normal = int(rec.get('off_norm', 0))
                sale.offline_event = int(rec.get('off_evt', 0))
                sale.online_normal = int(rec.get('on_norm', 0))
                sale.online_event = int(rec.get('on_evt', 0))
                
            db.session.commit()
            return {'status': 'success', 'message': '매출이 저장되었습니다.'}
        except Exception as e:
            db.session.rollback()
            return {'status': 'error', 'message': str(e)}