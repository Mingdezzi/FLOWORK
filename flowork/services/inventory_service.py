import traceback
from datetime import datetime
from sqlalchemy import select
from flowork.extensions import db
from flowork.models import Product, Variant, StoreStock, Store, StockHistory
from flowork.utils import clean_string_upper, get_choseong
from flowork.constants import StockChangeType

class InventoryService:
    @staticmethod
    def process_stock_data(records, upload_mode, brand_id, target_store_id=None, allow_create=True, progress_callback=None):
        try:
            if not records:
                return 0, 0, "데이터가 없습니다."

            total_items = len(records)
            
            pn_list = list(set(item['product_number_cleaned'] for item in records if item.get('product_number_cleaned')))
            barcode_list = list(set(item['barcode_cleaned'] for item in records if item.get('barcode_cleaned')))

            existing_products = db.session.query(Product).filter(
                Product.brand_id == brand_id,
                Product.product_number_cleaned.in_(pn_list)
            ).all()
            product_map = {p.product_number_cleaned: p for p in existing_products}

            new_products_data = []
            seen_new_pns = set()

            for item in records:
                pn_clean = item.get('product_number_cleaned')
                if not pn_clean: continue
                
                if pn_clean not in product_map and pn_clean not in seen_new_pns:
                    if allow_create:
                        pname = item.get('product_name') or item.get('product_number')
                        new_products_data.append({
                            'brand_id': brand_id,
                            'product_number': item.get('product_number'),
                            'product_name': pname,
                            'product_number_cleaned': pn_clean,
                            'product_name_cleaned': clean_string_upper(pname),
                            'product_name_choseong': item.get('product_name_choseong'),
                            'release_year': item.get('release_year'),
                            'item_category': item.get('item_category'),
                            'is_favorite': item.get('is_favorite', 0)
                        })
                        seen_new_pns.add(pn_clean)

            if new_products_data:
                db.session.bulk_insert_mappings(Product, new_products_data)
                db.session.flush()
                
                created_products = db.session.query(Product).filter(
                    Product.brand_id == brand_id,
                    Product.product_number_cleaned.in_(seen_new_pns)
                ).all()
                for p in created_products:
                    product_map[p.product_number_cleaned] = p

            existing_variants = db.session.query(Variant).join(Product).filter(
                Product.brand_id == brand_id,
                Variant.barcode_cleaned.in_(barcode_list)
            ).all()
            variant_map = {v.barcode_cleaned: v for v in existing_variants}

            new_variants_data = []
            variants_to_update = []
            seen_new_barcodes = set()

            for item in records:
                pn_clean = item.get('product_number_cleaned')
                bc_clean = item.get('barcode_cleaned')
                if not pn_clean or not bc_clean: continue

                prod = product_map.get(pn_clean)
                if not prod: continue 

                if bc_clean not in variant_map and bc_clean not in seen_new_barcodes:
                    if allow_create:
                        new_variants_data.append({
                            'product_id': prod.id,
                            'barcode': item.get('barcode'),
                            'color': item.get('color'),
                            'size': item.get('size'),
                            'original_price': item.get('original_price', 0),
                            'sale_price': item.get('sale_price', 0),
                            'hq_quantity': item.get('hq_stock', 0) if upload_mode == 'hq' else 0,
                            'barcode_cleaned': bc_clean,
                            'color_cleaned': clean_string_upper(item.get('color')),
                            'size_cleaned': clean_string_upper(item.get('size'))
                        })
                        seen_new_barcodes.add(bc_clean)
                elif bc_clean in variant_map:
                    v = variant_map[bc_clean]
                    update_dict = {'id': v.id}
                    changed = False
                    
                    if item.get('original_price') and item['original_price'] > 0:
                        update_dict['original_price'] = item['original_price']
                        changed = True
                    if item.get('sale_price') and item['sale_price'] > 0:
                        update_dict['sale_price'] = item['sale_price']
                        changed = True
                    
                    if upload_mode == 'hq' and 'hq_stock' in item:
                        update_dict['hq_quantity'] = item['hq_stock']
                        changed = True
                    
                    if changed:
                        variants_to_update.append(update_dict)

            if new_variants_data:
                db.session.bulk_insert_mappings(Variant, new_variants_data)
                db.session.flush()
                
            if variants_to_update:
                db.session.bulk_update_mappings(Variant, variants_to_update)
                db.session.flush()

            if upload_mode == 'store' and target_store_id:
                all_variants_involved = db.session.query(Variant).join(Product).filter(
                    Product.brand_id == brand_id,
                    Variant.barcode_cleaned.in_(barcode_list)
                ).all()
                variant_id_map = {v.barcode_cleaned: v.id for v in all_variants_involved}
                
                variant_ids = list(variant_id_map.values())
                existing_stocks = db.session.query(StoreStock).filter(
                    StoreStock.store_id == target_store_id,
                    StoreStock.variant_id.in_(variant_ids)
                ).all()
                stock_map = {s.variant_id: s for s in existing_stocks}

                new_stocks_data = []
                stocks_to_update = []
                history_data = []

                for item in records:
                    bc_clean = item.get('barcode_cleaned')
                    v_id = variant_id_map.get(bc_clean)
                    
                    if v_id and 'store_stock' in item:
                        new_qty = int(item['store_stock'])
                        
                        if v_id in stock_map:
                            current_stock = stock_map[v_id]
                            if current_stock.quantity != new_qty:
                                change_amt = new_qty - current_stock.quantity
                                stocks_to_update.append({
                                    'id': current_stock.id,
                                    'quantity': new_qty
                                })
                                history_data.append({
                                    'store_id': target_store_id,
                                    'variant_id': v_id,
                                    'change_type': StockChangeType.EXCEL_UPLOAD,
                                    'quantity_change': change_amt,
                                    'current_quantity': new_qty,
                                    'created_at': datetime.now()
                                })
                        else:
                            new_stocks_data.append({
                                'store_id': target_store_id,
                                'variant_id': v_id,
                                'quantity': new_qty
                            })
                            history_data.append({
                                'store_id': target_store_id,
                                'variant_id': v_id,
                                'change_type': StockChangeType.EXCEL_UPLOAD,
                                'quantity_change': new_qty,
                                'current_quantity': new_qty,
                                'created_at': datetime.now()
                            })

                if new_stocks_data:
                    db.session.bulk_insert_mappings(StoreStock, new_stocks_data)
                if stocks_to_update:
                    db.session.bulk_update_mappings(StoreStock, stocks_to_update)
                if history_data:
                    db.session.bulk_insert_mappings(StockHistory, history_data)

            db.session.commit()
            
            if progress_callback:
                progress_callback(total_items, total_items)

            return len(variants_to_update) + (len(stocks_to_update) if upload_mode=='store' else 0), len(new_variants_data), f"처리가 완료되었습니다. (상품 {len(new_products_data)}건, 옵션 {len(new_variants_data)}건 신규)"

        except Exception as e:
            db.session.rollback()
            traceback.print_exc()
            raise e

    @staticmethod
    def full_import_db(records, brand_id, progress_callback=None):
        try:
            if not records:
                return True, "데이터가 없습니다."

            total_items = len(records)
            BATCH_SIZE = 2000
            
            store_ids = db.session.query(Store.id).filter_by(brand_id=brand_id).all()
            store_ids = [s[0] for s in store_ids]
            
            if store_ids:
                db.session.query(StoreStock).filter(StoreStock.store_id.in_(store_ids)).delete(synchronize_session=False)
                db.session.query(StockHistory).filter(StockHistory.store_id.in_(store_ids)).delete(synchronize_session=False)
            
            product_ids = db.session.query(Product.id).filter_by(brand_id=brand_id).all()
            product_ids = [p[0] for p in product_ids]
            
            if product_ids:
                db.session.query(Variant).filter(Variant.product_id.in_(product_ids)).delete(synchronize_session=False)
            
            db.session.query(Product).filter_by(brand_id=brand_id).delete(synchronize_session=False)
            db.session.commit()

            unique_products = {}
            for item in records:
                pn_clean = item.get('product_number_cleaned')
                if pn_clean and pn_clean not in unique_products:
                    pname = item.get('product_name') or item.get('product_number')
                    unique_products[pn_clean] = {
                        'brand_id': brand_id,
                        'product_number': item.get('product_number'),
                        'product_name': pname,
                        'product_number_cleaned': pn_clean,
                        'product_name_cleaned': clean_string_upper(pname),
                        'product_name_choseong': item.get('product_name_choseong'),
                        'release_year': item.get('release_year'),
                        'item_category': item.get('item_category'),
                        'is_favorite': item.get('is_favorite', 0)
                    }
            
            product_list = list(unique_products.values())
            for i in range(0, len(product_list), BATCH_SIZE):
                batch = product_list[i:i+BATCH_SIZE]
                db.session.bulk_insert_mappings(Product, batch)
                db.session.commit()
                if progress_callback:
                    progress_callback(i, total_items)

            all_products = db.session.query(Product.product_number_cleaned, Product.id).filter_by(brand_id=brand_id).all()
            product_id_map = {p[0]: p[1] for p in all_products}

            variant_list = []
            seen_barcodes = set()
            
            for item in records:
                pn_clean = item.get('product_number_cleaned')
                bc_clean = item.get('barcode_cleaned')
                
                if pn_clean in product_id_map and bc_clean and bc_clean not in seen_barcodes:
                    variant_list.append({
                        'product_id': product_id_map[pn_clean],
                        'barcode': item.get('barcode'),
                        'color': item.get('color'),
                        'size': item.get('size'),
                        'original_price': item.get('original_price', 0),
                        'sale_price': item.get('sale_price', 0),
                        'hq_quantity': item.get('hq_stock', 0),
                        'barcode_cleaned': bc_clean,
                        'color_cleaned': clean_string_upper(item.get('color')),
                        'size_cleaned': clean_string_upper(item.get('size'))
                    })
                    seen_barcodes.add(bc_clean)

            for i in range(0, len(variant_list), BATCH_SIZE):
                batch = variant_list[i:i+BATCH_SIZE]
                db.session.bulk_insert_mappings(Variant, batch)
                db.session.commit()
                if progress_callback:
                    progress_callback(min(i + len(product_list), total_items), total_items)

            if progress_callback:
                progress_callback(total_items, total_items)

            return True, f"초기화 완료: 상품 {len(product_list)}개, 옵션 {len(variant_list)}개 등록"

        except Exception as e:
            db.session.rollback()
            traceback.print_exc()
            raise e
