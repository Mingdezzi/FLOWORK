from flowork.services.sales_service import SalesService
from flowork.constants import SaleStatus, PaymentMethod
from flowork.models import Sale, StoreStock, StockHistory

def test_create_sale(app, setup_data):
    store_id = setup_data['store'].id
    user_id = setup_data['user'].id
    variant_id = setup_data['variant'].id
    
    items = [{
        'variant_id': variant_id,
        'quantity': 2,
        'price': 10000,
        'discount_amount': 0
    }]
    
    result = SalesService.create_sale(
        store_id=store_id,
        user_id=user_id,
        sale_date_str='2023-01-01',
        items=items,
        payment_method=PaymentMethod.CARD,
        is_online=False
    )
    
    assert result['status'] == 'success'
    
    # 재고 차감 확인 (10 - 2 = 8)
    stock = StoreStock.query.filter_by(store_id=store_id, variant_id=variant_id).first()
    assert stock.quantity == 8
    
    # 판매 기록 확인
    sale = Sale.query.get(result['sale_id'])
    assert sale.status == SaleStatus.VALID
    assert sale.total_amount == 20000

def test_refund_sale_full(app, setup_data):
    # 먼저 판매 생성
    store_id = setup_data['store'].id
    user_id = setup_data['user'].id
    variant_id = setup_data['variant'].id
    
    items = [{'variant_id': variant_id, 'quantity': 1, 'price': 10000}]
    sale_result = SalesService.create_sale(store_id, user_id, '2023-01-01', items, PaymentMethod.CARD, False)
    sale_id = sale_result['sale_id']
    
    # 환불 실행
    refund_result = SalesService.refund_sale_full(sale_id, store_id, user_id)
    
    assert refund_result['status'] == 'success'
    
    # 재고 복구 확인 (10 - 1 + 1 = 10)
    stock = StoreStock.query.filter_by(store_id=store_id, variant_id=variant_id).first()
    assert stock.quantity == 10
    
    # 상태 변경 확인
    sale = Sale.query.get(sale_id)
    assert sale.status == SaleStatus.REFUNDED