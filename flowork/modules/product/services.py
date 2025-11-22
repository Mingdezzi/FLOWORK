from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload, joinedload
from flowork.models import db, Product, Variant, Store, StoreStock, Setting, StockHistory
from flowork.utils import clean_string_upper, get_sort_key, get_choseong
from flowork.services.db import get_filter_options_from_db
import json

def get_product_detail(product_id, brand_id):
    product = Product.query.options(
        selectinload(Product.variants).selectinload(Variant.stock_levels)
    ).filter(
        Product.id == product_id,
        Product.brand_id == brand_id
    ).first()

    if not product:
        return None, None, None

    variants = db.session.query(Variant).filter(
        Variant.product_id == product.id
    ).order_by(Variant.color, Variant.size).all()

    all_stores = Store.query.filter(
        Store.brand_id == brand_id,
        Store.is_active == True
    ).order_by(Store.store_name).all()

    store_id_set = {s.id for s in all_stores}
    stock_data_map = {s.id: {} for s in all_stores}

    for v in product.variants:
        for stock_level in v.stock_levels:
            if stock_level.store_id in store_id_set:
                stock_data_map[stock_level.store_id][v.id] = {
                    'quantity': stock_level.quantity,
                    'actual_stock': stock_level.actual_stock
                }
    
    return product, variants, stock_data_map

def get_stock_overview(brand_id):
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
        
    return all_stores, all_variants, stock_matrix

def search_products(brand_id, params, page=1, per_page=20):
    query = db.session.query(Product).options(selectinload(Product.variants)).distinct().filter(
            Product.brand_id == brand_id
    )
    
    needs_variant_join = False
    variant_filters = []
    
    if params.get('product_name'):
        query = query.filter(Product.product_name_cleaned.like(f"%{clean_string_upper(params['product_name'])}%"))
    if params.get('product_number'):
        query = query.filter(Product.product_number_cleaned.like(f"%{clean_string_upper(params['product_number'])}%"))
    if params.get('item_category'):
        query = query.filter(Product.item_category == params['item_category'])
    if params.get('release_year'):
        query = query.filter(Product.release_year == int(params['release_year']))

    if params.get('color'):
        needs_variant_join = True
        variant_filters.append(Variant.color_cleaned == clean_string_upper(params['color']))
    if params.get('size'):
        needs_variant_join = True
        variant_filters.append(Variant.size_cleaned == clean_string_upper(params['size']))
    if params.get('original_price'):
        needs_variant_join = True
        variant_filters.append(Variant.original_price == int(params['original_price']))
    if params.get('sale_price'):
        needs_variant_join = True
        variant_filters.append(Variant.sale_price == int(params['sale_price']))
    if params.get('min_discount'):
        try:
            min_discount_val = float(params['min_discount']) / 100.0
            if min_discount_val > 0:
                needs_variant_join = True
                variant_filters.append(Variant.original_price > 0)
                variant_filters.append((Variant.sale_price / Variant.original_price) <= (1.0 - min_discount_val))
        except (ValueError, TypeError):
            pass 

    if needs_variant_join:
        query = query.join(Product.variants).filter(*variant_filters)
        
    pagination = query.order_by(
        Product.release_year.desc(), Product.product_name
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    return pagination

def update_stock_quantity(barcode, change, store_id, brand_id):
    try:
        cleaned_barcode = clean_string_upper(barcode)
        variant = db.session.query(Variant).join(Product).filter(
            Variant.barcode_cleaned == cleaned_barcode,
            Product.brand_id == brand_id
        ).first()
        
        if not variant:
            return False, '상품(바코드) 없음', None

        stock = db.session.query(StoreStock).filter_by(
            variant_id=variant.id,
            store_id=store_id
        ).with_for_update().first()
        
        if not stock:
            stock = StoreStock(variant_id=variant.id, store_id=store_id, quantity=0)
            db.session.add(stock)
            db.session.flush()
        
        old_qty = stock.quantity
        new_stock = max(0, stock.quantity + change)
        stock.quantity = new_stock
        
        history = StockHistory(
            store_id=store_id,
            variant_id=variant.id,
            change_type='MANUAL_UPDATE',
            quantity_change=change,
            current_quantity=new_stock
        )
        db.session.add(history)
        db.session.commit()
        
        diff = new_stock - stock.actual_stock if stock.actual_stock is not None else None
        return True, new_stock, diff
    except Exception as e:
        db.session.rollback()
        return False, str(e), None

def update_actual_stock_quantity(barcode, actual_val, store_id, brand_id):
    try:
        cleaned_barcode = clean_string_upper(barcode)
        variant = db.session.query(Variant).join(Product).filter(
            Variant.barcode_cleaned == cleaned_barcode,
            Product.brand_id == brand_id
        ).first()

        if not variant:
            return False, '상품(바코드) 없음', None

        stock = db.session.query(StoreStock).filter_by(
            variant_id=variant.id,
            store_id=store_id
        ).first()
        
        if not stock:
            stock = StoreStock(variant_id=variant.id, store_id=store_id, quantity=0)
            db.session.add(stock)
        
        stock.actual_stock = actual_val
        db.session.commit()
        
        diff = stock.quantity - actual_val if actual_val is not None else None
        return True, actual_val, diff
    except Exception as e:
        db.session.rollback()
        return False, str(e), None

def toggle_product_favorite(product_id, brand_id):
    try:
        product = Product.query.filter_by(id=product_id, brand_id=brand_id).first()
        if not product: return False, '상품 없음'
        
        product.is_favorite = 1 - (product.is_favorite or 0)
        new_status = product.is_favorite
        db.session.commit()
        return True, new_status
    except Exception as e:
        db.session.rollback()
        return False, str(e)

def delete_product_data(product_id, brand_id):
    try:
        product = Product.query.filter_by(id=product_id, brand_id=brand_id).first()
        if not product: return False, "상품 없음"
        
        db.session.delete(product)
        db.session.commit()
        return True, None
    except Exception as e:
        db.session.rollback()
        return False, str(e)