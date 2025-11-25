class OrderStatus:
    """주문 상태 상수"""
    ORDERED = '고객주문'
    REGISTERED = '주문등록'
    ARRIVED = '매장도착'
    CONTACTED = '고객연락'
    SHIPPED = '택배 발송'
    COMPLETED = '완료'
    ETC = '기타'
    
    ALL = [ORDERED, REGISTERED, ARRIVED, CONTACTED, SHIPPED, COMPLETED, ETC]
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
    """재고 변동 유형 상수"""
    SALE = 'SALE'                     # 판매
    REFUND_FULL = 'REFUND_FULL'       # 전체 환불
    REFUND_PARTIAL = 'REFUND_PARTIAL' # 부분 환불
    MANUAL_UPDATE = 'MANUAL_UPDATE'   # 관리자 수동 수정
    EXCEL_UPLOAD = 'EXCEL_UPLOAD'     # 엑셀 대량 업로드
    CHECK_ADJUST = 'CHECK_ADJUST'     # 실사 반영 조정
    TRANSFER_OUT = 'TRANSFER_OUT'     # 수평 이동 출고
    TRANSFER_IN = 'TRANSFER_IN'       # 수평 이동 입고
    ORDER_IN = 'ORDER_IN'             # 본사 주문 입고
    RETURN_OUT = 'RETURN_OUT'         # 본사 반품 출고

class SaleStatus:
    """판매 상태 상수"""
    VALID = 'valid'       # 정상 판매
    REFUNDED = 'refunded' # 환불됨

class ImageProcessStatus:
    """이미지 처리 상태 상수"""
    READY = 'READY'           # 대기
    PROCESSING = 'PROCESSING' # 처리중
    COMPLETED = 'COMPLETED'   # 완료
    FAILED = 'FAILED'         # 실패

class TransferType:
    """재고 이동 유형 상수"""
    REQUEST = 'REQUEST'         # 매장 요청
    INSTRUCTION = 'INSTRUCTION' # 본사 지시

class TransferStatus:
    """재고 이동 상태 상수"""
    REQUESTED = 'REQUESTED' # 요청됨
    SHIPPED = 'SHIPPED'     # 출고됨 (이동중)
    RECEIVED = 'RECEIVED'   # 입고됨 (완료)
    REJECTED = 'REJECTED'   # 거절됨
    CANCELLED = 'CANCELLED' # 취소됨