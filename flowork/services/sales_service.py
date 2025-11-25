import traceback
from datetime import datetime, date
from sqlalchemy import func
from flowork.extensions import db
from flowork.models import Sale, SaleItem, StoreStock, StockHistory, Variant, Store
from flowork.constants import SaleStatus, StockChangeType

class SalesService:
    @staticmethod
    def create_sale(store_id, user_id, sale_date_str, items, payment_method, is_online):
        try:
            # 1. 매장 락(Lock) 및 정보 조회
            store = db.session.query(Store).with_for_update().get(store_id)
            if not store:
                raise ValueError("매장을 찾을 수 없습니다.")

            sale_date = datetime.strptime(sale_date_str, '%Y-%m-%d').date() if sale_date_str else date.today()
            
            # 2. 일련번호 생성
            last_sale = Sale.query.filter_by(store_id=store_id, sale_date=sale_date)\
                                  .order_by(Sale.daily_number.desc()).first()
            next_num = (last_sale.daily_number + 1) if last_sale else 1
            
            # 3. 판매 레코드 생성
            new_sale = Sale(
                store_id=store_id,
                user_id=user_id,
                payment_method=payment_method,
                sale_date=sale_date,
                daily_number=next_num,
                status=SaleStatus.VALID,
                is_online=is_online
            )
            db.session.add(new_sale)
            db.session.flush() # ID 생성을 위해 flush
            
            total_amount = 0
            
            # 4. 아이템 처리 및 재고 차감
            for item in items:
                variant_id = item.get('variant_id')
                qty = int(item.get('quantity', 1))
                
                # [보안 패치] DB에서 상품 정보를 직접 조회하여 가격 위변조 방지
                variant = db.session.get(Variant, variant_id)
                if not variant:
                    raise ValueError(f"상품 정보를 찾을 수 없습니다. (Variant ID: {variant_id})")

                # 클라이언트가 보낸 가격 대신 DB의 실제 판매가 사용
                unit_price = variant.sale_price
                
                # 할인 금액 검증
                discount_amt = int(item.get('discount_amount', 0))
                if discount_amt < 0: 
                    discount_amt = 0
                if discount_amt > unit_price:
                    raise ValueError(f"할인 금액이 상품 가격보다 클 수 없습니다. ({variant.product.product_name})")

                discounted_price = unit_price - discount_amt
                subtotal = discounted_price * qty
                
                # 재고 조회 및 차감 (Row Lock)
                stock = StoreStock.query.filter_by(store_id=store_id, variant_id=variant_id).with_for_update().first()
                if not stock:
                    stock = StoreStock(store_id=store_id, variant_id=variant_id, quantity=0)
                    db.session.add(stock)
                
                current_qty = stock.quantity
                stock.quantity -= qty
                
                # 이력 기록
                history = StockHistory(
                    store_id=store_id,
                    variant_id=variant_id,
                    change_type=StockChangeType.SALE,
                    quantity_change=-qty,
                    current_quantity=stock.quantity,
                    user_id=user_id
                )
                db.session.add(history)
                
                # 판매 상세 아이템 저장 (스냅샷)
                sale_item = SaleItem(
                    sale_id=new_sale.id,
                    variant_id=variant_id,
                    product_name=variant.product.product_name,
                    product_number=variant.product.product_number,
                    color=variant.color,
                    size=variant.size,
                    original_price=variant.original_price,
                    unit_price=unit_price, # 검증된 DB 가격
                    discount_amount=discount_amt,
                    discounted_price=discounted_price,
                    quantity=qty,
                    subtotal=subtotal
                )
                db.session.add(sale_item)
                total_amount += subtotal
                
            new_sale.total_amount = total_amount
            db.session.commit()
            
            return {
                'status': 'success', 
                'message': f'판매 등록 완료 ({new_sale.receipt_number})', 
                'sale_id': new_sale.id
            }
            
        except Exception as e:
            db.session.rollback()
            print("Sale Creation Error:")
            traceback.print_exc()
            return {'status': 'error', 'message': f'판매 등록 중 오류 발생: {str(e)}'}

    @staticmethod
    def refund_sale_full(sale_id, store_id, user_id):
        try:
            sale = Sale.query.filter_by(id=sale_id, store_id=store_id).first()
            if not sale: return {'status': 'error', 'message': '내역 없음'}
            if sale.status == SaleStatus.REFUNDED: 
                return {'status': 'error', 'message': '이미 환불된 건입니다.'}
            
            for item in sale.items:
                if item.quantity <= 0: continue
                
                stock = StoreStock.query.filter_by(store_id=store_id, variant_id=item.variant_id).with_for_update().first()
                # 재고가 없으면 생성
                if not stock:
                    stock = StoreStock(store_id=store_id, variant_id=item.variant_id, quantity=0)
                    db.session.add(stock)

                stock.quantity += item.quantity
                
                history = StockHistory(
                    store_id=store_id,
                    variant_id=item.variant_id,
                    change_type=StockChangeType.REFUND_FULL,
                    quantity_change=item.quantity,
                    current_quantity=stock.quantity,
                    user_id=user_id
                )
                db.session.add(history)
                
            sale.status = SaleStatus.REFUNDED
            db.session.commit()
            return {'status': 'success', 'message': f'환불 완료 ({sale.receipt_number})'}
            
        except Exception as e:
            db.session.rollback()
            traceback.print_exc()
            return {'status': 'error', 'message': str(e)}

    @staticmethod
    def refund_sale_partial(sale_id, store_id, user_id, refund_items):
        try:
            # 부분 환불 시에도 Lock을 걸어 동시성 문제 방지
            sale = Sale.query.filter_by(id=sale_id, store_id=store_id).with_for_update().first()
            if not sale: return {'status': 'error', 'message': '내역 없음'}
            if sale.status == SaleStatus.REFUNDED: 
                return {'status': 'error', 'message': '이미 전체 환불된 건입니다.'}

            total_refunded_amount = 0

            for r_item in refund_items:
                variant_id = r_item['variant_id']
                refund_qty = int(r_item['quantity'])
                
                if refund_qty <= 0: continue

                sale_item = SaleItem.query.filter_by(sale_id=sale.id, variant_id=variant_id).first()
                
                if sale_item and sale_item.quantity >= refund_qty:
                    # 환불 금액 계산 (할인 적용가 기준)
                    refund_amount = sale_item.discounted_price * refund_qty
                    
                    sale_item.quantity -= refund_qty
                    sale_item.subtotal -= refund_amount
                    sale.total_amount -= refund_amount
                    total_refunded_amount += refund_amount
                    
                    # 재고 복구
                    stock = StoreStock.query.filter_by(store_id=store_id, variant_id=variant_id).with_for_update().first()
                    if not stock:
                        stock = StoreStock(store_id=store_id, variant_id=variant_id, quantity=0)
                        db.session.add(stock)

                    stock.quantity += refund_qty
                        
                    history = StockHistory(
                        store_id=store_id,
                        variant_id=variant_id,
                        change_type=StockChangeType.REFUND_PARTIAL,
                        quantity_change=refund_qty,
                        current_quantity=stock.quantity,
                        user_id=user_id
                    )
                    db.session.add(history)

            # 모든 아이템이 환불(수량 0)되었는지 확인하여 상태 업데이트
            all_zero = True
            for item in sale.items:
                if item.quantity > 0:
                    all_zero = False
                    break
            
            if all_zero:
                sale.status = SaleStatus.REFUNDED

            db.session.commit()
            return {'status': 'success', 'message': '부분 환불이 완료되었습니다.'}

        except Exception as e:
            db.session.rollback()
            traceback.print_exc()
            return {'status': 'error', 'message': str(e)}
