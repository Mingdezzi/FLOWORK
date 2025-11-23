import traceback
from datetime import datetime
from flowork.extensions import db
from flowork.models import Customer, Repair

class CrmService:
    @staticmethod
    def add_customer(store_id, name, phone, address):
        try:
            # 고객 코드 생성 (C-날짜-난수 또는 순번)
            today_str = datetime.now().strftime('%Y%m%d')
            count = Customer.query.filter(Customer.customer_code.like(f"C-{today_str}-%")).count()
            code = f"C-{today_str}-{str(count+1).zfill(3)}"
            
            customer = Customer(
                store_id=store_id,
                name=name,
                phone=phone,
                address=address,
                customer_code=code
            )
            db.session.add(customer)
            db.session.commit()
            
            return {'status': 'success', 'message': '고객이 등록되었습니다.', 'customer_id': customer.id}
        except Exception as e:
            db.session.rollback()
            return {'status': 'error', 'message': str(e)}

    @staticmethod
    def create_repair(store_id, data):
        try:
            customer_id = data.get('customer_id')
            
            if not customer_id:
                # 간편 등록: 고객 정보가 텍스트로 온 경우 처리
                name = data.get('customer_name')
                phone = data.get('customer_phone')
                if name and phone:
                    # 기존 고객 검색
                    cust = Customer.query.filter_by(store_id=store_id, phone=phone, name=name).first()
                    if not cust:
                        # 신규 생성
                        today_str = datetime.now().strftime('%Y%m%d')
                        count = Customer.query.filter(Customer.customer_code.like(f"C-{today_str}-%")).count()
                        code = f"C-{today_str}-{str(count+1).zfill(3)}"
                        cust = Customer(store_id=store_id, name=name, phone=phone, customer_code=code)
                        db.session.add(cust)
                        db.session.flush()
                    customer_id = cust.id
                else:
                     return {'status': 'error', 'message': '고객 정보가 필요합니다.'}

            reception_date = datetime.strptime(data.get('date', datetime.now().strftime('%Y-%m-%d')), '%Y-%m-%d')
            
            repair = Repair(
                store_id=store_id,
                customer_id=customer_id,
                reception_date=reception_date,
                product_info=data.get('product_info'),
                product_code=data.get('product_code'),
                color=data.get('color'),
                size=data.get('size'),
                description=data.get('description'),
                status='접수'
            )
            db.session.add(repair)
            db.session.commit()
            return {'status': 'success', 'message': '수선 접수가 완료되었습니다.'}
        except Exception as e:
            db.session.rollback()
            return {'status': 'error', 'message': str(e)}

    @staticmethod
    def update_repair_status(repair_id, store_id, new_status):
        try:
            repair = Repair.query.filter_by(id=repair_id, store_id=store_id).first()
            if not repair:
                return {'status': 'error', 'message': '수선 내역을 찾을 수 없습니다.'}
                
            repair.status = new_status
            db.session.commit()
            return {'status': 'success', 'message': f'상태가 {new_status}(으)로 변경되었습니다.'}
        except Exception as e:
            db.session.rollback()
            return {'status': 'error', 'message': str(e)}