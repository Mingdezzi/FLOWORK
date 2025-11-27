import pandas as pd
from backend.models import db, Product, Variant, Stock, Store
from backend import create_app

def process_excel_file(file_path, brand_id, upload_type='inventory'):
    """
    엑셀 파일을 읽어 DB에 반영합니다.
    upload_type: 'full_db' (상품정보+본사재고 리셋), 'store_stock' (매장재고 업데이트)
    """
    df = pd.read_excel(file_path).fillna('')
    
    # 필수 컬럼 확인 및 매핑 로직 (단순화)
    # 실제로는 동적 매핑이 필요할 수 있으나, 여기선 표준 포맷을 가정
    
    if upload_type == 'full_db':
        _process_full_db_import(df, brand_id)
    elif upload_type == 'store_stock':
        pass # 매장 재고 로직 (생략)

def _process_full_db_import(df, brand_id):
    # 기존 데이터 리셋 로직 필요 시 추가
    
    for _, row in df.iterrows():
        p_code = str(row.get('product_number')).strip()
        color = str(row.get('color')).strip()
        size = str(row.get('size')).strip()
        
        # Product 처리
        product = Product.query.filter_by(brand_id=brand_id, product_code=p_code).first()
        if not product:
            product = Product(
                brand_id=brand_id,
                product_code=p_code,
                name=row.get('product_name', p_code),
                search_code=p_code.replace(' ', '').upper(),
                release_year=row.get('year')
            )
            db.session.add(product)
            db.session.flush()
            
        # Variant 처리
        barcode = f"{p_code}{color}{size}" # 단순 바코드 생성 규칙 예시
        variant = Variant.query.filter_by(product_id=product.id, barcode=barcode).first()
        
        if not variant:
            variant = Variant(
                product_id=product.id,
                barcode=barcode,
                color=color,
                size=size,
                sale_price=row.get('price', 0)
            )
            db.session.add(variant)
            db.session.flush()
            
        # 본사 재고 처리 (본사 Store ID를 찾는 로직 필요)
        hq_store = Store.query.filter_by(brand_id=brand_id, is_hq=True).first()
        if hq_store:
            hq_qty = int(row.get('hq_stock', 0))
            stock = Stock.query.filter_by(store_id=hq_store.id, variant_id=variant.id).first()
            if not stock:
                stock = Stock(store_id=hq_store.id, variant_id=variant.id, quantity=0)
                db.session.add(stock)
            
            stock.quantity = hq_qty # 덮어쓰기

    db.session.commit()