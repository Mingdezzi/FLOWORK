import traceback
from sqlalchemy.orm import selectinload
from flowork.extensions import db
from flowork.models import Product, Variant, StoreStock, Store
from flowork.utils import clean_string_upper, get_choseong

class InventoryService:
    @staticmethod
    def process_stock_data(records, upload_mode, brand_id, target_store_id=None, allow_create=True, progress_callback=None):
        """
        정제된 데이터(records)를 받아 DB에 반영합니다.
        """
        cnt_prod = 0
        cnt_var = 0
        cnt_update = 0
        total_items = len(records)

        try:
            # 1. 기존 데이터 로드 (Bulk 처리를 위한 메모리 캐싱)
            # 업로드된 데이터에 있는 품번만 조회하여 최적화
            pn_list = list(set(item['product_number_cleaned'] for item in records))
            
            products_in_db = Product.query.filter(
                Product.brand_id == brand_id, 
                Product.product_number_cleaned.in_(pn_list)
            ).options(
                selectinload(Product.variants).selectinload(Variant.stock_levels)
            ).all()
            
            product_map = {p.product_number_cleaned: p for p in products_in_db}
            
            variant_map = {} 
            for p in products_in_db:
                for v in p.variants:
                    variant_map[v.barcode_cleaned] = v
            
            store_stock_map = {}
            if upload_mode == 'store' and target_store_id:
                v_ids = [v.id for v in variant_map.values()]
                if v_ids:
                    stocks = db.session.query(StoreStock).filter(
                        StoreStock.store_id == target_store_id, 
                        StoreStock.variant_id.in_(v_ids)
                    ).all()
                    store_stock_map = {s.variant_id: s for s in stocks}

            # 2. 데이터 처리 루프
            for idx, item in enumerate(records):
                if progress_callback and idx % 100 == 0:
                    progress_callback(idx, total_items)
                
                try:
                    pn_clean = item['product_number_cleaned']
                    bc_clean = item['barcode_cleaned']

                    # Product 처리
                    prod = product_map.get(pn_clean)
                    if not prod:
                        if not allow_create: continue
                        
                        pname = item.get('product_name') or item['product_number']
                        pn_cleaned_val = item.get('product_number_cleaned')
                        choseong_val = item.get('product_name_choseong')

                        prod = Product(
                            brand_id=brand_id, 
                            product_number=item['product_number'], 
                            product_name=pname, 
                            product_number_cleaned=pn_clean, 
                            product_name_cleaned=clean_string_upper(pname), 
                            product_name_choseong=choseong_val
                        )
                        db.session.add(prod)
                        product_map[pn_clean] = prod
                        cnt_prod += 1
                    
                    # Product 속성 업데이트
                    if item.get('release_year') and item['release_year'] > 0: 
                        prod.release_year = item['release_year']
                    if item.get('item_category'): 
                        prod.item_category = item['item_category']
                    if item.get('is_favorite') == 1:
                        prod.is_favorite = 1
                    
                    # Variant 처리
                    var = variant_map.get(bc_clean)
                    op = item.get('original_price', 0)
                    sp = item.get('sale_price', 0)

                    if not var:
                        if not allow_create: continue
                        var = Variant(
                            product=prod, 
                            barcode=item['barcode'], 
                            color=item['color'], 
                            size=item['size'], 
                            original_price=op, 
                            sale_price=sp, 
                            hq_quantity=0, 
                            barcode_cleaned=bc_clean,
                            color_cleaned=clean_string_upper(item['color']),
                            size_cleaned=clean_string_upper(item['size'])
                        )
                        db.session.add(var)
                        variant_map[bc_clean] = var
                        cnt_var += 1
                    else:
                        if op > 0: var.original_price = op
                        if sp > 0: var.sale_price = sp
                    
                    # 재고 업데이트
                    if upload_mode == 'hq' and 'hq_stock' in item:
                        var.hq_quantity = item['hq_stock']
                        cnt_update += 1
                    
                    elif upload_mode == 'store' and 'store_stock' in item:
                        qty = item['store_stock']
                        
                        # 이미 로드된 재고 맵 사용
                        if var.id in store_stock_map:
                            store_stock_map[var.id].quantity = qty
                            cnt_update += 1
                        else:
                            # 맵에 없으면 새로 생성하거나 product.variants 관계를 통해 확인 (이중 체크)
                            found_in_rel = False
                            if hasattr(var, 'stock_levels'):
                                for s in var.stock_levels:
                                    if s.store_id == target_store_id:
                                        s.quantity = qty
                                        store_stock_map[var.id] = s
                                        found_in_rel = True
                                        break
                            
                            if not found_in_rel:
                                new_stk = StoreStock(store_id=target_store_id, variant_id=var.id, quantity=qty)
                                # 아직 var.id가 없을 수 있으므로(신규 생성), 관계에 추가
                                var.stock_levels.append(new_stk)
                                # 맵에는 id가 생성된 후 추가 가능하므로 여기선 패스
                            
                            cnt_update += 1

                except Exception as e:
                    print(f"Row Error: {e}")
                    continue

            db.session.commit()
            
            if progress_callback: 
                progress_callback(total_items, total_items)
                
            return cnt_update, cnt_var, f"완료: 상품 {cnt_prod} / 옵션 {cnt_var} 생성, {cnt_update}건 업데이트"

        except Exception as e:
            db.session.rollback()
            traceback.print_exc()
            raise e

    @staticmethod
    def full_import_db(records, brand_id, progress_callback=None):
        """
        기존 DB를 삭제하고 전체 데이터를 새로 넣습니다.
        """
        BATCH_SIZE = 5000
        total_items = len(records)
        
        try:
            # 1. 기존 데이터 삭제
            store_ids = db.session.query(Store.id).filter_by(brand_id=brand_id)
            db.session.query(StoreStock).filter(StoreStock.store_id.in_(store_ids)).delete(synchronize_session=False)
            product_ids = db.session.query(Product.id).filter_by(brand_id=brand_id)
            db.session.query(Variant).filter(Variant.product_id.in_(product_ids)).delete(synchronize_session=False)
            db.session.query(Product).filter_by(brand_id=brand_id).delete(synchronize_session=False)
            db.session.commit()
            
            # 2. 데이터 삽입
            products_id_map = {} 
            total_products = 0
            total_variants = 0
            
            for i in range(0, total_items, BATCH_SIZE):
                if progress_callback: progress_callback(i, total_items)
                batch = records[i:i+BATCH_SIZE]
                
                products_to_add = []
                new_products_in_batch = {} 

                for item in batch:
                    pn = item['product_number_cleaned']
                    if pn not in products_id_map and pn not in new_products_in_batch:
                        
                        pname = item.get('product_name') or item['product_number']
                        
                        p = Product(
                            brand_id=brand_id,
                            product_number=item['product_number'],
                            product_name=pname,
                            release_year=item.get('release_year'),
                            item_category=item.get('item_category'),
                            is_favorite=item.get('is_favorite', 0),
                            product_number_cleaned=pn,
                            product_name_cleaned=clean_string_upper(pname),
                            product_name_choseong=item.get('product_name_choseong')
                        )
                        new_products_in_batch[pn] = p
                        products_to_add.append(p)
                
                if products_to_add:
                    db.session.add_all(products_to_add)
                    db.session.flush()
                    for pn, p_obj in new_products_in_batch.items():
                        products_id_map[pn] = p_obj.id
                    total_products += len(products_to_add)
                
                variants_to_add = []
                for item in batch:
                    pid = products_id_map.get(item['product_number_cleaned'])
                    if pid:
                        v = Variant(
                            product_id=pid,
                            barcode=item['barcode'],
                            color=item['color'],
                            size=item['size'],
                            original_price=item['original_price'],
                            sale_price=item['sale_price'],
                            hq_quantity=item.get('hq_stock', 0), 
                            barcode_cleaned=item['barcode_cleaned'],
                            color_cleaned=item.get('color_cleaned', clean_string_upper(item['color'])),
                            size_cleaned=item.get('size_cleaned', clean_string_upper(item['size']))
                        )
                        variants_to_add.append(v)
                
                if variants_to_add:
                    db.session.bulk_save_objects(variants_to_add)
                    total_variants += len(variants_to_add)
                
                db.session.commit()
                
            if progress_callback: progress_callback(total_items, total_items)
            return True, f"초기화 완료: 상품 {total_products}개, 옵션 {total_variants}개"
            
        except Exception as e:
            db.session.rollback()
            traceback.print_exc()
            raise e