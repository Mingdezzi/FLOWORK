import traceback
from sqlalchemy import func
from sqlalchemy.orm import selectinload, joinedload
from flask import current_app
from flowork.extensions import db, cache
from flowork.models import Product, Variant, Store, StoreStock

class ProductService:
    @staticmethod
    def get_product_detail_context(product_id, brand_id, my_store_id=None):
        try:
            # 1. 상품 및 옵션/재고 로드
            product = Product.query.options(
                selectinload(Product.variants).selectinload(Variant.stock_levels)
            ).filter(
                Product.id == product_id,
                Product.brand_id == brand_id
            ).first()

            if not product:
                return None

            product_variants_for_map = product.variants
            
            # 2. 정렬된 변형 목록
            variants = db.session.query(Variant).filter(
                Variant.product_id == product.id
            ).order_by(Variant.color, Variant.size).all()
            
            variants_list_for_json = [{
                'id': v.id,
                'barcode': v.barcode,
                'color': v.color,
                'size': v.size,
                'hq_quantity': v.hq_quantity or 0,
                'original_price': v.original_price or 0,
                'sale_price': v.sale_price or 0
            } for v in variants]
            
            # 3. 전체 매장 목록
            all_stores = Store.query.filter(
                Store.brand_id == brand_id,
                Store.is_active == True
            ).order_by(Store.store_name).all()
            
            store_id_set = {s.id for s in all_stores}
            
            # 4. 재고 매트릭스 구축 (Store x Variant)
            stock_data_map = {s.id: {} for s in all_stores}
            
            for v in product_variants_for_map:
                for stock_level in v.stock_levels:
                    if stock_level.store_id in store_id_set:
                        stock_data_map[stock_level.store_id][v.id] = {
                            'quantity': stock_level.quantity,
                            'actual_stock': stock_level.actual_stock
                        }
            
            # 5. 연관 상품
            related_products = []
            if product.item_category:
                related_products = Product.query.options(selectinload(Product.variants)).filter(
                    Product.brand_id == brand_id, 
                    Product.item_category == product.item_category,
                    Product.id != product.id
                ).order_by(func.random()).limit(5).all()

            return {
                'product': product,
                'variants': variants,
                'variants_list_for_json': variants_list_for_json,
                'stock_data_map': stock_data_map,
                'all_stores': all_stores,
                'my_store_id': my_store_id,
                'related_products': related_products
            }

        except Exception as e:
            current_app.logger.error(f"Error in ProductService.get_product_detail_context: {e}")
            traceback.print_exc()
            raise e

    @staticmethod
    @cache.memoize(timeout=300) # 5분간 캐싱 (브랜드 ID 기준)
    def get_stock_overview_matrix(brand_id):
        try:
            current_app.logger.info(f"Fetching stock overview matrix for brand_id: {brand_id} (Not Cached)")
            
            all_stores = Store.query.filter(
                Store.brand_id == brand_id,
                Store.is_active == True
            ).order_by(Store.store_name).all()
            
            store_id_set = {s.id for s in all_stores}

            all_variants = db.session.query(Variant)\
                .join(Product)\
                .filter(Product.brand_id == brand_id)\
                .options(
                    joinedload(Variant.product),
                    selectinload(Variant.stock_levels)
                )\
                .order_by(Product.product_number, Variant.color, Variant.size)\
                .all()
            
            stock_matrix = {}
            for v in all_variants:
                stock_map_for_variant = {}
                for stock_level in v.stock_levels:
                    if stock_level.store_id in store_id_set:
                        stock_map_for_variant[stock_level.store_id] = stock_level.quantity
                
                stock_matrix[v.id] = stock_map_for_variant
                
            return {
                'all_stores': all_stores,
                'all_variants': all_variants,
                'stock_matrix': stock_matrix
            }
        except Exception as e:
            current_app.logger.error(f"Error in ProductService.get_stock_overview_matrix: {e}")
            traceback.print_exc()
            raise e