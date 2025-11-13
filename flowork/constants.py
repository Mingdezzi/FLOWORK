class OrderStatus:
    """주문 상태 상수"""
    ORDERED = '고객주문'
    REGISTERED = '주문등록'
    ARRIVED = '매장도착'
    CONTACTED = '고객연락'
    SHIPPED = '택배 발송'
    COMPLETED = '완료'
    ETC = '기타'
    
    # 전체 목록 (순서 보장)
    ALL = [ORDERED, REGISTERED, ARRIVED, CONTACTED, SHIPPED, COMPLETED, ETC]
    
    # 진행 중인 상태 (완료/기타 제외)
    PENDING = [ORDERED, REGISTERED, ARRIVED, CONTACTED, SHIPPED]

class ReceptionMethod:
    """수령 방법 상수"""
    VISIT = '방문수령'
    DELIVERY = '택배수령'

class PaymentMethod:
    """결제 수단 상수"""
    CARD = '카드'
    CASH = '현금'
    TRANSFER = '계좌이체'

class StockChangeType:
    """재고 변동 유형 상수 (StockHistory용)"""
    SALE = 'SALE'                     # 판매
    REFUND_FULL = 'REFUND_FULL'       # 전체 환불
    REFUND_PARTIAL = 'REFUND_PARTIAL' # 부분 환불
    MANUAL_UPDATE = 'MANUAL_UPDATE'   # 관리자 수동 수정
    EXCEL_UPLOAD = 'EXCEL_UPLOAD'     # 엑셀 대량 업로드
    CHECK_ADJUST = 'CHECK_ADJUST'     # 실사 반영 조정